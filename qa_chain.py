import os
from dotenv import load_dotenv
from google import genai
from tavily import TavilyClient
from retriever import retrieve_chunks

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
tavily_key = os.getenv("TAVILY_API_KEY")

client = genai.Client(api_key=api_key)
tavily_client = TavilyClient(api_key=tavily_key) if tavily_key else None

SUMMARY_FILE = "document_summary.txt"
WEB_SEARCH_MARKER = "[WEB_SEARCH_NEEDED]"

PROMPT_TEMPLATE = """You are a study assistant helping a student understand and think critically about their uploaded material.

You have two jobs, depending on what's asked:
1. If the student asks for a FACT (a date, name, definition, specific detail) that IS in the context below — answer using the context.
2. If the student asks for ANALYSIS, EVALUATION, EXPLANATION, or OPINION about the document's content — actually reason about it. Use your own understanding and judgment, applied to the document's content. Don't just refuse because exact words aren't written verbatim — synthesize, interpret, explain like a knowledgeable tutor.

If the question asks about something the document doesn't cover — especially outside/background knowledge about a real person, place, event, or concept mentioned in the document (not something the document itself explains) — respond with EXACTLY this and nothing else:
{marker} <a short, specific web search query that would find the answer>

Otherwise, answer normally and directly.

Recent conversation (for context on follow-up questions like "this person" or "that chapter"):
{history}

Document Overview:
{summary}

Relevant excerpts:
{context}

Question: {question}

Answer:"""

FINAL_PROMPT_TEMPLATE = """You previously determined this question needs outside information beyond the uploaded document. Here are web search results:

{web_results}

Original document context (for reference):
{context}

Question: {question}

Write a clear, helpful answer combining both sources. Clearly distinguish what came from the student's uploaded document versus general/web knowledge, e.g. "According to your document..." vs "More generally,..."."""


def generate_document_summary(full_text: str) -> str:
    prompt = f"""Summarize the following document in 200-300 words.
Include: the title (if mentioned), author/editor (if mentioned),
main topics covered, and overall structure. Be factual and concise.

Document:
{full_text[:50000]}

Summary:"""
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text


def load_summary() -> str:
    if os.path.exists(SUMMARY_FILE):
        with open(SUMMARY_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "(No summary available yet.)"


def format_history(history: list) -> str:
    """Turns a list of {role, content} dicts into readable text for the prompt."""
    if not history:
        return "(No previous conversation.)"
    lines = []
    for msg in history[-6:]:  # last 3 exchanges (6 messages) is plenty of context
        role = "Student" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def answer_question(question: str, history: list = None, k: int = 4) -> dict:
    """
    Full pipeline: retrieve chunks, check conversation history, answer from
    document context, and fall back to web search if the model signals it needs
    outside information.
    """
    history = history or []

    # use last user question too, to help retrieval resolve follow-ups
    last_user_q = next(
        (m["content"] for m in reversed(history) if m["role"] == "user"), ""
    )
    retrieval_query = f"{last_user_q} {question}".strip() if last_user_q else question

    chunks = retrieve_chunks(retrieval_query, k=k)
    context = "\n\n".join(
        f"[Page {doc.metadata['page']}]: {doc.page_content}" for doc in chunks
    )
    summary = load_summary()
    history_text = format_history(history)

    prompt = PROMPT_TEMPLATE.format(
        marker=WEB_SEARCH_MARKER,
        history=history_text,
        summary=summary,
        context=context,
        question=question,
    )

    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    answer_text = response.text.strip()
    sources = sorted(set(doc.metadata["page"] for doc in chunks))
    used_web = False

    # check if the model asked for a web search
    if answer_text.startswith(WEB_SEARCH_MARKER) and tavily_client:
        search_query = answer_text.replace(WEB_SEARCH_MARKER, "").strip()
        try:
            search_results = tavily_client.search(search_query, max_results=3)
            web_summary = "\n\n".join(
                f"- {r['title']}: {r['content'][:300]}"
                for r in search_results.get("results", [])
            )
            final_prompt = FINAL_PROMPT_TEMPLATE.format(
                web_results=web_summary, context=context, question=question
            )
            final_response = client.models.generate_content(
                model="gemini-2.5-flash", contents=final_prompt
            )
            answer_text = final_response.text
            used_web = True
        except Exception as e:
            answer_text = f"I wanted to search the web for this but hit an error: {e}"

    return {"answer": answer_text, "sources": sources, "used_web_search": used_web}


if __name__ == "__main__":
    result = answer_question("What is this book about?")
    print(
        f"Answer: {result['answer']}\nSources: {result['sources']}\nUsed web: {result['used_web_search']}"
    )
