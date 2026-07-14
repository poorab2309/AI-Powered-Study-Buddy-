import os
import json
import re
from dotenv import load_dotenv
from google import genai
from google.genai.errors import ClientError
from qa_chain import load_summary
from retriever import retrieve_chunks, get_chunks_by_page

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=api_key)

WEAK_AREAS_FILE = "weak_areas.json"

MCQ_PROMPT_TEMPLATE = """You are a study assistant creating a quiz to help a student test their understanding of their uploaded material.

Generate exactly {num_questions} multiple-choice questions based on the content below.
{weak_area_instruction}

Rules:
- Each question must be answerable directly from the content provided.
- Each question has exactly 4 options (A, B, C, D). Only one option is correct.
- Vary difficulty: some easy recall, some requiring understanding.
- Include a "source_page" field with the page number the question is based on.
- Format any mathematical expressions using LaTeX notation ($...$ for inline, $$...$$ for block equations).
- Do NOT include any text outside the JSON.

Respond with ONLY a valid JSON array:
[
  {{
    "type": "mcq",
    "question": "question text",
    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "correct_answer": "A",
    "explanation": "one sentence why",
    "source_page": 5
  }}
]

Document Overview:
{summary}

Content:
{context}

JSON array:"""

SHORT_ANSWER_PROMPT_TEMPLATE = """You are a study assistant creating short-answer questions to test a student's understanding of their uploaded material.

Generate exactly {num_questions} short-answer questions based on the content below.
{weak_area_instruction}

Rules:
- Each question should require a brief written answer (a phrase or 1-2 sentences), not multiple choice.
- Provide a clear model/correct answer for each.
- Include a "source_page" field with the page number the question is based on.
- Do NOT include any text outside the JSON.

Respond with ONLY a valid JSON array:
[
  {{
    "type": "short_answer",
    "question": "question text",
    "correct_answer": "the expected answer",
    "explanation": "brief context or elaboration",
    "source_page": 5
  }}
]

Document Overview:
{summary}

Content:
{context}

JSON array:"""

FORMULA_PROMPT_TEMPLATE = """You are a study assistant creating formula-recall questions to test a student's understanding of technical/formula-based material in their uploaded document.

Generate exactly {num_questions} formula-recall questions based on the content below. Only generate questions if the content actually contains formulas, equations, or quantitative relationships. If the content has no such material, generate conceptual short-answer questions about key technical relationships instead.
{weak_area_instruction}

Rules:
- Each question should ask the student to recall or state a formula/equation.
- Provide the exact correct formula as the answer.
- Include a "source_page" field with the page number the question is based on.
- Format all formulas using LaTeX notation ($...$ for inline, $$...$$ for block equations), e.g. "$F = ma$" or "$$x = \\frac{{-b \\pm \\sqrt{{b^2 - 4ac}}}}{{2a}}$$".
- Do NOT include any text outside the JSON.

Respond with ONLY a valid JSON array:
[
  {{
    "type": "formula",
    "question": "question text, e.g. 'What is the formula for X?'",
    "correct_answer": "the formula in LaTeX, e.g. $F = ma$",
    "explanation": "brief context",
    "source_page": 5
  }}
]

Document Overview:
{summary}

Content:
{context}

JSON array:"""

FLASHCARD_PROMPT_TEMPLATE = """You are a study assistant creating flashcards to help a student memorize and understand their uploaded material.

Generate exactly {num_cards} flashcards based on the content below.

Rules:
- Each flashcard has a "front" and a "back".
- Keep fronts short and focused. Keep backs concise but complete.
- Format any mathematical expressions using LaTeX notation ($...$ for inline math).
- Do NOT include any text outside the JSON.

Respond with ONLY a valid JSON array:
[
  {{"front": "term or question", "back": "answer or explanation"}}
]

Document Overview:
{summary}

Content:
{context}

JSON array:"""


def extract_json_array(text: str) -> str:
    text = text.strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    return match.group(0) if match else text


def load_weak_areas() -> dict:
    if os.path.exists(WEAK_AREAS_FILE):
        with open(WEAK_AREAS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_weak_areas(data: dict):
    with open(WEAK_AREAS_FILE, "w") as f:
        json.dump(data, f)


def record_quiz_results(results: list):
    weak_areas = load_weak_areas()
    for r in results:
        page = str(r.get("source_page"))
        if page == "None":
            continue
        if page not in weak_areas:
            weak_areas[page] = {"correct": 0, "wrong": 0}
        if r.get("correct"):
            weak_areas[page]["correct"] += 1
        else:
            weak_areas[page]["wrong"] += 1
    save_weak_areas(weak_areas)


def get_top_weak_pages(limit: int = 3) -> list:
    weak_areas = load_weak_areas()
    scored = []
    for page, stats in weak_areas.items():
        wrong = stats.get("wrong", 0)
        correct = stats.get("correct", 0)
        if wrong > correct:
            scored.append((int(page), wrong - correct))
    scored.sort(key=lambda x: -x[1])
    return [p for p, _ in scored[:limit]]


def get_progress_summary() -> dict:
    weak_areas = load_weak_areas()
    total_correct = sum(v.get("correct", 0) for v in weak_areas.values())
    total_wrong = sum(v.get("wrong", 0) for v in weak_areas.values())
    total = total_correct + total_wrong
    accuracy = round((total_correct / total) * 100, 1) if total > 0 else None
    weak_pages = get_top_weak_pages(limit=5)
    return {
        "total_questions_answered": total,
        "correct": total_correct,
        "wrong": total_wrong,
        "accuracy_percent": accuracy,
        "weak_pages": weak_pages,
    }


def reset_weak_areas():
    if os.path.exists(WEAK_AREAS_FILE):
        os.remove(WEAK_AREAS_FILE)


def _build_context(topic: str, k: int, include_weak_areas: bool):
    query = (
        topic
        if topic.strip()
        else "main concepts and important details in this document"
    )
    chunks = retrieve_chunks(query, k=k)
    context_parts = [
        f"[Page {doc.metadata['page']}]: {doc.page_content}" for doc in chunks
    ]

    weak_area_instruction = ""
    if include_weak_areas and not topic.strip():
        weak_pages = get_top_weak_pages()
        if weak_pages:
            extra_content = []
            for page in weak_pages:
                for text in get_chunks_by_page(page):
                    extra_content.append(f"[Page {page} - weak area]: {text}")
            if extra_content:
                context_parts.extend(extra_content)
                weak_area_instruction = f"\nThe student has previously struggled with page(s) {', '.join(map(str, weak_pages))}. Prioritize questions from that content."

    return "\n\n".join(context_parts), weak_area_instruction


def _generate_from_template(
    template: str, num_questions: int, topic: str, k: int
) -> dict:
    context, weak_area_instruction = _build_context(topic, k, include_weak_areas=True)
    summary = load_summary()

    prompt = template.format(
        num_questions=num_questions,
        weak_area_instruction=weak_area_instruction,
        summary=summary,
        context=context,
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


def generate_quiz(
    topic: str = "", num_questions: int = 5, k: int = 8, question_type: str = "mcq"
) -> dict:
    template = {
        "mcq": MCQ_PROMPT_TEMPLATE,
        "short_answer": SHORT_ANSWER_PROMPT_TEMPLATE,
        "formula": FORMULA_PROMPT_TEMPLATE,
    }.get(question_type, MCQ_PROMPT_TEMPLATE)

    return _generate_from_template(template, num_questions, topic, k)


def generate_flashcards(topic: str = "", num_cards: int = 8, k: int = 8) -> dict:
    context, _ = _build_context(topic, k, include_weak_areas=False)
    summary = load_summary()

    prompt = FLASHCARD_PROMPT_TEMPLATE.format(
        num_cards=num_cards, summary=summary, context=context
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
    except ClientError as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            return {
                "cards": [],
                "error": "Daily API limit reached. Please try again later.",
            }
        return {"cards": [], "error": f"API error: {e}"}

    raw_text = extract_json_array(response.text)
    try:
        cards = json.loads(raw_text)
    except json.JSONDecodeError:
        return {
            "cards": [],
            "error": "Could not parse flashcard output. Please try again.",
        }

    return {"cards": cards, "error": None}


if __name__ == "__main__":
    result = generate_quiz(num_questions=3, question_type="mcq")
    if result["error"]:
        print(f"Error: {result['error']}")
    else:
        for i, q in enumerate(result["questions"], 1):
            print(f"\nQ{i}: {q['question']} (page {q.get('source_page')})")
