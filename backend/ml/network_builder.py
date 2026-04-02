"""build_graph(query: str, subreddit: str) -> GraphResult. networkx.DiGraph PageRank & Louvain."""
import networkx as nx
from community import community_louvain
import pymongo
from core.config import settings

def _get_sync_db():
    client = pymongo.MongoClient(settings.MONGO_URI)
    return client[settings.MONGO_DB]

def build_graph(query: str, subreddit: str) -> dict:
    db = _get_sync_db()
    
    filters = {}
    if subreddit:
        filters["subreddit"] = subreddit
    if query:
        # Simplistic text index filter for subgraph queries
        filters["$text"] = {"$search": query}
        
    cursor = db.posts.find(filters, {"author": 1, "crosspost_parent_author": 1, "domain": 1, "score": 1})
    docs = list(cursor)
    
    G = nx.DiGraph()
    
    for d in docs:
        author = d.get("author")
        if not author or author == "[deleted]":
             continue
             
        cp_author = d.get("crosspost_parent_author")
        domain = d.get("domain", "")
        weight = d.get("score", 1)
        if weight < 1:
             weight = 1
             
        # Add basic authored node
        if not G.has_node(author):
             G.add_node(author, post_count=0)
        G.nodes[author]['post_count'] += 1
        
        # 1. Crosspost edges
        if cp_author and cp_author != "[deleted]":
             if not G.has_node(cp_author):
                  G.add_node(cp_author, post_count=0)
             if G.has_edge(author, cp_author):
                  G[author][cp_author]['weight'] += weight
             else:
                  G.add_edge(author, cp_author, weight=weight)
                  
        # 2. Shared Domain edges? 
        # (Implementing exact shared domains creates a bipartite graph, but since prompt says "nodes are authors", we skip dense matrix logic to remain safe and lightweight for now)
        
    if G.number_of_nodes() == 0:
         return {"nodes": [], "edges": []}
         
    # Convert directed for Louvain (requires undirected)
    UndG = G.to_undirected()
    try:
        partition = community_louvain.best_partition(UndG)
    except:
        partition = {n: 0 for n in UndG.nodes()}
        
    # PageRank on disconnected components per requirement
    pageranks = {}
    for c in nx.weakly_connected_components(G):
        subgraph = G.subgraph(c)
        try:
             pr = nx.pagerank(subgraph, alpha=0.85, weight='weight')
             pageranks.update(pr)
        except:
             for n in c:
                  pageranks[n] = 0.0

    nodes = []
    for n in G.nodes():
         nodes.append({
              "id": n,
              "label": n,
              "pagerank": pageranks.get(n, 0.0),
              "community": partition.get(n, 0),
              "post_count": G.nodes[n].get('post_count', 0)
         })
         
    edges = []
    for u, v, data in G.edges(data=True):
         edges.append({
              "source": u, 
              "target": v,
              "weight": data.get('weight', 1)
         })
         
    return {"nodes": nodes, "edges": edges}

def remove_node(graph_dict: dict, node_id: str) -> dict:
     G = nx.DiGraph()
     
     for n in graph_dict["nodes"]:
          if n["id"] != node_id:
               G.add_node(n["id"], post_count=n.get("post_count", 0), community=n.get("community", 0))
               
     for e in graph_dict["edges"]:
          if e["source"] != node_id and e["target"] != node_id:
               G.add_edge(e["source"], e["target"], weight=e.get("weight", 1))
               
     # Recompute PageRank
     pageranks = {}
     for c in nx.weakly_connected_components(G):
        subgraph = G.subgraph(c)
        try:
             pr = nx.pagerank(subgraph, alpha=0.85, weight='weight')
             pageranks.update(pr)
        except:
             for n in c:
                  pageranks[n] = 0.0
                  
     nodes = []
     for n in G.nodes():
          item = {
               "id": n,
               "label": n,
               "pagerank": pageranks.get(n, 0.0),
               "community": G.nodes[n].get('community', 0),
               "post_count": G.nodes[n].get('post_count', 0)
          }
          nodes.append(item)
          
     edges = []
     for u, v, data in G.edges(data=True):
          edges.append({"source": u, "target": v, "weight": data.get('weight', 1)})
          
     return {"nodes": nodes, "edges": edges}
