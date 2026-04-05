import type {
  SearchResult,
  TimeSeriesPoint,
  TimeSeriesAnalytics,
  ClusterResult,
  GraphResult,
  NetworkGraphType,
  IngestStatus,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

const DEFAULT_TIMEOUT_MS = 15_000;
const DEFAULT_CACHE_TTL_MS = 5 * 60_000;
const SESSION_CACHE_PREFIX = "rei-api-cache:v1:";

interface FetchJsonOptions extends RequestInit {
  timeoutMs?: number;
  cacheTtlMs?: number;
  cacheKey?: string;
}

interface CacheEntry {
  expiresAt: number;
  payload: unknown;
}

const memoryCache = new Map<string, CacheEntry>();

function isBrowserEnvironment(): boolean {
  return typeof window !== "undefined";
}

function canUseSessionStorage(): boolean {
  return isBrowserEnvironment() && typeof window.sessionStorage !== "undefined";
}

function clonePayload<T>(payload: T): T {
  if (typeof structuredClone === "function") {
    return structuredClone(payload);
  }
  return JSON.parse(JSON.stringify(payload)) as T;
}

function buildCacheKey(url: string, options: RequestInit, explicitKey?: string): string | null {
  const method = (options.method ?? "GET").toUpperCase();
  if (explicitKey) {
    return `${method}:${API_BASE}${url}:${explicitKey}`;
  }

  if (options.body == null) {
    return `${method}:${API_BASE}${url}`;
  }
  if (typeof options.body === "string") {
    return `${method}:${API_BASE}${url}:${options.body}`;
  }
  return null;
}

function readCachedValue<T>(key: string): T | null {
  const now = Date.now();
  const fromMemory = memoryCache.get(key);
  if (fromMemory) {
    if (fromMemory.expiresAt > now) {
      return clonePayload(fromMemory.payload as T);
    }
    memoryCache.delete(key);
  }

  if (!canUseSessionStorage()) return null;

  const storageKey = `${SESSION_CACHE_PREFIX}${key}`;
  const rawValue = window.sessionStorage.getItem(storageKey);
  if (!rawValue) return null;

  try {
    const parsed = JSON.parse(rawValue) as Partial<CacheEntry>;
    if (typeof parsed.expiresAt !== "number") {
      window.sessionStorage.removeItem(storageKey);
      return null;
    }
    if (parsed.expiresAt <= now) {
      window.sessionStorage.removeItem(storageKey);
      return null;
    }

    const entry: CacheEntry = {
      expiresAt: parsed.expiresAt,
      payload: parsed.payload,
    };
    memoryCache.set(key, entry);
    return clonePayload(entry.payload as T);
  } catch {
    window.sessionStorage.removeItem(storageKey);
    return null;
  }
}

function writeCachedValue(key: string, payload: unknown, ttlMs: number): void {
  const entry: CacheEntry = {
    expiresAt: Date.now() + ttlMs,
    payload,
  };
  memoryCache.set(key, entry);
  if (!canUseSessionStorage()) return;

  try {
    window.sessionStorage.setItem(`${SESSION_CACHE_PREFIX}${key}`, JSON.stringify(entry));
  } catch {
    // Ignore quota/security errors and keep in-memory cache only.
  }
}

async function fetchJson<T>(
  url: string,
  options?: FetchJsonOptions
): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, cacheTtlMs, cacheKey, ...fetchOptions } = options ?? {};
  const method = (fetchOptions.method ?? "GET").toUpperCase();
  const effectiveCacheTtlMs = cacheTtlMs ?? (method === "GET" ? DEFAULT_CACHE_TTL_MS : 0);
  const shouldUseCache = isBrowserEnvironment() && effectiveCacheTtlMs > 0;
  const resolvedCacheKey = shouldUseCache
    ? buildCacheKey(url, { ...fetchOptions, method }, cacheKey)
    : null;

  if (shouldUseCache && resolvedCacheKey) {
    const cachedValue = readCachedValue<T>(resolvedCacheKey);
    if (cachedValue !== null) return cachedValue;
  }

  // Merge caller's signal with timeout signal
  const timeoutCtrl = new AbortController();
  const timerId = setTimeout(() => timeoutCtrl.abort(), timeoutMs);

  const signal = fetchOptions.signal
    ? anySignal([fetchOptions.signal, timeoutCtrl.signal])
    : timeoutCtrl.signal;

  try {
    const res = await fetch(`${API_BASE}${url}`, {
      headers: { "Content-Type": "application/json" },
      ...fetchOptions,
      signal,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        detail = body.detail ?? detail;
      } catch { }
      throw new ApiError(res.status, detail);
    }

    const data = (await res.json()) as T;
    if (shouldUseCache && resolvedCacheKey) {
      writeCachedValue(resolvedCacheKey, data, effectiveCacheTtlMs);
      return clonePayload(data);
    }
    return data;
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new ApiError(408, `Request timed out after ${timeoutMs / 1000}s`);
    }
    throw err;
  } finally {
    clearTimeout(timerId);
  }
}

/** Aborts as soon as any one of the provided signals fires */
function anySignal(signals: AbortSignal[]): AbortSignal {
  const ctrl = new AbortController();
  for (const sig of signals) {
    if (sig.aborted) { ctrl.abort(); break; }
    sig.addEventListener("abort", () => ctrl.abort(), { once: true });
  }
  return ctrl.signal;
}

// ── Ingest ────────────────────────────────────────────────────────────────────
export async function getIngestStatus(): Promise<IngestStatus> {
  // Keep status polling live; avoid serving stale ingest progress.
  return fetchJson<IngestStatus>("/api/ingest/status", { cacheTtlMs: 0 });
}

// ── Time Series ───────────────────────────────────────────────────────────────
export interface TimeSeriesParams {
  query?: string;
  subreddit?: string;
  from_date?: string;
  to_date?: string;
}

export async function getTimeSeries(params: TimeSeriesParams = {}): Promise<TimeSeriesPoint[]> {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v))
  ).toString();
  return fetchJson<TimeSeriesPoint[]>(`/api/timeseries/${qs ? "?" + qs : ""}`);
}

export async function getTimeSeriesAnalytics(
  params: TimeSeriesParams = {}
): Promise<TimeSeriesAnalytics> {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v))
  ).toString();
  // Analytics can include aggregation + ML transforms; allow a wider timeout window.
  return fetchJson<TimeSeriesAnalytics>(`/api/timeseries/analytics${qs ? "?" + qs : ""}`, {
    timeoutMs: 60_000,
  });
}

export async function getTimeSeriesSummary(
  params: TimeSeriesParams = {}
): Promise<{ summary: string }> {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v))
  ).toString();
  return fetchJson<{ summary: string }>(`/api/timeseries/summary${qs ? "?" + qs : ""}`);
}

// ── Search ────────────────────────────────────────────────────────────────────
export interface SearchParams {
  query: string;
  top_k?: number;
  subreddit_filter?: string;
}

export async function searchPosts(params: SearchParams): Promise<SearchResult[]> {
  return fetchJson<SearchResult[]>("/api/search/", {
    method: "POST",
    body: JSON.stringify({ top_k: 10, ...params }),
    cacheTtlMs: 5 * 60_000,
  });
}

// ── Clusters ──────────────────────────────────────────────────────────────────
// Clustering is CPU-bound on the backend; give it up to 2 minutes
export async function getClusters(n_topics = 10): Promise<ClusterResult> {
  return fetchJson<ClusterResult>(`/api/clusters/?n_topics=${n_topics}`, {
    timeoutMs: 120_000,
  });
}

export interface EmbeddingsResult {
  umap_2d: [number, number][];
  cluster_labels: number[];
  post_ids: string[];
  point_labels?: string[];
  point_confidences?: number[];
  projection_quality?: {
    umap_n_neighbors: number;
    umap_min_dist: number;
    trustworthiness_at_k: number | null;
    knn_overlap_at_k: number | null;
    tuning_score: number | null;
    metric_k: number;
    sample_size: number;
    point_count: number;
    outlier_ratio: number;
  };
}

export async function getEmbeddings(n_clusters = 10): Promise<EmbeddingsResult> {
  return fetchJson<EmbeddingsResult>(`/api/clusters/embeddings?n_clusters=${n_clusters}`, {
    timeoutMs: 120_000,
  });
}

// ── Network ───────────────────────────────────────────────────────────────────
export interface NetworkParams {
  query?: string;
  graph_type?: NetworkGraphType;
  top_n?: number;
  max_nodes?: number;
}

export async function getNetwork(params: NetworkParams = {}): Promise<GraphResult> {
  const entries = Object.entries(params)
    .filter(([, v]) => v != null)
    .map(([k, v]) => [k, String(v)]) as [string, string][];
  const qs = new URLSearchParams(entries).toString();
  return fetchJson<GraphResult>(`/api/network${qs ? "?" + qs : ""}`, {
    timeoutMs: 30_000,
  });
}

// ── Chat (SSE) ────────────────────────────────────────────────────────────────
export interface ChatRequest {
  query: string;
  messages: Array<{ role: string; content: string }>;
}

export function streamChat(
  req: ChatRequest,
  onChunk: (token: string) => void,
  onSources: (sources: SearchResult[]) => void,
  onSuggestions: (suggestions: string[]) => void,
  onError: (err: string) => void,
  onDone: () => void
): AbortController {
  const controller = new AbortController();

  fetch(`${API_BASE}/api/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok || !res.body) {
        onError("Chat request failed");
        return;
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.content) onChunk(data.content);
            if (Array.isArray(data.sources)) onSources(data.sources as SearchResult[]);
            if (data.suggested_queries) onSuggestions(data.suggested_queries);
            if (data.error) onError(data.error);
          } catch { }
        }
      }
      onDone();
    })
    .catch((err) => {
      if (err.name !== "AbortError") onError(String(err));
    });

  return controller;
}
