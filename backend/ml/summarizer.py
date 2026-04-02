import google.generativeai as genai
import json
from core.config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

# Use Gemini 1.5 Flash for speed
model = genai.GenerativeModel('gemini-1.5-flash')

def summarize_trend(data: list[dict], query: str) -> str:
    if not data:
        return "Insufficient data to identify a trend."
    
    # Format data strictly without templates
    formatted_data = "\n".join(
        f"Date: {d.get('date')}, Post Count: {d.get('count')}, Avg Score: {d.get('avg_score'):.2f}, Avg Engagement: {d.get('avg_engagement'):.2f}"
        for d in data
    )
    
    prompt = (
        f"Analyze the following time-series data related to the search query '{query}':\n"
        f"{formatted_data}\n\n"
        "Provide a brief, plain-language description of the trend observed over time. Keep it concise."
    )
    
    try:
        response = model.generate_content(prompt)
        return response.text.replace('**', '').strip()
    except Exception as e:
        return f"Failed to summarize trend: {e}"

def generate_suggested_queries(context: str, current_query: str) -> list[str]:
    prompt = (
        f"Given the user's conversational intent regarding: '{current_query}', and the following context:\n"
        f"{context}\n\n"
        "Propose exactly 3 follow-up queries that the user could ask next to dig deeper."
        "Return them as a valid JSON list of strings."
    )
    
    try:
        response = model.generate_content(prompt)
        text = response.text
        # Naive json extraction out of markdown response
        if '```json' in text:
             text = text.split('```json')[1].split('```')[0].strip()
        parsed = json.loads(text)
        if isinstance(parsed, list):
             return [str(q) for q in parsed[:3]]
    except Exception as e:
        pass
    
    return ["What are the conflicting opinions?", "How is this evolving?", "Who are the main actors?"]
