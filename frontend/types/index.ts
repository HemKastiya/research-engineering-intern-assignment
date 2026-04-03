export interface Post {
  id: string;
  title: string;
  selftext_clean?: string;
  subreddit: string;
  author: string;
  created_utc: string;
  score: number;
}

export interface SearchResult {
  post: Post;
  relevance_score: number;
}

export interface TimeSeriesPoint {
  date: string;
  count: number;
  avg_score: number;
}

export interface ClusterTopic {
  topic_id: number;
  name: string;
  count: number;
  representation: string[];
}

export interface ClusterResult {
  topics: ClusterTopic[];
}

export interface NetworkNode {
  id: string;
  label: string;
  pagerank_score: number;
  community_id: number;
}

export interface NetworkEdge {
  source: string;
  target: string;
  weight: number;
}

export interface GraphResult {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface IngestStatus {
  mongo_documents: number;
  chroma_vectors: number;
  embedding_status: string;
}
