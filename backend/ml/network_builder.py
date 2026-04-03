"""Precomputed network backbone and fast induced-subgraph responses."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from itertools import combinations
import hashlib
import re
import threading
from typing import Any

import networkx as nx
import pymongo

from core.config import settings

try:
    from community import community_louvain
except Exception:
    community_louvain = None


GRAPH_TYPE_CO_SUBREDDIT = "co_subreddit"
GRAPH_TYPE_CROSSPOST = "crosspost"
GRAPH_TYPE_SHARED_DOMAIN = "shared_domain"
SUPPORTED_GRAPH_TYPES = {
    GRAPH_TYPE_CO_SUBREDDIT,
    GRAPH_TYPE_CROSSPOST,
    GRAPH_TYPE_SHARED_DOMAIN,
}

DEFAULT_BACKBONE_TOP_N = 150
DEFAULT_MAX_RESPONSE_NODES = 200
MAX_BACKBONE_TOP_N = 500

_TOP_LIST_SIZE = 5
_RECENT_TITLE_SAMPLE = 5


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_author(author: Any) -> str:
    if author is None:
        return ""
    value = str(author).strip()
    if not value:
        return ""
    if value.lower() in {"[deleted]", "[removed]"}:
        return ""
    return value


def _is_external_domain(domain: Any) -> bool:
    value = str(domain or "").strip().lower()
    if not value:
        return False
    if value.startswith("self."):
        return False
    if "reddit.com" in value:
        return False
    return True


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _safe_pagerank(graph: nx.Graph | nx.DiGraph) -> dict[str, float]:
    node_count = graph.number_of_nodes()
    if node_count == 0:
        return {}
    if graph.number_of_edges() == 0:
        uniform = 1.0 / max(node_count, 1)
        return {str(node): uniform for node in graph.nodes()}
    try:
        return nx.pagerank(graph, alpha=0.85, weight="weight")
    except Exception:
        total_weight = 0.0
        degree_map: dict[str, float] = {}
        for node in graph.nodes():
            if graph.is_directed():
                degree = float(graph.in_degree(node, weight="weight")) + float(
                    graph.out_degree(node, weight="weight")
                )
            else:
                degree = float(graph.degree(node, weight="weight"))
            degree_map[str(node)] = degree
            total_weight += degree
        if total_weight <= 0:
            uniform = 1.0 / max(node_count, 1)
            return {str(node): uniform for node in graph.nodes()}
        return {node: degree / total_weight for node, degree in degree_map.items()}


def _safe_louvain(graph: nx.Graph | nx.DiGraph) -> dict[str, int]:
    if graph.number_of_nodes() == 0:
        return {}
    undirected = graph.to_undirected() if graph.is_directed() else graph
    if undirected.number_of_edges() == 0:
        return {str(node): 0 for node in undirected.nodes()}

    if community_louvain is not None:
        try:
            result = community_louvain.best_partition(undirected, weight="weight")
            return {str(node): int(group) for node, group in result.items()}
        except Exception:
            pass

    partition: dict[str, int] = {}
    for idx, component in enumerate(nx.connected_components(undirected)):
        for node in component:
            partition[str(node)] = idx
    return partition


def _compute_corpus_hash(docs: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for doc in sorted(docs, key=lambda item: str(item.get("post_id") or "")):
        digest.update(str(doc.get("post_id", "")).encode("utf-8", errors="ignore"))
        digest.update(str(doc.get("created_utc", "")).encode("utf-8", errors="ignore"))
    return digest.hexdigest()


def _build_author_profiles(docs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    bucket: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "post_count": 0,
            "subreddit_counts": Counter(),
            "domain_counts": Counter(),
            "titles": [],
        }
    )

    for doc in docs:
        author = _normalize_author(doc.get("author"))
        if not author:
            continue

        stats = bucket[author]
        stats["post_count"] += 1

        subreddit = str(doc.get("subreddit") or "").strip()
        if subreddit:
            stats["subreddit_counts"][subreddit] += 1

        domain = str(doc.get("domain") or "").strip()
        if _is_external_domain(domain):
            stats["domain_counts"][domain] += 1

        title = str(doc.get("title_clean") or "").strip()
        if title:
            created_utc = _safe_float(doc.get("created_utc"))
            stats["titles"].append((created_utc, title))

    profiles: dict[str, dict[str, Any]] = {}
    for author, stats in bucket.items():
        top_subreddits = [name for name, _ in stats["subreddit_counts"].most_common(_TOP_LIST_SIZE)]
        top_domains = [name for name, _ in stats["domain_counts"].most_common(_TOP_LIST_SIZE)]
        recent_titles: list[str] = []
        seen_titles: set[str] = set()
        for _, title in sorted(stats["titles"], key=lambda item: item[0], reverse=True):
            if title in seen_titles:
                continue
            seen_titles.add(title)
            recent_titles.append(title)
            if len(recent_titles) >= _RECENT_TITLE_SAMPLE:
                break

        profiles[author] = {
            "post_count": int(stats["post_count"]),
            "top_subreddits": top_subreddits,
            "top_domains": top_domains,
            "recent_post_titles": recent_titles,
        }

    return profiles


def _build_full_co_subreddit_graph(
    docs: list[dict[str, Any]], author_profiles: dict[str, dict[str, Any]]
) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(author_profiles.keys())

    subreddit_authors: dict[str, set[str]] = defaultdict(set)
    for doc in docs:
        author = _normalize_author(doc.get("author"))
        subreddit = str(doc.get("subreddit") or "").strip()
        if author and subreddit:
            subreddit_authors[subreddit].add(author)

    for authors in subreddit_authors.values():
        if len(authors) < 2:
            continue
        for left, right in combinations(sorted(authors), 2):
            if graph.has_edge(left, right):
                graph[left][right]["weight"] += 1.0
            else:
                graph.add_edge(
                    left,
                    right,
                    weight=1.0,
                    edge_type=GRAPH_TYPE_CO_SUBREDDIT,
                )

    return graph


def _select_backbone_nodes(
    full_graph: nx.Graph,
    pagerank: dict[str, float],
    author_profiles: dict[str, dict[str, Any]],
    top_n: int,
) -> list[str]:
    connected_nodes = [node for node in full_graph.nodes() if full_graph.degree(node) > 0]
    connected_nodes.sort(
        key=lambda node: (
            pagerank.get(str(node), 0.0),
            float(full_graph.degree(node, weight="weight")),
            author_profiles.get(str(node), {}).get("post_count", 0),
        ),
        reverse=True,
    )

    selected = connected_nodes[:top_n]
    if len(selected) >= top_n:
        return [str(node) for node in selected]

    selected_set = {str(node) for node in selected}
    remaining = [node for node in full_graph.nodes() if str(node) not in selected_set]
    remaining.sort(
        key=lambda node: (
            author_profiles.get(str(node), {}).get("post_count", 0),
            pagerank.get(str(node), 0.0),
        ),
        reverse=True,
    )
    selected.extend(remaining[: max(0, top_n - len(selected))])
    return [str(node) for node in selected]


def _build_backbone_co_subreddit(
    full_co_subreddit_graph: nx.Graph,
    backbone_nodes: list[str],
) -> nx.Graph:
    graph = full_co_subreddit_graph.subgraph(backbone_nodes).copy()
    for left, right in graph.edges():
        graph[left][right]["edge_type"] = GRAPH_TYPE_CO_SUBREDDIT
    return graph


def _build_backbone_crosspost(
    docs: list[dict[str, Any]],
    backbone_nodes: list[str],
) -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_nodes_from(backbone_nodes)
    backbone_set = set(backbone_nodes)

    for doc in docs:
        reposter = _normalize_author(doc.get("author"))
        original_author = _normalize_author(doc.get("crosspost_parent_author"))
        if not reposter or not original_author:
            continue
        if reposter == original_author:
            continue
        if reposter not in backbone_set or original_author not in backbone_set:
            continue
        if graph.has_edge(original_author, reposter):
            graph[original_author][reposter]["weight"] += 1.0
        else:
            graph.add_edge(
                original_author,
                reposter,
                weight=1.0,
                edge_type=GRAPH_TYPE_CROSSPOST,
            )
    return graph


def _build_backbone_shared_domain(
    docs: list[dict[str, Any]],
    backbone_nodes: list[str],
) -> nx.Graph:
    graph = nx.Graph()
    graph.add_nodes_from(backbone_nodes)
    backbone_set = set(backbone_nodes)
    domain_authors: dict[str, set[str]] = defaultdict(set)

    for doc in docs:
        author = _normalize_author(doc.get("author"))
        if not author or author not in backbone_set:
            continue
        domain = str(doc.get("domain") or "").strip().lower()
        if not _is_external_domain(domain):
            continue
        domain_authors[domain].add(author)

    for authors in domain_authors.values():
        if len(authors) < 2:
            continue
        for left, right in combinations(sorted(authors), 2):
            if graph.has_edge(left, right):
                graph[left][right]["weight"] += 1.0
            else:
                graph.add_edge(
                    left,
                    right,
                    weight=1.0,
                    edge_type=GRAPH_TYPE_SHARED_DOMAIN,
                )

    return graph


def _build_backbone_state(top_n: int) -> dict[str, Any]:
    projection = {
        "post_id": 1,
        "created_utc": 1,
        "author": 1,
        "subreddit": 1,
        "domain": 1,
        "title_clean": 1,
        "crosspost_parent_author": 1,
    }
    client = pymongo.MongoClient(settings.MONGO_URI)
    try:
        db = client[settings.MONGO_DB]
        docs = list(db.posts.find({}, projection))
    finally:
        client.close()

    if not docs:
        empty_graphs = {
            graph_type: {
                "graph": nx.DiGraph() if graph_type == GRAPH_TYPE_CROSSPOST else nx.Graph(),
                "pagerank": {},
                "communities": {},
            }
            for graph_type in SUPPORTED_GRAPH_TYPES
        }
        return {
            "top_n": top_n,
            "computed_at": _utc_now_iso(),
            "corpus_hash": "empty",
            "node_ids": [],
            "profiles": {},
            "graphs": empty_graphs,
        }

    author_profiles = _build_author_profiles(docs)
    full_co_subreddit = _build_full_co_subreddit_graph(docs, author_profiles)
    full_pagerank = _safe_pagerank(full_co_subreddit)
    backbone_nodes = _select_backbone_nodes(
        full_graph=full_co_subreddit,
        pagerank=full_pagerank,
        author_profiles=author_profiles,
        top_n=top_n,
    )

    co_subreddit_graph = _build_backbone_co_subreddit(full_co_subreddit, backbone_nodes)
    crosspost_graph = _build_backbone_crosspost(docs, backbone_nodes)
    shared_domain_graph = _build_backbone_shared_domain(docs, backbone_nodes)

    graphs: dict[str, dict[str, Any]] = {}
    for graph_type, graph in (
        (GRAPH_TYPE_CO_SUBREDDIT, co_subreddit_graph),
        (GRAPH_TYPE_CROSSPOST, crosspost_graph),
        (GRAPH_TYPE_SHARED_DOMAIN, shared_domain_graph),
    ):
        graphs[graph_type] = {
            "graph": graph,
            "pagerank": _safe_pagerank(graph),
            "communities": _safe_louvain(graph),
        }

    selected_profiles = {node_id: author_profiles.get(node_id, {}) for node_id in backbone_nodes}

    return {
        "top_n": top_n,
        "computed_at": _utc_now_iso(),
        "corpus_hash": _compute_corpus_hash(docs),
        "node_ids": backbone_nodes,
        "profiles": selected_profiles,
        "graphs": graphs,
    }


def _get_or_create_lock(app_state: Any) -> threading.Lock:
    lock = getattr(app_state, "network_backbone_lock", None)
    if lock is None:
        lock = threading.Lock()
        setattr(app_state, "network_backbone_lock", lock)
    return lock


def _get_or_create_cache(app_state: Any) -> dict[int, dict[str, Any]]:
    cache = getattr(app_state, "network_backbones", None)
    if cache is None:
        cache = {}
        setattr(app_state, "network_backbones", cache)
    return cache


def _sanitize_top_n(top_n: int | None) -> int:
    value = _safe_int(top_n if top_n is not None else DEFAULT_BACKBONE_TOP_N)
    if value <= 0:
        value = DEFAULT_BACKBONE_TOP_N
    return min(value, MAX_BACKBONE_TOP_N)


def _sanitize_max_nodes(max_nodes: int | None) -> int:
    value = _safe_int(max_nodes if max_nodes is not None else DEFAULT_MAX_RESPONSE_NODES)
    if value <= 0:
        value = DEFAULT_MAX_RESPONSE_NODES
    return min(value, MAX_BACKBONE_TOP_N)


def ensure_backbone_state(app_state: Any, top_n: int = DEFAULT_BACKBONE_TOP_N) -> dict[str, Any]:
    sanitized_top_n = _sanitize_top_n(top_n)
    cache = _get_or_create_cache(app_state)
    existing = cache.get(sanitized_top_n)
    if existing is not None:
        return existing

    lock = _get_or_create_lock(app_state)
    with lock:
        cache = _get_or_create_cache(app_state)
        existing = cache.get(sanitized_top_n)
        if existing is not None:
            return existing
        computed = _build_backbone_state(sanitized_top_n)
        cache[sanitized_top_n] = computed
        return computed


def warm_network_backbone_cache(
    app_state: Any,
    top_n: int = DEFAULT_BACKBONE_TOP_N,
) -> dict[str, Any]:
    return ensure_backbone_state(app_state, top_n=top_n)


def _lookup_matching_authors(
    backbone_state: dict[str, Any],
    query: str | None,
) -> set[str]:
    node_ids = set(backbone_state["node_ids"])
    if not query:
        return node_ids

    keyword = query.strip()
    if not keyword:
        return node_ids

    client = pymongo.MongoClient(settings.MONGO_URI)
    try:
        db = client[settings.MONGO_DB]
        filters = {
            "author": {"$in": list(node_ids)},
            "$text": {"$search": keyword},
        }
        matches = db.posts.distinct("author", filters)
    except Exception:
        escaped_keyword = re.escape(keyword)
        fallback_filters = {
            "author": {"$in": list(node_ids)},
            "$or": [
                {"title_clean": {"$regex": escaped_keyword, "$options": "i"}},
                {"selftext_clean": {"$regex": escaped_keyword, "$options": "i"}},
                {"combined_text": {"$regex": escaped_keyword, "$options": "i"}},
            ],
        }
        matches = db.posts.distinct("author", fallback_filters)
    finally:
        client.close()

    return {author for author in matches if author in node_ids}


def _prepare_nodes(
    node_ids: list[str],
    pagerank_scores: dict[str, float],
    communities: dict[str, int],
    profiles: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    sorted_nodes = sorted(
        node_ids,
        key=lambda node_id: pagerank_scores.get(node_id, 0.0),
        reverse=True,
    )

    nodes: list[dict[str, Any]] = []
    for node_id in sorted_nodes:
        profile = profiles.get(node_id, {})
        nodes.append(
            {
                "id": node_id,
                "label": node_id,
                "pagerank_score": float(pagerank_scores.get(node_id, 0.0)),
                "community_id": int(communities.get(node_id, 0)),
                "post_count": int(profile.get("post_count", 0)),
                "top_subreddits": list(profile.get("top_subreddits", [])),
                "top_domains": list(profile.get("top_domains", [])),
                "recent_post_titles": list(profile.get("recent_post_titles", [])),
            }
        )
    return nodes


def _prepare_edges(graph: nx.Graph | nx.DiGraph, graph_type: str) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for source, target, data in graph.edges(data=True):
        edges.append(
            {
                "source": str(source),
                "target": str(target),
                "weight": float(data.get("weight", 1.0)),
                "edge_type": str(data.get("edge_type", graph_type)),
            }
        )
    edges.sort(key=lambda edge: edge["weight"], reverse=True)
    return edges


def get_network_payload(
    app_state: Any,
    query: str | None,
    graph_type: str = GRAPH_TYPE_CO_SUBREDDIT,
    top_n: int = DEFAULT_BACKBONE_TOP_N,
    max_nodes: int = DEFAULT_MAX_RESPONSE_NODES,
) -> dict[str, Any]:
    if graph_type not in SUPPORTED_GRAPH_TYPES:
        supported = ", ".join(sorted(SUPPORTED_GRAPH_TYPES))
        raise ValueError(f"Unsupported graph_type '{graph_type}'. Supported: {supported}.")

    backbone_state = ensure_backbone_state(app_state, top_n=top_n)
    graph_bundle = backbone_state["graphs"][graph_type]
    base_graph: nx.Graph | nx.DiGraph = graph_bundle["graph"]
    base_pagerank: dict[str, float] = graph_bundle["pagerank"]
    base_communities: dict[str, int] = graph_bundle["communities"]

    matched_nodes = _lookup_matching_authors(backbone_state, query)
    matched_subgraph = base_graph.subgraph(matched_nodes).copy()
    total_nodes_before_limit = matched_subgraph.number_of_nodes()
    total_edges_before_limit = matched_subgraph.number_of_edges()

    truncated = False
    truncated_note = None
    capped_nodes = _sanitize_max_nodes(max_nodes)
    selected_nodes = set(matched_subgraph.nodes())
    apply_limit = bool(query and query.strip())
    if apply_limit and len(selected_nodes) > capped_nodes:
        ranked_nodes = sorted(
            selected_nodes,
            key=lambda node_id: base_pagerank.get(str(node_id), 0.0),
            reverse=True,
        )
        selected_nodes = set(ranked_nodes[:capped_nodes])
        truncated = True
        truncated_note = (
            f"Result limited to top {capped_nodes} nodes by PageRank. "
            f"Original match had {total_nodes_before_limit} nodes."
        )

    working_graph = matched_subgraph.subgraph(selected_nodes).copy()
    if not (query and query.strip()):
        recomputed_pagerank = base_pagerank
    else:
        recomputed_pagerank = _safe_pagerank(working_graph)

    nodes = _prepare_nodes(
        node_ids=[str(node) for node in working_graph.nodes()],
        pagerank_scores=recomputed_pagerank,
        communities=base_communities,
        profiles=backbone_state["profiles"],
    )
    edges = _prepare_edges(working_graph, graph_type=graph_type)

    return {
        "nodes": nodes,
        "edges": edges,
        "meta": {
            "graph_type": graph_type,
            "query": query.strip() if query else None,
            "top_n": int(backbone_state["top_n"]),
            "max_nodes": capped_nodes,
            "total_nodes_before_limit": int(total_nodes_before_limit),
            "total_edges_before_limit": int(total_edges_before_limit),
            "returned_nodes": len(nodes),
            "returned_edges": len(edges),
            "truncated": truncated,
            "truncation_note": truncated_note,
            "corpus_hash": str(backbone_state["corpus_hash"]),
            "computed_at": _utc_now_iso(),
            "backbone_computed_at": str(backbone_state["computed_at"]),
        },
    }
