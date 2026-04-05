import re
from typing import Any, Dict, List
from ml.embedder import embed
from core.chroma import get_chroma
from core.mongo import db
from core.schemas import SearchResult, PostDocument
from core.config import settings

_MIN_SELFTEXT_WORDS = 6
_REDDIT_POST_ID_PATTERN = re.compile(r"/comments/([a-z0-9]+)/", re.IGNORECASE)


def _canonical_post_id(chroma_id: str) -> str:
    chroma_id = str(chroma_id)
    if chroma_id.endswith("_title") or chroma_id.endswith("_body"):
        return chroma_id.rsplit("_", 1)[0]
    return chroma_id


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


def _dedup_chroma_hits(ids: list[str], distances: list[float]) -> list[tuple[str, float]]:
    best_by_post: dict[str, float] = {}
    for index, chunk_id in enumerate(ids):
        dist = 2.0
        if index < len(distances) and distances[index] is not None:
            dist = float(distances[index])

        post_id = _canonical_post_id(chunk_id)
        current = best_by_post.get(post_id)
        if current is None or dist < current:
            best_by_post[post_id] = dist

    ranked = sorted(best_by_post.items(), key=lambda item: item[1])
    return ranked


async def search(query: str, top_k: int, filters: Dict) -> List[SearchResult]:
    if not query.strip():
        return []
    
    # 1. Embed query 
    query_vector = embed([query])[0].tolist()
    
    # 2. Build Chroma Where clause
    where_clause = {}
    if "subreddit" in filters:
        where_clause["subreddit"] = filters["subreddit"]
        
    chroma_client = get_chroma()
    collection = chroma_client.get_collection(settings.CHROMA_COLLECTION)
    
    # 3. Query Chroma
    chroma_results = collection.query(
        query_embeddings=[query_vector],
        n_results=max(top_k * 3, top_k),
        where=where_clause if where_clause else None
    )
    
    if not chroma_results["ids"] or not chroma_results["ids"][0]:
        return []
        
    chunk_ids = [str(item) for item in chroma_results["ids"][0]]
    distances = [
        float(item) if item is not None else 2.0
        for item in chroma_results["distances"][0]
    ]
    dedup_hits = _dedup_chroma_hits(chunk_ids, distances)
    if not dedup_hits:
        return []

    post_ids = [post_id for post_id, _ in dedup_hits[:top_k]]
    distance_map = {post_id: dist for post_id, dist in dedup_hits}
     
    # 4. Fetch full documents from MongoDB
    # Note: Chroma returns cosine distances (closer to 0 is better if configured internally)
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

        dist = float(distance_map.get(pid, 2.0))
        ranked_candidates.append((_result_priority(selected_doc), dist, selected_doc))

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

    for _, dist, doc in ordered:
        relevance_score = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
        post = PostDocument(**doc)
        final_results.append(SearchResult(post=post, relevance_score=relevance_score))

    return final_results
