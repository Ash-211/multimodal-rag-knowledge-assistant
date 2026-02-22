import os
from dotenv import load_dotenv
import google.genai as genai
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# --- Groq Fallback ---
_groq_client = None

def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        _groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _groq_client

GROQ_MODEL = "llama-3.1-70b-versatile"


def _build_prompt(query, text_contexts, image_contexts):
    """Build the shared prompt for both Gemini and Groq."""
    text_block = "\n\n".join(
        [f"[Text Source {i+1}]\n{ctx['content']}"
        for i, ctx in enumerate(text_contexts)]
    )

    image_block = "\n\n".join(
        [f"[Image Source {i+1}] Page {ctx['page']} -> {ctx['image_path']}"
         for i, ctx in enumerate(image_contexts)]
    )

    return f"""You are VectorMind, a smart and conversational AI assistant. The user has uploaded documents, and the relevant excerpts are provided below as context.

Your job is to be genuinely helpful. You should:
- Answer questions using the provided context as your primary source of truth
- Analyze, interpret, summarize, compare, evaluate, or give opinions about the content when asked
- Be conversational and natural — not robotic or overly cautious
- If the user asks you to do something with the document content (evaluate, critique, improve, etc.), do your best using what you have
- Only say you don't have enough information if the context truly has nothing relevant
- Cite your sources naturally, like (Text Source 1) or (Image Source 2)

TEXT CONTEXT:
{text_block}

IMAGE CONTEXT:
{image_block}

QUESTION:
{query}
"""


def generate_title(user_message):
    """Generate a short title for a conversation based on the first user message."""
    prompt = f"Generate a concise 3-6 word title for a conversation that starts with this message. Return ONLY the title, no quotes or punctuation.\n\nMessage: {user_message}\n\nTitle:"
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return response.text.strip().strip('"').strip("'")[:50]
    except Exception:
        # Fallback to Groq for title generation
        try:
            groq = _get_groq_client()
            response = groq.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
            )
            return response.choices[0].message.content.strip().strip('"').strip("'")[:50]
        except Exception:
            return "New Chat"


def decompose_query(user_query):
    prompt = f"""
Break the following user question into smaller, independent search queries.

Question:
{user_query}

Return 2–4 focused sub-queries related to the input documents, if the query can be broken down, else return a singular query.
Do NOT answer the question.
Only return the search queries.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return [q.strip("- ").strip() for q in response.text.split("\n") if q.strip()]

def generate_answer(query, text_contexts, image_contexts):
    prompt = _build_prompt(query, text_contexts, image_contexts)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception as e:
        if _is_rate_limit(e):
            return _groq_generate(prompt)
        raise


def generate_answer_stream(query, text_contexts, image_contexts):
    """Streaming version — tries Gemini first, falls back to Groq on rate limit."""
    prompt = _build_prompt(query, text_contexts, image_contexts)

    try:
        response = client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception as e:
        if _is_rate_limit(e):
            yield from _groq_generate_stream(prompt)
        else:
            raise


def _is_rate_limit(error):
    """Check if the error is a rate limit / quota error."""
    error_str = str(error).lower()
    return any(kw in error_str for kw in ["429", "quota", "rate limit", "resource exhausted"])


def _groq_generate(prompt):
    """Non-streaming Groq fallback."""
    groq = _get_groq_client()
    response = groq.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def _groq_generate_stream(prompt):
    """Streaming Groq fallback."""
    groq = _get_groq_client()
    stream = groq.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        stream=True,
    )
    for chunk in stream:
        content = chunk.choices[0].delta.content
        if content:
            yield content