"""
LLM wrapper. Supports Groq (recommended - fast & free) and Gemini.
Both have generous free tiers, no credit card needed.
"""
import os
from dotenv import load_dotenv

load_dotenv()

PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()


def _groq_client():
    from groq import Groq
    return Groq(api_key=os.getenv("GROQ_API_KEY"))


def _gemini_model():
    import google.generativeai as genai
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    return genai.GenerativeModel("gemini-1.5-flash")


def generate(prompt: str, max_tokens: int = 600) -> str:
    """Single generate call. Keep it simple — RAG does the heavy lifting."""
    if PROVIDER == "groq":
        client = _groq_client()
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.1,  # low temp = less hallucination
        )
        return resp.choices[0].message.content.strip()

    elif PROVIDER == "gemini":
        model = _gemini_model()
        resp = model.generate_content(
            prompt,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": 0.1,
            },
        )
        return resp.text.strip()

    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {PROVIDER}")
