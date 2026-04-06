import re
from typing import Any, Dict, List
from ml.embedder import embed
from core.pinecone import get_pinecone_index, get_pinecone_namespace
from core.mongo import db
from core.schemas import SearchResult, PostDocument

_MIN_SELFTEXT_WORDS = 6
_REDDIT_POST_ID_PATTERN = re.compile(r"/comments/([a-z0-9]+)/", re.IGNORECASE)


def _canonical_post_id(chroma_id: str) -> str:
    chroma_id = str(chroma_id)
    if chroma_id.endswith("_title") or chroma_id.endswith("_body"):
        return chroma_id.rsplit("_", 1)[0]
    return chroma_id


def _match_id(match: Any) -> str:
    if isinstance(match, dict):
        return str(match.get("id") or "")
    return str(getattr(match, "id", "") or "")


def _match_score(match: Any) -> float:
    if isinstance(match, dict):
        return float(match.get("score") or 0.0)
    return float(getattr(match, "score", 0.0) or 0.0)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _has_own_selftext(doc: dict[str, Any]) -> bool:
    selftext = _clean_text(doc.get("selftext_clean"))
    if not selftext:
        return False
    return len(selftext.split()) >= _MIN_SELFTEXT_WORDS


def _extract_referenced_post_id(doc: dict[str, Any]) -> str | None:
    explicit_reference = _clean_text(doc.get("crosspost_parent_post_id"))
    if explicit_reference:
        return explicit_reference

    crosspost_parent = _clean_text(doc.get("crosspost_parent"))
    if crosspost_parent.startswith("t3_") and len(crosspost_parent) > 3:
        return crosspost_parent[3:]

    for field in ("external_url", "normalized_external_url", "url"):
        value = _clean_text(doc.get(field))
        if not value:
            continue
        match = _REDDIT_POST_ID_PATTERN.search(value)
        if match:
            return match.group(1)

    return None


def _should_resolve_to_reference(doc: dict[str, Any]) -> bool:
    return _extract_referenced_post_id(doc) is not None or not _has_own_selftext(doc)


def _result_priority(doc: dict[str, Any]) -> int:
    # Priority 0 is preferred: posts with their own self-text and no references.
    return 0 if _has_own_selftext(doc) and _extract_referenced_post_id(doc) is None else 1


def _normalize_similarity(score: float) -> float:
    try:
        value = float(score)
    except Exception:
        return 0.0
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return value


def _dedup_hits(ids: list[str], scores: list[float]) -> list[tuple[str, float]]:
    best_by_post: dict[str, float] = {}
    for index, chunk_id in enumerate(ids):
        score = 0.0
        if index < len(scores) and scores[index] is not None:
            score = float(scores[index])

        post_id = _canonical_post_id(chunk_id)
        current = best_by_post.get(post_id)
        if current is None or score > current:
            best_by_post[post_id] = score

    ranked = sorted(best_by_post.items(), key=lambda item: item[1], reverse=True)
    return ranked


async def search(query: str, top_k: int, filters: Dict) -> List[SearchResult]:
    if not query.strip():
        return []
    
    # 1. Embed query 
    query_vector = embed([query])[0].tolist()
    
    # 2. Build Pinecone filter clause
    where_clause = {}
    if "subreddit" in filters:
        where_clause["subreddit"] = {"$eq": filters["subreddit"]}
        
    index = get_pinecone_index()
    namespace = get_pinecone_namespace()
    
    # 3. Query Pinecone
    pinecone_results = index.query(
        namespace=namespace,
        vector=query_vector,
        top_k=max(top_k * 3, top_k),
        filter=where_clause if where_clause else None,
        include_values=False,
        include_metadata=False,
    )

    if isinstance(pinecone_results, dict):
        matches = pinecone_results.get("matches") or []
    else:
        matches = getattr(pinecone_results, "matches", []) or []

    if not matches:
        return []
        
    chunk_ids = [_match_id(match) for match in matches]
    scores = [_match_score(match) for match in matches]
    dedup_hits = _dedup_hits(chunk_ids, scores)
    if not dedup_hits:
        return []

    post_ids = [post_id for post_id, _ in dedup_hits[:top_k]]
    score_map = {post_id: score for post_id, score in dedup_hits}
     
    # 4. Fetch full documents from MongoDB
    # Pinecone returns similarity scores (higher is better for cosine).
    cursor = db.posts.find({"post_id": {"$in": post_ids}})
    docs_list = await cursor.to_list(length=len(post_ids))

    doc_map = {str(doc["post_id"]): doc for doc in docs_list}

    # If a result references another post (crosspost/link), or has no self-text,
    # we try to replace it with the referenced post document.
    referenced_post_ids: set[str] = set()
    for pid in post_ids:
        doc = doc_map.get(pid)
        if not doc or not _should_resolve_to_reference(doc):
            continue

        referenced_id = _extract_referenced_post_id(doc)
        if not referenced_id or referenced_id == pid or referenced_id in doc_map:
            continue

        referenced_post_ids.add(referenced_id)

    if referenced_post_ids:
        referenced_cursor = db.posts.find({"post_id": {"$in": list(referenced_post_ids)}})
        referenced_docs = await referenced_cursor.to_list(length=len(referenced_post_ids))
        for referenced_doc in referenced_docs:
            doc_map[str(referenced_doc["post_id"])] = referenced_doc

    # 5. Build final result list: prioritize posts with original self-text,
    # and substitute referenced post docs when needed.
    ranked_candidates: list[tuple[int, float, dict[str, Any]]] = []
    final_results = []

    for pid in post_ids:
        source_doc = doc_map.get(pid)
        if not source_doc:
            continue

        selected_doc = source_doc
        if _should_resolve_to_reference(source_doc):
            referenced_id = _extract_referenced_post_id(source_doc)
            if referenced_id and referenced_id != pid and referenced_id in doc_map:
                selected_doc = doc_map[referenced_id]

        score = float(score_map.get(pid, 0.0))
        ranked_candidates.append((_result_priority(selected_doc), -score, selected_doc))

    if not ranked_candidates:
        return []

    # Remove duplicates after substitution while preserving best rank.
    best_by_post_id: dict[str, tuple[int, float, dict[str, Any]]] = {}
    for priority, dist, doc in ranked_candidates:
        current_post_id = str(doc.get("post_id", ""))
        if not current_post_id:
            continue
        previous = best_by_post_id.get(current_post_id)
        if previous is None or (priority, dist) < (previous[0], previous[1]):
            best_by_post_id[current_post_id] = (priority, dist, doc)

    ordered = sorted(best_by_post_id.values(), key=lambda item: (item[0], item[1]))[:top_k]

    for _, neg_score, doc in ordered:
        relevance_score = _normalize_similarity(-neg_score)
        post = PostDocument(**doc)
        final_results.append(SearchResult(post=post, relevance_score=relevance_score))

    return final_results
