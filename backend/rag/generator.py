import os
from dotenv import load_dotenv
import google.genai as genai
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
def decompose_query(user_query):
    prompt = f"""
Break the following user question into smaller, independent search queries.

Question:
{user_query}

Return 2–4 focused sub-queries, if the query can be broken down, else return a singular query.
Do NOT answer the question.
Only return the search queries.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )

    return [q.strip("- ").strip() for q in response.text.split("\n") if q.strip()]

def generate_answer(query, text_contexts, image_contexts):
    text_block = "\n\n".join(
        [f"[Text Source {i+1}]\n{ctx['content']}"
        for i, ctx in enumerate(text_contexts)]
    )

    image_block = "\n\n".join(
        [f"[Image Source {i+1}] Page {ctx['page']} -> {ctx['image_path']}"
         for i, ctx in enumerate(image_contexts)]
    )

    prompt = f"""
You are a multimodal AI Knowledge assistant. Use ONLY the provided context to answer the question. If the answer is not in the context, say you don't know.
Try to provide answers to the user to the best of your ability.

TEXT CONTEXT:
{text_block}

IMAGE CONTEXT:
{image_block}

QUESTION:
{query}

Provide a clear answer with references like:
(Text Source 1), (Image Source 2)
"""
    response = client.models.generate_content(
        model = "gemini-2.5-flash",
        contents=prompt
    )
    return response.text