from __future__ import annotations

import asyncio
import json
import math
import re
from collections import Counter
from functools import lru_cache
from typing import Any, Sequence

import google.generativeai as genai

from core.pinecone import get_pinecone_index, get_pinecone_namespace
from core.config import settings
from core.mongo import db
from ml.embedder import embed

CHAT_MODEL_NAME = "gemini-2.5-flash"
HYBRID_TOP_K = 30
RERANK_TOP_K = 8
RRF_K = 60
BM25_K1 = 1.5
BM25_B = 0.75
MAX_DOC_CHARS_FOR_SCORING = 8000
MAX_DOC_CHARS_FOR_CONTEXT = 600
MAX_CONTEXT_CHARS = 16000

TOKEN_RE = re.compile(r"\b\w{2,}\b", re.UNICODE)

STOPWORDS = {"a", "an", "and","are", "as", "at", "be", "by", "for", "from", "has", "have", "how",
    "in", "is", "it", "its", "of", "on", "or", "that", "the", "this", "to", "was",
    "were", "what", "when", "where", "which", "who", "why", "with", "you", "your",
    "about", "into", "over", "under", "after", "before", "between","than", "then", "they","their","them",
}


@lru_cache(maxsize=1)
def get_chat_model():
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(CHAT_MODEL_NAME)


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _normalize_text(value: str) -> str:
    return " ".join(_safe_text(value).split()).strip()


def _tokenize(value: str) -> list[str]:
    tokens = [token.casefold() for token in TOKEN_RE.findall(_safe_text(value))]
    normalized_tokens: list[str] = []

    for token in tokens:
        if not any(ch.isalnum() for ch in token):
            continue
        # Keep stopword filtering scoped to ASCII tokens so multilingual
        # terms are preserved for lexical/BM25 scoring.
        if token.isascii() and token in STOPWORDS:
            continue
        normalized_tokens.append(token)

    return normalized_tokens


def _extract_history_context(messages: Sequence[dict[str, str]] | None) -> str:
    if not messages:
        return ""
    user_messages = [
        _normalize_text(msg.get("content", ""))
        for msg in messages
        if _safe_text(msg.get("role", "")).lower() == "user"
    ]
    user_messages = [msg for msg in user_messages if msg]
    if not user_messages:
        return ""
    return user_messages[-1]


def _canonical_post_id(chunk_id: str) -> str:
    chunk_id = _safe_text(chunk_id)
    if chunk_id.endswith("_title") or chunk_id.endswith("_body"):
        return chunk_id.rsplit("_", 1)[0]
    return chunk_id


def expand_query(query: str, messages: Sequence[dict[str, str]] | None = None) -> list[str]:
    original = _normalize_text(query)
    if not original:
        return []

    expansions: list[str] = [original]
    query_terms = _tokenize(original)

    if query_terms:
        keyword_query = " ".join(query_terms[:8])
        if keyword_query and keyword_query != original:
            expansions.append(keyword_query)

    if len(query_terms) >= 3:
        high_signal = " ".join(
            sorted(set(query_terms), key=lambda term: (-query_terms.count(term), len(term)))[:6]
        )
        if high_signal and high_signal not in expansions:
            expansions.append(high_signal)

    history_context = _extract_history_context(messages)
    if history_context:
        history_terms = _tokenize(history_context)
        carry_terms = [term for term in history_terms if term not in query_terms][:4]
        if carry_terms:
            contextual = _normalize_text(f"{original} {' '.join(carry_terms)}")
            if contextual and contextual not in expansions:
                expansions.append(contextual)

    deduped: list[str] = []
    seen = set()
    for item in expansions:
        normalized = item.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(item)

    return deduped[:4]


def _bm25_score_documents(query_terms: list[str], docs: dict[str, dict[str, Any]]) -> dict[str, float]:
    if not query_terms or not docs:
        return {}

    corpus_tokens: dict[str, list[str]] = {}
    document_frequency: Counter[str] = Counter()
    total_length = 0

    for post_id, doc in docs.items():
        title = _safe_text(doc.get("title_clean", ""))
        body = _safe_text(doc.get("selftext_clean") or doc.get("combined_text", ""))
        if len(body) > MAX_DOC_CHARS_FOR_SCORING:
            body = body[:MAX_DOC_CHARS_FOR_SCORING]

        tokens = _tokenize(f"{title} {body}")
        corpus_tokens[post_id] = tokens
        total_length += len(tokens)
        for token in set(tokens):
            document_frequency[token] += 1

    if not corpus_tokens:
        return {}

    n_docs = len(corpus_tokens)
    avg_doc_len = max(total_length / max(n_docs, 1), 1.0)
    valid_terms = [term for term in query_terms if term in document_frequency]
    if not valid_terms:
        return {post_id: 0.0 for post_id in corpus_tokens}

    idf: dict[str, float] = {}
    for term in set(valid_terms):
        df = document_frequency[term]
        idf[term] = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))

    bm25_scores: dict[str, float] = {}
    for post_id, tokens in corpus_tokens.items():
        tf = Counter(tokens)
        doc_len = max(len(tokens), 1)
        score = 0.0

        for term in valid_terms:
            freq = tf.get(term, 0)
            if freq <= 0:
                continue

            numerator = freq * (BM25_K1 + 1.0)
            denominator = freq + BM25_K1 * (1.0 - BM25_B + BM25_B * (doc_len / avg_doc_len))
            score += idf[term] * (numerator / max(denominator, 1e-9))

        bm25_scores[post_id] = score

    return bm25_scores


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


def _match_id(match: Any) -> str:
    if isinstance(match, dict):
        return str(match.get("id") or "")
    return str(getattr(match, "id", "") or "")


def _match_score(match: Any) -> float:
    if isinstance(match, dict):
        return float(match.get("score") or 0.0)
    return float(getattr(match, "score", 0.0) or 0.0)


def _dedup_hits(ids: list[str], scores: list[float]) -> list[tuple[str, float]]:
    best_by_post: dict[str, tuple[str, float, int]] = {}

    for index, chunk_id in enumerate(ids, start=1):
        score = 0.0
        if index - 1 < len(scores) and scores[index - 1] is not None:
            score = float(scores[index - 1])

        post_id = _canonical_post_id(chunk_id)
        current = best_by_post.get(post_id)
        if current is None or score > current[1]:
            best_by_post[post_id] = (chunk_id, score, index)

    ranked = sorted(best_by_post.items(), key=lambda item: (-item[1][1], item[1][2]))
    return [(post_id, value[1]) for post_id, value in ranked]


async def _dense_retrieve(expanded_queries: list[str], per_query_limit: int = 20) -> dict[str, dict[str, float]]:
    if not expanded_queries:
        return {}

    query_embeddings = await asyncio.to_thread(embed, expanded_queries)
    query_embedding_list = query_embeddings.tolist()

    namespace = get_pinecone_namespace()

    async def _query_one(vector: list[float]) -> Any:
        def _call() -> Any:
            index = get_pinecone_index()
            return index.query(
                namespace=namespace,
                vector=vector,
                top_k=per_query_limit,
                include_metadata=False,
                include_values=False,
            )

        return await asyncio.to_thread(_call)

    results = await asyncio.gather(
        *[_query_one(vector) for vector in query_embedding_list],
        return_exceptions=True,
    )

    dense_signals: dict[str, dict[str, float]] = {}
    for result in results:
        if isinstance(result, Exception):
            continue

        if isinstance(result, dict):
            matches = result.get("matches") or []
        else:
            matches = getattr(result, "matches", []) or []

        if not matches:
            continue

        ids = [_match_id(match) for match in matches]
        scores = [_match_score(match) for match in matches]
        dedup_hits = _dedup_hits(ids, scores)

        for rank_index, (post_id, score) in enumerate(dedup_hits, start=1):
            similarity = _normalize_similarity(score)
            signal = dense_signals.setdefault(
                post_id,
                {"dense_similarity": 0.0, "dense_rank": float(rank_index), "dense_rrf": 0.0},
            )

            if similarity > signal["dense_similarity"]:
                signal["dense_similarity"] = similarity
            if rank_index < signal["dense_rank"]:
                signal["dense_rank"] = float(rank_index)
            signal["dense_rrf"] += 1.0 / (RRF_K + rank_index)

    return dense_signals


async def _fetch_lexical_candidates(expanded_queries: list[str], per_query_limit: int = 40) -> dict[str, dict[str, Any]]:
    if not expanded_queries:
        return {}

    async def _search_one(search_query: str) -> list[dict[str, Any]]:
        pipeline = [
            {"$match": {"$text": {"$search": search_query}}},
            {
                "$project": {
                    "post_id": 1,
                    "title_clean": 1,
                    "selftext_clean": 1,
                    "combined_text": 1,
                    "full_permalink": 1,
                    "subreddit": 1,
                    "author": 1,
                    "created_datetime": 1,
                    "created_date": 1,
                    "score": 1,
                    "text_score": {"$meta": "textScore"},
                }
            },
            {"$sort": {"text_score": {"$meta": "textScore"}}},
            {"$limit": per_query_limit},
        ]
        cursor = db.posts.aggregate(pipeline)
        return await cursor.to_list(length=per_query_limit)

    results = await asyncio.gather(
        *[_search_one(expanded_query) for expanded_query in expanded_queries],
        return_exceptions=True,
    )

    candidate_docs: dict[str, dict[str, Any]] = {}
    for result in results:
        if isinstance(result, Exception):
            continue

        for doc in result:
            post_id = str(doc.get("post_id", ""))
            if not post_id:
                continue

            existing = candidate_docs.get(post_id)
            if existing is None:
                candidate_docs[post_id] = doc
            else:
                new_score = float(doc.get("text_score", 0.0) or 0.0)
                old_score = float(existing.get("text_score", 0.0) or 0.0)
                if new_score > old_score:
                    candidate_docs[post_id] = doc

    return candidate_docs


def _rank_dict(values: dict[str, float], descending: bool = True) -> dict[str, int]:
    sorted_items = sorted(values.items(), key=lambda kv: kv[1], reverse=descending)
    return {post_id: rank for rank, (post_id, _) in enumerate(sorted_items, start=1)}


def _fuse_dense_and_bm25(
    dense_signals: dict[str, dict[str, float]],
    bm25_scores: dict[str, float],
) -> dict[str, dict[str, float]]:
    dense_rrf_map = {post_id: signal.get("dense_rrf", 0.0) for post_id, signal in dense_signals.items()}
    bm25_rank_map = _rank_dict(bm25_scores, descending=True)

    fused: dict[str, dict[str, float]] = {}
    all_ids = set(dense_signals.keys()) | set(bm25_scores.keys())

    for post_id in all_ids:
        dense_similarity = dense_signals.get(post_id, {}).get("dense_similarity", 0.0)
        dense_rrf = dense_rrf_map.get(post_id, 0.0)

        bm25_score = bm25_scores.get(post_id, 0.0)
        bm25_rank = bm25_rank_map.get(post_id)
        bm25_rrf = (1.0 / (RRF_K + bm25_rank)) if bm25_rank else 0.0

        hybrid_score = 0.60 * dense_rrf + 0.40 * bm25_rrf

        fused[post_id] = {
            "dense_similarity": dense_similarity,
            "dense_rrf": dense_rrf,
            "bm25_score": bm25_score,
            "bm25_rrf": bm25_rrf,
            "hybrid_score": hybrid_score,
        }

    return fused


async def _fetch_documents_by_ids(
    post_ids: list[str],
    lexical_docs: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    docs_by_id: dict[str, dict[str, Any]] = {
        post_id: doc for post_id, doc in lexical_docs.items() if post_id in post_ids
    }
    missing_ids = [post_id for post_id in post_ids if post_id not in docs_by_id]

    if missing_ids:
        projection = {
            "post_id": 1,
            "title_clean": 1,
            "selftext_clean": 1,
            "combined_text": 1,
            "full_permalink": 1,
            "subreddit": 1,
            "author": 1,
            "created_datetime": 1,
            "created_date": 1,
            "score": 1,
        }
        cursor = db.posts.find({"post_id": {"$in": missing_ids}}, projection)
        missing_docs = await cursor.to_list(length=len(missing_ids))

        for doc in missing_docs:
            post_id = str(doc.get("post_id", ""))
            if post_id:
                docs_by_id[post_id] = doc

    return docs_by_id


def _minmax_norm(value: float, values: list[float]) -> float:
    if not values:
        return 0.0
    min_value = min(values)
    max_value = max(values)
    if max_value <= min_value:
        return 0.0
    return (value - min_value) / (max_value - min_value)


def _term_overlap_score(query_terms: list[str], doc_text: str) -> float:
    if not query_terms:
        return 0.0
    doc_terms = set(_tokenize(doc_text))
    if not doc_terms:
        return 0.0
    query_term_set = set(query_terms)
    return len(query_term_set & doc_terms) / max(len(query_term_set), 1)


def _rerank_documents(
    query: str,
    top_post_ids: list[str],
    docs_by_id: dict[str, dict[str, Any]],
    fused_scores: dict[str, dict[str, float]],
    rerank_top_k: int = RERANK_TOP_K,
) -> list[dict[str, Any]]:
    query_terms = _tokenize(query)
    query_norm = _normalize_text(query).lower()

    dense_values = [fused_scores.get(post_id, {}).get("dense_similarity", 0.0) for post_id in top_post_ids]
    bm25_values = [fused_scores.get(post_id, {}).get("bm25_score", 0.0) for post_id in top_post_ids]
    hybrid_values = [fused_scores.get(post_id, {}).get("hybrid_score", 0.0) for post_id in top_post_ids]

    scored: list[dict[str, Any]] = []
    for post_id in top_post_ids:
        doc = docs_by_id.get(post_id)
        if not doc:
            continue

        title = _safe_text(doc.get("title_clean", ""))
        body = _safe_text(doc.get("selftext_clean") or doc.get("combined_text", ""))
        if len(body) > MAX_DOC_CHARS_FOR_SCORING:
            body = body[:MAX_DOC_CHARS_FOR_SCORING]
        full_text = f"{title} {body}".strip()

        signal = fused_scores.get(post_id, {})
        dense_similarity = float(signal.get("dense_similarity", 0.0))
        bm25_score = float(signal.get("bm25_score", 0.0))
        hybrid_score = float(signal.get("hybrid_score", 0.0))

        dense_norm = _minmax_norm(dense_similarity, dense_values)
        bm25_norm = _minmax_norm(bm25_score, bm25_values)
        hybrid_norm = _minmax_norm(hybrid_score, hybrid_values)
        overlap = _term_overlap_score(query_terms, full_text)

        phrase_boost = 0.08 if query_norm and query_norm in full_text.lower() else 0.0
        title_overlap = _term_overlap_score(query_terms, title)
        title_boost = 0.07 * title_overlap

        rerank_score = (
            0.40 * hybrid_norm
            + 0.25 * dense_norm
            + 0.20 * bm25_norm
            + 0.15 * overlap
            + phrase_boost
            + title_boost
        )

        scored.append(
            {
                "post_id": post_id,
                "doc": doc,
                "dense_similarity": dense_similarity,
                "bm25_score": bm25_score,
                "hybrid_score": hybrid_score,
                "rerank_score": rerank_score,
            }
        )

    scored.sort(key=lambda item: item["rerank_score"], reverse=True)

    desired_k = min(max(5, rerank_top_k), 10)
    if len(scored) <= desired_k:
        return scored
    return scored[:desired_k]


def _format_doc_for_context(query: str, doc: dict[str, Any], index: int) -> str:
    del query  # Query is currently unused, kept for future formatting variants.

    post_id = _safe_text(doc.get("post_id", ""))
    title = _normalize_text(_safe_text(doc.get("title_clean", "")))

    body = _safe_text(doc.get("selftext_clean") or doc.get("combined_text", ""))
    body = _normalize_text(body)
    if len(body) > MAX_DOC_CHARS_FOR_CONTEXT:
        body = body[:MAX_DOC_CHARS_FOR_CONTEXT]

    subreddit = _safe_text(doc.get("subreddit", ""))
    author = _safe_text(doc.get("author", ""))
    date = _safe_text(doc.get("created_date", ""))
    score = _safe_text(doc.get("score", ""))
    url = _safe_text(doc.get("full_permalink", ""))

    return (
        f"[{index}] {title}\n"
        f"post_id: {post_id}\n"
        f"r/{subreddit} | u/{author} | {date} | score: {score}\n"
        f"url: {url}\n"
        f"{body}\n"
    )


def _build_structured_context(
    query: str,
    expanded_queries: list[str],
    reranked_docs: list[dict[str, Any]],
) -> str:
    if not reranked_docs:
        return (
            f"Query: {query}\n"
            "No relevant documents found in the dataset for this query."
        )

    evidence_blocks: list[str] = []
    for index, item in enumerate(reranked_docs, start=1):
        evidence_blocks.append(_format_doc_for_context(query, item["doc"], index))

    context = "\n---\n".join(evidence_blocks)
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS]

    return (
        "## Query\n"
        f"{query}\n\n"
        "## Query Expansion\n"
        f"{', '.join(expanded_queries)}\n\n"
        "## Evidence Documents\n"
        f"{context}"
    )


def _format_chat_history(messages: Sequence[dict[str, str]] | None) -> str:
    if not messages:
        return "No prior chat history."

    trimmed = messages[-6:]
    lines: list[str] = []
    for msg in trimmed:
        role = _safe_text(msg.get("role", "user")).strip().lower()
        role_label = "User" if role == "user" else "Assistant"
        content = _normalize_text(msg.get("content", ""))
        if not content:
            continue
        lines.append(f"{role_label}: {content[:500]}")

    if not lines:
        return "No prior chat history."
    return "\n".join(lines)


def build_rag_answer_prompt(
    query: str,
    structured_context: str,
    messages: Sequence[dict[str, str]] | None = None,
) -> str:
    history = _format_chat_history(messages)
    return (
        "You are an investigative analyst for a Reddit research dashboard.\n"
        "Answer ONLY using the numbered evidence documents below.\n"
        "Every factual claim MUST end with a bracketed citation like [1] or [2,3].\n"
        "If you cannot find evidence for a claim, say 'Not found in current dataset.'\n"
        "Do not speculate beyond the evidence.\n\n"
        f"## Conversation history\n{history}\n\n"
        f"## User query\n{_normalize_text(query)}\n\n"
        f"## Evidence documents\n{structured_context}\n\n"
        "## Your response (required format)\n"
        "**Direct answer** (2-3 sentences with citations):\n\n"
        "**Key findings**:\n"
        "- finding one [citation]\n"
        "- finding two [citation]\n"
        "- finding three [citation]\n\n"
        "**Confidence**: High / Medium / Low - one sentence explaining why.\n"
    )


def _strip_markdown_fence(text: str) -> str:
    cleaned = _safe_text(text).strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        parts = cleaned.split("\n", 1)
        if len(parts) == 2:
            cleaned = parts[1]
    if cleaned.endswith("```"):
        cleaned = cleaned.rsplit("```", 1)[0]
    return cleaned.strip()


def _parse_json_array_of_strings(text: str) -> list[str]:
    candidate = _strip_markdown_fence(text)
    try:
        parsed = json.loads(candidate)
    except Exception:
        return []

    if not isinstance(parsed, list):
        return []

    output: list[str] = []
    for item in parsed:
        value = _normalize_text(_safe_text(item))
        if len(value) < 10:
            continue
        output.append(value)
        if len(output) >= 3:
            break

    return output


def _parse_question_lines(text: str) -> list[str]:
    suggestions: list[str] = []
    for line in _safe_text(text).splitlines():
        stripped = line.strip()
        if stripped.startswith("?"):
            candidate = stripped.lstrip("?").strip()
        elif stripped.startswith("-"):
            candidate = stripped.lstrip("-").strip()
        else:
            candidate = stripped

        if "?" not in candidate:
            continue

        if len(candidate) < 10:
            continue

        if candidate not in suggestions:
            suggestions.append(candidate)
        if len(suggestions) >= 3:
            break

    return suggestions


def _fallback_suggestions(current_query: str) -> list[str]:
    return [
        f"What changed over time for '{current_query}'?",
        f"Which subreddits are driving discussion about '{current_query}'?",
        f"What opposing viewpoints appear for '{current_query}'?",
    ]


def generate_suggested_queries(
    context: str,
    current_query: str,
    reranked_docs: Sequence[dict[str, Any]] | None = None,
) -> list[str]:
    del reranked_docs

    prompt = (
        "Generate exactly 3 follow-up questions grounded in the retrieved evidence.\n"
        "Rules:\n"
        "- Focus on investigative depth and unresolved evidence gaps.\n"
        "- Keep each question specific and answerable from dataset exploration.\n"
        "- Return ONLY a JSON array of 3 strings.\n\n"
        f"Current query: {current_query}\n\n"
        f"Retrieved evidence:\n{context[:7000]}"
    )

    try:
        response = get_chat_model().generate_content(prompt)
        text = _safe_text(response.text)

        suggestions = _parse_json_array_of_strings(text)
        if suggestions:
            return suggestions

        suggestions = _parse_question_lines(text)
        if suggestions:
            return suggestions[:3]
    except Exception:
        pass

    return _fallback_suggestions(current_query)


async def build_chat_rag_payload(
    query: str,
    messages: Sequence[dict[str, str]] | None = None,
) -> dict[str, Any]:
    expanded_queries = expand_query(query, messages)
    if not expanded_queries:
        empty_context = "No usable query was provided."
        return {
            "expanded_queries": [],
            "top_documents": [],
            "structured_context": empty_context,
            "prompt": build_rag_answer_prompt(query, empty_context, messages),
            "debug": {"retrieval_scores": []},
        }

    dense_task = asyncio.create_task(_dense_retrieve(expanded_queries, per_query_limit=24))
    lexical_task = asyncio.create_task(_fetch_lexical_candidates(expanded_queries, per_query_limit=40))
    dense_signals, lexical_candidates = await asyncio.gather(dense_task, lexical_task)

    query_terms = _tokenize(" ".join(expanded_queries))
    bm25_scores = _bm25_score_documents(query_terms, lexical_candidates)
    fused_scores = _fuse_dense_and_bm25(dense_signals, bm25_scores)

    ranked_by_hybrid = sorted(
        fused_scores.items(),
        key=lambda kv: (
            kv[1].get("hybrid_score", 0.0),
            kv[1].get("dense_similarity", 0.0),
            kv[1].get("bm25_score", 0.0),
        ),
        reverse=True,
    )
    top_30_ids = [post_id for post_id, _ in ranked_by_hybrid[:HYBRID_TOP_K]]

    docs_by_id = await _fetch_documents_by_ids(top_30_ids, lexical_candidates)
    reranked_docs = _rerank_documents(query, top_30_ids, docs_by_id, fused_scores, rerank_top_k=RERANK_TOP_K)

    structured_context = _build_structured_context(query, expanded_queries, reranked_docs)
    prompt = build_rag_answer_prompt(query, structured_context, messages)

    return {
        "expanded_queries": expanded_queries,
        "top_documents": reranked_docs,
        "structured_context": structured_context,
        "prompt": prompt,
        "debug": {
            "retrieval_scores": [
                {
                    "post_id": item["post_id"],
                    "hybrid": round(item["hybrid_score"], 4),
                    "dense": round(item["dense_similarity"], 4),
                    "bm25": round(item["bm25_score"], 4),
                    "rerank": round(item["rerank_score"], 4),
                }
                for item in reranked_docs
            ]
        },
    }


def summarize_trend(data: list[dict[str, Any]], query: str) -> str:
    if not data:
        return "Insufficient data to identify a trend."

    formatted_data = "\n".join(
        (
            f"Date: {d.get('date')}, "
            f"Post Count: {d.get('count')}, "
            f"Avg Score: {float(d.get('avg_score', 0.0)):.2f}, "
            f"Avg Engagement: {float(d.get('avg_engagement', 0.0)):.2f}"
        )
        for d in data
    )

    prompt = (
        f"Analyze the following time-series data related to '{query}':\n"
        f"{formatted_data}\n\n"
        "Provide a concise plain-language summary of the trend."
    )

    try:
        response = get_chat_model().generate_content(prompt)
        return _safe_text(response.text).replace("**", "").strip()
    except Exception as exc:
        return f"Failed to summarize trend: {exc}"
