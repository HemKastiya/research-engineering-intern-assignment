"""POST /api/chat streams Gemini responses using the structured RAG pipeline."""
import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from core.schemas import ChatRequest
from ml.summarizer import build_chat_rag_payload, generate_suggested_queries, get_chat_model

router = APIRouter()


def _serialize_sources(top_documents: list[dict]) -> list[dict]:
    serialized: list[dict] = []
    for item in top_documents:
        doc = item.get("doc", {}) if isinstance(item, dict) else {}

        title = str(doc.get("title_clean") or "").strip()
        if not title:
            fallback = str(doc.get("combined_text") or "").strip()
            title = fallback[:120] if fallback else "(untitled)"

        selftext = str(doc.get("selftext_clean") or "").strip()
        if not selftext:
            selftext = str(doc.get("combined_text") or "").strip()

        created_value = (
            doc.get("created_datetime")
            or doc.get("created_date")
            or doc.get("created_utc")
            or ""
        )

        serialized.append(
            {
                "post": {
                    "id": str(doc.get("post_id") or ""),
                    "title": title,
                    "selftext_clean": selftext,
                    "subreddit": str(doc.get("subreddit") or ""),
                    "author": str(doc.get("author") or ""),
                    "created_utc": str(created_value),
                    "score": int(doc.get("score") or 0),
                },
                "relevance_score": float(item.get("rerank_score", 0.0) or 0.0),
            }
        )

    return serialized


@router.post("/")
async def process_chat(req: ChatRequest):
    history = [{"role": msg.role, "content": msg.content} for msg in req.messages]
    rag_payload = await build_chat_rag_payload(req.query, history)
    prompt = rag_payload["prompt"]
    structured_context = rag_payload.get("structured_context", "")
    sources = _serialize_sources(rag_payload.get("top_documents", []))

    async def generate():
        try:
            yield f"data: {json.dumps({'sources': sources})}\n\n"

            model = get_chat_model()
            response = model.generate_content(prompt, stream=True)

            for chunk in response:
                text = getattr(chunk, "text", None)
                if text:
                    yield f"data: {json.dumps({'content': text.replace('**', '')})}\n\n"

            suggestions = await asyncio.to_thread(
                generate_suggested_queries,
                structured_context,
                req.query,
                rag_payload.get("top_documents", []),
            )
            yield f"data: {json.dumps({'suggested_queries': suggestions})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
