import json
import redis
from pydantic import BaseModel
from bertopic import BERTopic
from hdbscan import HDBSCAN
from umap import UMAP
from ml.embedder import embed
from core.config import settings
from core.mongo import client as sync_mongo

# We will implement run_clustering sequentially. Because BERTopic is CPU heavy, we might fetch everything from a sync connector in a background thread here.
# Note: we are writing synchronous logic because clustering runs in celery which is sync.

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

class SynchronousMongo:
    def __init__(self):
        # We need a synchronous client for Celery workers
        import pymongo
        self.client = pymongo.MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.MONGO_DB]
        
def run_clustering(n_topics: int) -> dict:
    # Check cache
    cache_key = f"cluster_{n_topics}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
        
    db = SynchronousMongo().db
    cursor = db.posts.find({}, {"combined_text": 1, "title_clean": 1, "post_id": 1})
    docs = list(cursor)
    
    if len(docs) < 10:
        return {"cluster_labels": [], "top_terms": {}, "post_counts": {}, "sample_posts": {}}
        
    texts = [d["combined_text"] for d in docs]
    post_ids = [d["post_id"] for d in docs]
    
    # 1. Embeddings
    embeddings = embed(texts)
    
    # 2. Constraints & Models
    n_posts = len(texts)
    if n_topics >= n_posts:
        n_topics = max(1, n_posts // 2)
        
    min_cluster_size = max(5, n_posts // 200)
    
    # UMAP for reduction (both for clustering and visualization later)
    umap_model = UMAP(n_neighbors=15, n_components=5, min_dist=0.0, metric='cosine', random_state=42)
    # 2D UMAP exclusively for returning the visual 2D projection
    umap_2d = UMAP(n_neighbors=15, n_components=2, min_dist=0.0, metric='cosine', random_state=42)
    
    hdbscan_model = HDBSCAN(min_cluster_size=min_cluster_size, metric='euclidean', cluster_selection_method='eom', prediction_data=True)
    
    # Base BERTopic model
    topic_model = BERTopic(
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        language="english",
        calculate_probabilities=False,
        nr_topics=n_topics if n_topics > 1 else None
    )
    
    topics, probs = topic_model.fit_transform(texts, embeddings)
    coords_2d = umap_2d.fit_transform(embeddings)
    
    # 3. Format results precisely as expected by the frontend
    topic_info = topic_model.get_topic_info()
    
    top_terms = {}
    post_counts = {}
    sample_posts = {}
    
    for _, row in topic_info.iterrows():
        t_id = int(row["Topic"])
        if t_id == -1:
            label = "-1_Outliers"
        else:
            label = f"{t_id}_{row['Name']}"
        
        post_counts[label] = int(row["Count"])
        words = topic_model.get_topic(t_id)
        if words:
            top_terms[label] = [w[0] for w in words[:10]]
        else:
            top_terms[label] = []
            
        # Extract a few sample titles for this topic manually
        # In a real heavy system we'd join, but short loop logic:
        sample_posts[label] = []

    # Map each item individually
    cluster_labels = []
    
    for i, t_id in enumerate(topics):
        if t_id == -1:
            l = "-1_Outliers"
        else:
            l = f"{t_id}_{topic_info.loc[topic_info['Topic'] == t_id, 'Name'].values[0]}"
            
        cluster_labels.append(l)
        
        # Pull 5 samples top per topic roughly finding the earliest docs assigned to it
        if len(sample_posts[l]) < 5:
            sample_posts[l].append(docs[i])

    result_dict = {
        "cluster_labels": cluster_labels,
        "top_terms": top_terms,
        "post_counts": post_counts,
        "samples": sample_posts, # Note: Pydantic model uses PostDocument, logic requires formatting these
        "umap_2d": coords_2d.tolist(),
        "post_ids": post_ids
    }
    
    redis_client.set(cache_key, json.dumps(result_dict))
    
    return result_dict
