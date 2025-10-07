import os
from typing import List, Tuple
from decouple import config
from django.db import connection

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

import requests

EMBEDDING_PROVIDER = config("EMBEDDING_PROVIDER", default="openai")  # openai | fireworks

# OpenAI config (used if provider=openai)
EMBEDDING_MODEL = config("OPENAI_EMBEDDING_MODEL", default="text-embedding-3-small")
CHAT_MODEL = config("OPENAI_CHAT_MODEL", default="gpt-4o-mini")
OPENAI_API_KEY = config("OPENAI_API_KEY", default=None)
import os
from typing import List, Tuple
from decouple import config
from django.db import connection

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

import requests

EMBEDDING_PROVIDER = config("EMBEDDING_PROVIDER", default="openai")  # openai | fireworks

# OpenAI config (used if provider=openai)
EMBEDDING_MODEL = config("OPENAI_EMBEDDING_MODEL", default="text-embedding-3-small")
CHAT_MODEL = config("OPENAI_CHAT_MODEL", default="gpt-4o-mini")
OPENAI_API_KEY = config("OPENAI_API_KEY", default=None)

import os
from typing import List, Tuple
from decouple import config
from django.db import connection

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

import requests

EMBEDDING_PROVIDER = config("EMBEDDING_PROVIDER", default="openai")  # openai | fireworks

# OpenAI config (used if provider=openai)
EMBEDDING_MODEL = config("OPENAI_EMBEDDING_MODEL", default="text-embedding-3-small")
CHAT_MODEL = config("OPENAI_CHAT_MODEL", default="gpt-4o-mini")
OPENAI_API_KEY = config("OPENAI_API_KEY", default=None)

# Fireworks config (used if provider=fireworks)
FIREWORKS_API_KEY = config("FIREWORKS_API_KEY", default=None)
FIREWORKS_EMBEDDING_MODEL = config("FIREWORKS_EMBEDDING_MODEL", default="nomic-ai/nomic-embed-text-v1.5")
# IMPORTANT: Set this to match your pgvector dimension used to store job embeddings
FIREWORKS_EMBEDDING_DIM = config("FIREWORKS_EMBEDDING_DIM", default=None, cast=int)
FIREWORKS_BASE_URL = config("FIREWORKS_BASE_URL", default="https://api.fireworks.ai/inference/v1")


def chunk_text(text: str, chunk_chars: int = 1200, overlap: int = 100) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_chars, n)
        chunks.append(text[start:end])
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks


def get_openai_client():
    if OpenAI is None:
        raise RuntimeError("openai library not installed")
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=OPENAI_API_KEY)


def embed_text_openai(text: str) -> List[float]:
    client = get_openai_client()
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return resp.data[0].embedding


def embed_text_fireworks(text: str) -> List[float]:
    if not FIREWORKS_API_KEY:
        raise RuntimeError("FIREWORKS_API_KEY is not set")
    url = f"{FIREWORKS_BASE_URL}/embeddings"
    payload = {
        "input": text,
        "model": FIREWORKS_EMBEDDING_MODEL,
    }
    if FIREWORKS_EMBEDDING_DIM:
        payload["dimensions"] = FIREWORKS_EMBEDDING_DIM
    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json",
    }
    # Try the request. If the service returns a 5xx and we included an
    # explicit `dimensions` field, retry once without it (some models do
    # not expect or accept the dimensions parameter).
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
    except Exception as e:
        raise RuntimeError(f"Fireworks request failed: {e}")

    if not r.ok and FIREWORKS_EMBEDDING_DIM and r.status_code >= 500:
        # Retry without dimensions
        try:
            payload2 = {"input": text, "model": FIREWORKS_EMBEDDING_MODEL}
            r2 = requests.post(url, json=payload2, headers=headers, timeout=30)
        except Exception as e:
            raise RuntimeError(f"Fireworks request failed on retry: {e}")
        if not r2.ok:
            body = None
            try:
                body = r2.text
            except Exception:
                body = "<unreadable response body>"
            raise RuntimeError(f"Fireworks embedding error (retry): status={r2.status_code}, body={body}")
        data = r2.json()
        try:
            return data["data"][0]["embedding"]
        except Exception as e:
            raise RuntimeError(f"Unexpected Fireworks response shape (retry): {e} - {data}")

    # If first response was not OK and not retriable, raise with body
    if not r.ok:
        body = None
        try:
            body = r.text
        except Exception:
            body = "<unreadable response body>"
        raise RuntimeError(f"Fireworks embedding error: status={r.status_code}, body={body}")

    data = r.json()
    try:
        return data["data"][0]["embedding"]
    except Exception as e:
        raise RuntimeError(f"Unexpected Fireworks response shape: {e} - {data}")


def embed_text(text: str) -> List[float]:
    if EMBEDDING_PROVIDER.lower() == "fireworks":
        return embed_text_fireworks(text)
    return embed_text_openai(text)


def search_similar_jobs(embedding: List[float], top_n: int = 10, similarity_threshold: float = 0.3) -> List[Tuple]:
    """
    Search for similar jobs using cosine similarity with pgvector.
    """
    if not embedding:
        return []

    # Convert embedding list to a pgvector literal string (e.g. [0.1,0.2,...])
    emb_literal = "[" + ",".join(map(str, embedding)) + "]"

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT j.id, j.title, j.description, j.requirements, j.company_id,
                   e.embedding, (1 - (e.embedding <=> %s::vector)) AS score
            FROM job_embeddings e
            JOIN jobs j ON j.id = e.job_id
            WHERE j.is_active = TRUE
            ORDER BY (e.embedding <=> %s::vector) NULLS LAST
            LIMIT %s
            """,
            [emb_literal, emb_literal, top_n],
        )
        rows = cursor.fetchall()

    # Filter by similarity_threshold in Python to avoid casting surprises
    filtered = [row for row in rows if (row and len(row) >= 7 and row[6] is not None and float(row[6]) >= similarity_threshold)]
    if filtered:
        return filtered

    # Fallback: return some active jobs with raw similarity scores (no threshold)
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT j.id, j.title, j.description, j.requirements, j.company_id,
                       e.embedding, (1 - (e.embedding <=> %s::vector)) AS score
                FROM job_embeddings e
                JOIN jobs j ON j.id = e.job_id
                WHERE j.is_active = TRUE
                ORDER BY (e.embedding <=> %s::vector) NULLS LAST
                LIMIT %s
                """,
                [emb_literal, emb_literal, max(top_n, 10)],
            )
            fallback_rows = cursor.fetchall()
        return fallback_rows or []
    except Exception:
        return []


def generate_answer(query: str, jobs: List[Tuple]) -> str:
    if not OPENAI_API_KEY or OpenAI is None:
        return "Summary disabled: chat model not configured. Returning results without summary."
    client = get_openai_client()
    context_lines = []
    for idx, (job_id, title, description, requirements, company_id, _, score) in enumerate(jobs, start=1):
        context_lines.append(f"[{idx}] {title} (score={score:.3f})\nDesc: {description}\nReq: {requirements}\n")
    context = "\n".join(context_lines)
    prompt = (
        "You are a helpful assistant for job recommendations. "
        "Given the user's query and the top matched jobs (with descriptions and requirements), "
        "summarize why these jobs are relevant and suggest next steps."
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"User query:\n{query}\n\nMatched jobs:\n{context}"},
    ]
    resp = client.chat.completions.create(model=CHAT_MODEL, messages=messages, temperature=0.2)
    return resp.choices[0].message.content.strip()
    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json",
    }
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    # Fireworks returns { data: [{ embedding: [...] }] }
    return data["data"][0]["embedding"]


def embed_text(text: str) -> List[float]:
    if EMBEDDING_PROVIDER.lower() == "fireworks":
        return embed_text_fireworks(text)
    return embed_text_openai(text)


def search_similar_jobs(embedding: List[float], top_n: int = 10, similarity_threshold: float = 0.3) -> List[Tuple]:
    """
    Search for similar jobs using cosine similarity with pgvector.
    
    Args:
        embedding: Query embedding vector
        top_n: Maximum number of results to return
        similarity_threshold: Minimum similarity score (0-1) to include a result
        
    Returns:
        List of tuples with job data and similarity scores
    """
    if not embedding:
        return []

    # Convert embedding list to a pgvector literal string (e.g. [0.1,0.2,...])
    emb_literal = "[" + ",".join(map(str, embedding)) + "]"

    # We'll select the single best (nearest) embedding row per job using
    # DISTINCT ON (j.id) ordered by distance. Then outer-query sorts by the
    # computed score and we limit to the requested top_n. This removes duplicate
    # job rows when multiple chunk embeddings exist for the same job.
    sql_limit = max(top_n, 100)
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT q.id, q.title, q.description, q.requirements, q.company_id, q.score
            FROM (
              SELECT DISTINCT ON (j.id)
                     j.id, j.title, j.description, j.requirements, j.company_id,
                     (1 - (e.embedding <=> %s::vector)) AS score
              FROM job_embeddings e
              JOIN jobs j ON j.id = e.job_id
              WHERE j.is_active = TRUE
              ORDER BY j.id, e.embedding <=> %s::vector
            ) q
            ORDER BY q.score DESC
            LIMIT %s
            """,
            [emb_literal, emb_literal, sql_limit],
        )
        rows = cursor.fetchall()

    # rows: (id, title, description, requirements, company_id, score)
    # Filter by similarity_threshold in Python and return matches above the threshold.
    filtered = [row for row in rows if (row and len(row) >= 6 and row[5] is not None and float(row[5]) >= similarity_threshold)]
    return filtered


def generate_answer(query: str, jobs: List[Tuple]) -> str:
    # If OpenAI chat is not configured, return a fallback summary instead of raising
    if not OPENAI_API_KEY or OpenAI is None:
        return "Summary disabled: chat model not configured. Returning results without summary."
    client = get_openai_client()
    context_lines = []
    for idx, (job_id, title, description, requirements, company_id, _, score) in enumerate(jobs, start=1):
        context_lines.append(f"[{idx}] {title} (score={score:.3f})\nDesc: {description}\nReq: {requirements}\n")
    context = "\n".join(context_lines)
    prompt = (
        "You are a helpful assistant for job recommendations. "
        "Given the user's query and the top matched jobs (with descriptions and requirements), "
        "summarize why these jobs are relevant and suggest next steps."
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"User query:\n{query}\n\nMatched jobs:\n{context}"},
    ]
    resp = client.chat.completions.create(model=CHAT_MODEL, messages=messages, temperature=0.2)
    return resp.choices[0].message.content.strip()