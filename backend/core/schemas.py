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

class ClusterResult(BaseModel):
    cluster_labels: List[int]
    top_terms: Dict[str, List[str]]
    post_counts: Dict[str, int]
    sample_posts: Dict[str, List[PostDocument]]

class NetworkNode(BaseModel):
    id: str
    label: str
    pagerank: float
    community: int
    post_count: int

class NetworkEdge(BaseModel):
    source: str
    target: str
    weight: float

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
