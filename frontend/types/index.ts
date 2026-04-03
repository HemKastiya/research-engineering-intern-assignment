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
  avg_engagement: number;
}

export interface DistributionPoint {
  label: string;
  value: number;
}

export interface TrendProjectionPoint {
  date: string;
  predicted_count: number;
}

export interface TrendRegressionAnalytics {
  slope: number;
  r2: number;
  direction: "upward" | "downward" | "flat";
  trend_line: TrendProjectionPoint[];
  projected_next: TrendProjectionPoint[];
}

export interface AnomalyPoint {
  date: string;
  count: number;
  avg_score: number;
  avg_engagement: number;
}

export interface DailyClusterSummary {
  cluster_id: number;
  days: number;
  avg_count: number;
  avg_score: number;
  avg_engagement: number;
}

export interface DailyClusterAssignment {
  date: string;
  cluster_id: number;
  count: number;
  avg_score: number;
  avg_engagement: number;
}

export interface TimeSeriesAnalytics {
  time_series: TimeSeriesPoint[];
  subreddit_distribution: DistributionPoint[];
  weekday_distribution: DistributionPoint[];
  score_buckets: DistributionPoint[];
  ml_models: {
    trend_regression: TrendRegressionAnalytics;
    anomalies: AnomalyPoint[];
    daily_clusters: {
      n_clusters: number;
      clusters: DailyClusterSummary[];
      assignments: DailyClusterAssignment[];
    };
  };
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
  post_count: number;
  top_subreddits: string[];
  top_domains: string[];
  recent_post_titles: string[];
}

export type NetworkGraphType = "co_subreddit" | "crosspost" | "shared_domain";

export interface NetworkEdge {
  source: string;
  target: string;
  weight: number;
  edge_type: NetworkGraphType;
}

export interface NetworkGraphMeta {
  graph_type: NetworkGraphType;
  query?: string | null;
  top_n: number;
  max_nodes: number;
  total_nodes_before_limit: number;
  total_edges_before_limit: number;
  returned_nodes: number;
  returned_edges: number;
  truncated: boolean;
  truncation_note?: string | null;
  corpus_hash: string;
  computed_at: string;
  backbone_computed_at: string;
}

export interface GraphResult {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
  meta: NetworkGraphMeta;
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
