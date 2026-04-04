from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class PostDocument(BaseModel):
    post_id: str
    post_fullname: str
    author: str
    author_id: str
    subreddit: str
    subreddit_id: str
    subreddit_subscribers: int
    created_utc: float
    created_datetime: str
    created_date: str
    title_clean: str
    selftext_clean: str
    combined_text: str
    token_count: int
    hashtags: List[str]
    url: str
    external_url: Optional[str] = None
    normalized_external_url: Optional[str] = None
    domain: str
    is_self: bool
    post_hint: Optional[str] = None
    link_flair_text: Optional[str] = None
    score: int
    num_comments: int
    upvote_ratio: float
    num_crossposts: int
    engagement: int
    over_18: bool
    spoiler: bool
    locked: bool
    stickied: bool
    archived: bool
    is_crosspost: bool
    crosspost_parent: Optional[str] = None
    crosspost_parent_post_id: Optional[str] = None
    crosspost_parent_author: Optional[str] = None
    crosspost_parent_subreddit: Optional[str] = None
    permalink: str
    full_permalink: str

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    subreddit_filter: Optional[str] = None

class SearchResult(BaseModel):
    post: PostDocument
    relevance_score: float

class ClusterPostPreview(BaseModel):
    post_id: str
    title: str
    author: str
    subreddit: str
    score: int = 0
    num_comments: int = 0
    created_date: str = ""
    permalink: str = ""

class ClusterTopic(BaseModel):
    topic_id: int
    name: str
    count: int
    representation: List[str] = Field(default_factory=list)
    top_posts: List[ClusterPostPreview] = Field(default_factory=list)

class ClusterResult(BaseModel):
    topics: List[ClusterTopic] = Field(default_factory=list)
    cluster_labels: List[int] = Field(default_factory=list)
    top_terms: Dict[str, List[str]] = Field(default_factory=dict)
    post_counts: Dict[str, int] = Field(default_factory=dict)
    sample_posts: Dict[str, List[PostDocument]] = Field(default_factory=dict)

class NetworkNode(BaseModel):
    id: str
    label: str
    pagerank_score: float
    community_id: int
    post_count: int = 0
    top_subreddits: List[str] = Field(default_factory=list)
    top_domains: List[str] = Field(default_factory=list)
    recent_post_titles: List[str] = Field(default_factory=list)

class NetworkEdge(BaseModel):
    source: str
    target: str
    weight: float
    edge_type: str

class NetworkGraphMeta(BaseModel):
    graph_type: str
    query: Optional[str] = None
    top_n: int
    max_nodes: int
    total_nodes_before_limit: int
    total_edges_before_limit: int
    returned_nodes: int
    returned_edges: int
    truncated: bool = False
    truncation_note: Optional[str] = None
    corpus_hash: str
    computed_at: str
    backbone_computed_at: str

class GraphResult(BaseModel):
    nodes: List[NetworkNode] = Field(default_factory=list)
    edges: List[NetworkEdge] = Field(default_factory=list)
    meta: NetworkGraphMeta

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    query: str

class TimeSeriesPoint(BaseModel):
    date: str
    count: int
    avg_score: float
    avg_engagement: float
