import os
import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ClientError
from qa_chain import load_summary
from retriever import retrieve_chunks

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

QUIZ_PROMPT_TEMPLATE = """You are a study assistant creating a quiz to help a student test their understanding of their uploaded material.

Generate exactly {num_questions} multiple-choice questions based on the content below.

Rules:
- Each question must be answerable directly from the content provided.
- Each question has exactly 4 options (A, B, C, D).
- Only one option is correct.
- Vary difficulty: include some easy recall questions and some that require understanding, not just memorization.
- Do NOT include any text outside the JSON. No preamble, no explanation, no markdown formatting.

Respond with ONLY a valid JSON array in this exact format:
[
  {{
    "question": "question text here",
    "options": {{
      "A": "option text",
      "B": "option text",
      "C": "option text",
      "D": "option text"
    }},
    "correct_answer": "A",
    "explanation": "one sentence explaining why this is correct"
  }}
]

Document Overview:
{summary}

Content to base questions on:
{context}

JSON array:"""


def extract_json_array(text: str) -> str:
    """
    Gemini sometimes wraps JSON in markdown code fences despite instructions.
    This strips that off defensively before parsing.
    """
    text = text.strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return match.group(0)
    return text


def generate_quiz(topic: str = "", num_questions: int = 5, k: int = 8) -> dict:
    """
    Generates a multiple-choice quiz from the uploaded document.

    Args:
        topic: optional topic/keyword to focus the quiz on. Empty = whole document.
        num_questions: how many questions to generate
        k: how many chunks to pull as source material (more than qa_chain's
           default since quiz generation needs broader coverage, not one answer)

    Returns:
        dict with 'questions' (list) and 'error' (str or None)
    """
    query = (
        topic
        if topic.strip()
        else "main concepts and important details in this document"
    )
    chunks = retrieve_chunks(query, k=k)

    context = "\n\n".join(
        f"[Page {doc.metadata['page']}]: {doc.page_content}" for doc in chunks
    )
    summary = load_summary()

    prompt = QUIZ_PROMPT_TEMPLATE.format(
        num_questions=num_questions, summary=summary, context=context
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
    except ClientError as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            return {
                "questions": [],
                "error": "Daily API limit reached. Please try again later.",
            }
        return {"questions": [], "error": f"API error: {e}"}

    raw_text = extract_json_array(response.text)

    try:
        questions = json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "questions": [],
            "error": "Could not parse quiz output. Please try again.",
        }

    return {"questions": questions, "error": None}


if __name__ == "__main__":
    result = generate_quiz(num_questions=3)

    if result["error"]:
        print(f"Error: {result['error']}")
    else:
        for i, q in enumerate(result["questions"], 1):
            print(f"\nQ{i}: {q['question']}")
            for letter, text in q["options"].items():
                print(f"  {letter}) {text}")
            print(f"Correct: {q['correct_answer']}")
            print(f"Why: {q['explanation']}")
