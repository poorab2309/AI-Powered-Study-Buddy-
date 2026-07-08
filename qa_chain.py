import os
from dotenv import load_dotenv
from google import genai
from retriever import retrieve_chunks

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

PROMPT_TEMPLATE = """You are a study assistant helping a student understand their uploaded material.
Answer the question using ONLY the context below. Do not use outside knowledge.
If the answer is not in the context, say "I don't have enough information in the uploaded material to answer that."

Context:
{context}

Question: {question}

Answer:"""


def answer_question(question: str, k: int = 4) -> dict:
    """
    Full RAG pipeline: retrieve relevant chunks, build a grounded prompt,
    get Gemini's answer, and return it along with source pages used.

    Returns:
        dict with 'answer' (str) and 'sources' (list of page numbers)
    """
    chunks = retrieve_chunks(question, k=k)

    # combine chunk texts into one context block, with page labels
    context = "\n\n".join(
        f"[Page {doc.metadata['page']}]: {doc.page_content}" for doc in chunks
    )

    prompt = PROMPT_TEMPLATE.format(context=context, question=question)

    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)

    sources = sorted(set(doc.metadata["page"] for doc in chunks))

    return {"answer": response.text, "sources": sources}


if __name__ == "__main__":
    test_question = "What is this book about?"
    result = answer_question(test_question)

    print(f"Question: {test_question}\n")
    print(f"Answer: {result['answer']}\n")
    print(f"Sources: pages {result['sources']}")
