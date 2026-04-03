"""POST /api/chat streams Gemini responses using the structured RAG pipeline."""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json

from core.schemas import ChatRequest
from ml.summarizer import build_chat_rag_payload, get_chat_model

router = APIRouter()


@router.post("/")
async def process_chat(req: ChatRequest):
    history = [{"role": msg.role, "content": msg.content} for msg in req.messages]
    rag_payload = await build_chat_rag_payload(req.query, history)
    prompt = rag_payload["prompt"]
    suggestions = rag_payload["suggested_queries"]

    async def generate():
        try:
            model = get_chat_model()
            response = model.generate_content(prompt, stream=True)
            for chunk in response:
                text = getattr(chunk, "text", None)
                if text:
                    yield f"data: {json.dumps({'content': text.replace('**', '')})}\n\n"

            yield f"data: {json.dumps({'suggested_queries': suggestions})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
