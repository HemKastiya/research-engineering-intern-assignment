"""POST /api/chat — body: {messages: [], query: str}. Runs semantic search → builds RAG context → streams Gemini response via SSE."""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from core.schemas import ChatRequest
from ml.semantic_search import search
from ml.summarizer import generate_suggested_queries
import google.generativeai as genai
from core.config import settings
import json

router = APIRouter()

@router.post("/")
async def process_chat(req: ChatRequest):
    # Retrieve Context 
    results = await search(req.query, top_k=5, filters={})
    
    context = "\n---\n".join([r.post.combined_text for r in results])
    
    # Simple SSE generator logic
    async def generate():
        genai.configure(api_key=settings.GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = (
            f"Given context documents:\n{context}\n\n"
            f"Answer the user query: '{req.query}'\n"
        )
        
        try:
             response = model.generate_content(prompt, stream=True)
             for chunk in response:
                  if chunk.text:
                       yield f"data: {json.dumps({'content': chunk.text.replace('**', '')})}\n\n"
                       
             # Emit suggestions
             suggestions = generate_suggested_queries(context, req.query)
             yield f"data: {json.dumps({'suggested_queries': suggestions})}\n\n"
             
        except Exception as e:
             yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
    return StreamingResponse(generate(), media_type="text/event-stream")
