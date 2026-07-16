import streamlit as st
import requests
import re
import random
import os
from datetime import datetime

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
STUDENT_NAME = "Buddy"

st.set_page_config(page_title="AI Study Buddy", page_icon="📚")

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

* {
    font-family: 'Inter', -apple-system, sans-serif;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.stApp {
    background-color: #0d1117;
}

h1 {
    font-weight: 700 !important;
    font-size: 1.75rem !important;
    letter-spacing: -0.02em;
    padding-bottom: 0.5rem;
}

[data-testid="stChatMessage"] {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 12px;
    padding: 0.75rem 1rem;
    margin-bottom: 0.75rem;
}

[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background-color: #1c2128;
}

[data-testid="stChatInput"] {
    border-radius: 12px;
}

[data-testid="stChatInput"] textarea {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 12px !important;
    padding: 0.75rem 1rem !important;
}

[data-testid="stSidebar"] {
    background-color: #0d1117;
    border-right: 1px solid #21262d;
}

[data-testid="stSidebar"] h2 {
    font-size: 1.1rem !important;
    font-weight: 600 !important;
}

.stButton button {
    border-radius: 8px;
    border: 1px solid #30363d;
    background-color: #21262d;
    font-weight: 500;
    transition: all 0.15s ease;
}

.stButton button:hover {
    background-color: #30363d;
    border-color: #484f58;
}

.stButton button[kind="primary"] {
    background-color: #2f81f7;
    border-color: #2f81f7;
}

.stRadio > div {
    gap: 0.4rem;
}

.stRadio label {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 0.5rem 0.75rem;
    margin-bottom: 0.25rem;
    transition: all 0.15s ease;
}

.stRadio label:hover {
    border-color: #30363d;
}

.stTextInput input {
    background-color: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
    padding: 0.5rem 0.75rem !important;
}

[data-testid="stExpander"] {
    background-color: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
}

.stAlert {
    border-radius: 10px;
}

[data-testid="stFileUploaderDropzone"] {
    background-color: #161b22;
    border: 1.5px dashed #30363d;
    border-radius: 10px;
}

.stCaption, [data-testid="stCaptionContainer"] {
    color: #8b949e !important;
}

hr {
    border-color: #21262d !important;
}
</style>
""",
    unsafe_allow_html=True,
)

st.title("📚 AI-Powered Study Buddy")

QUIZ_KEYWORDS = ["quiz", "mcq", "test me", "ask me questions", "practice questions"]
SHORT_ANSWER_KEYWORDS = ["short answer", "short-answer", "written answer"]
FORMULA_KEYWORDS = ["formula", "equation"]
FLASHCARD_KEYWORDS = ["flashcard", "flash card", "flip card"]
PROGRESS_KEYWORDS = [
    "my progress",
    "how am i doing",
    "show my performance",
    "weak areas",
    "my score",
]
EXPLAIN_KEYWORDS = [
    "explain",
    "why",
    "what does",
    "clarify",
    "help me understand",
    "don't understand",
    "dont understand",
    "i don't get",
    "i dont get",
    "confused about",
]


def is_explain_request(text):
    return any(k in text.lower() for k in EXPLAIN_KEYWORDS)


def is_quiz_request(text):
    lowered = text.lower()
    if is_explain_request(text):
        return False
    if any(k in lowered for k in QUIZ_KEYWORDS):
        return True
    action_words = [
        "give me",
        "generate",
        "create",
        "make",
        "quiz",
        "test me",
        "ask me",
        "practice",
    ]
    target_words = ["question", "mcq"] + FORMULA_KEYWORDS + SHORT_ANSWER_KEYWORDS
    has_action = any(a in lowered for a in action_words)
    has_target = any(t in lowered for t in target_words)
    return has_action and has_target


def is_flashcard_request(text):
    return any(k in text.lower() for k in FLASHCARD_KEYWORDS)


def is_progress_request(text):
    return any(k in text.lower() for k in PROGRESS_KEYWORDS)


def detect_quiz_type(text):
    lowered = text.lower()
    if any(k in lowered for k in FORMULA_KEYWORDS):
        return "formula"
    if any(k in lowered for k in SHORT_ANSWER_KEYWORDS):
        return "short_answer"
    return "mcq"


def extract_num(text, default=5, max_val=10):
    match = re.search(r"(\d+)", text)
    if match:
        return max(1, min(int(match.group(1)), max_val))
    return default


def get_greeting(name="there"):
    hour = datetime.now().hour

    if 5 <= hour < 12:
        options = [
            f"Good morning, {name}",
            f"Early start, {name}",
            f"Rise and study, {name}",
        ]
    elif 12 <= hour < 17:
        options = [
            f"Good afternoon, {name}",
            f"Back at it, {name}",
            f"Study session, {name}",
        ]
    elif 17 <= hour < 22:
        options = [
            f"Good evening, {name}",
            f"Evening grind, {name}",
            f"Still going, {name}",
        ]
    else:
        options = [
            f"Night owl, {name}",
            f"Late night studying, {name}",
            f"Burning the midnight oil, {name}",
        ]

    return random.choice(options)


def build_history_payload(messages):
    history = []
    for m in messages:
        if m.get("type") == "text":
            history.append({"role": m["role"], "content": m.get("content", "")})
        elif m.get("type") == "quiz":
            quiz_summary = "Here was the quiz I gave the student:\n"
            for qi, q in enumerate(m["quiz_data"]):
                quiz_summary += (
                    f"{qi+1}. {q['question']} (Correct answer: {q['correct_answer']})\n"
                )
            history.append({"role": "assistant", "content": quiz_summary})
        elif m.get("type") == "flashcards":
            card_summary = "Here were the flashcards I gave the student:\n"
            for ci, card in enumerate(m["cards"]):
                card_summary += (
                    f"{ci+1}. Front: {card['front']} | Back: {card['back']}\n"
                )
            history.append({"role": "assistant", "content": card_summary})
    return history


if "checked_status" not in st.session_state:
    try:
        status = requests.get(f"{API_URL}/status", timeout=5).json()
        st.session_state.document_uploaded = status.get("document_loaded", False)
        st.session_state.current_filename = status.get("filename")
    except requests.exceptions.RequestException:
        st.session_state.document_uploaded = False
        st.session_state.current_filename = None
    st.session_state.checked_status = True

if "messages" not in st.session_state:
    st.session_state.messages = []

if "greeting" not in st.session_state:
    st.session_state.greeting = get_greeting(STUDENT_NAME)

with st.sidebar:
    st.header("Upload Study Material")

    if st.session_state.get("current_filename"):
        st.caption(f"📄 Currently loaded: **{st.session_state.current_filename}**")

    uploaded_file = st.file_uploader("Choose a file", type=["pdf", "docx", "txt"])

    if uploaded_file is not None and st.button("Process Document"):
        with st.spinner("Extracting, chunking, embedding, and summarizing..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            try:
                response = requests.post(f"{API_URL}/upload", files=files, timeout=120)
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "error":
                        st.error(result["message"])
                    else:
                        st.success(
                            f"Processed {result['pages_extracted']} pages into {result['chunks_created']} chunks."
                        )
                        st.session_state.document_uploaded = True
                        st.session_state.current_filename = result["filename"]
                        st.session_state.messages = []
                        st.session_state.greeting = get_greeting(STUDENT_NAME)
                else:
                    st.error("Upload failed. Check the backend server.")
            except requests.exceptions.RequestException as e:
                st.error(f"Could not reach the backend server. Is it running? ({e})")

    st.divider()
    st.caption(
        "💡 Try: *'quiz me'*, *'give me short answer questions'*, *'give me formula questions'*, *'flashcards'*, *'my progress'*, or *'explain question 3'*"
    )

if not st.session_state.document_uploaded:
    st.markdown(
        f"""
    <div style="text-align: center; padding: 4rem 2rem; opacity: 0.7;">
        <div style="font-size: 1.3rem; font-weight: 600; margin-bottom: 0.75rem;">{st.session_state.greeting}</div>
        <div style="font-size: 0.95rem; color: #8b949e;">Upload a PDF, DOCX, or TXT to get started.</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
elif not st.session_state.messages:
    st.markdown(
        f"""
    <div style="text-align: center; padding: 4rem 2rem; opacity: 0.7;">
        <div style="font-size: 1.3rem; font-weight: 600; margin-bottom: 0.75rem;">{st.session_state.greeting}</div>
        <div style="font-size: 0.95rem; color: #8b949e;">Ready to help with <b>{st.session_state.current_filename}</b> — ask a question, or try "quiz me"</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        msg_type = msg.get("type")

        if msg_type == "quiz":
            st.markdown("**Here's your quiz:**")
            for qi, q in enumerate(msg["quiz_data"]):
                st.markdown(f"**Q{qi+1}.** {q['question']}")
                qtype = q.get("type", "mcq")

                if qtype == "mcq":
                    labels = [f"{k}) {v}" for k, v in q["options"].items()]
                    key = f"quiz_{i}_{qi}"
                    selected = st.radio(
                        key, labels, key=key, label_visibility="collapsed", index=None
                    )
                    if selected:
                        msg["user_answers"][qi] = selected[0]
                else:
                    key = f"quiz_text_{i}_{qi}"
                    typed = st.text_input(
                        "Your answer", key=key, label_visibility="collapsed"
                    )
                    if typed:
                        msg["user_answers"][qi] = typed

            if st.button("Submit Quiz", key=f"submit_{i}"):
                msg["submitted"] = True
                results_payload = []
                for qi, q in enumerate(msg["quiz_data"]):
                    user_ans = msg["user_answers"].get(qi, "")
                    qtype = q.get("type", "mcq")
                    if qtype == "mcq":
                        correct = user_ans == q["correct_answer"]
                    else:
                        correct = (
                            user_ans.strip().lower()
                            in q["correct_answer"].strip().lower()
                            or q["correct_answer"].strip().lower()
                            in user_ans.strip().lower()
                        )
                    results_payload.append(
                        {"source_page": q.get("source_page"), "correct": correct}
                    )
                try:
                    requests.post(
                        f"{API_URL}/quiz-result",
                        json={"results": results_payload},
                        timeout=15,
                    )
                except requests.exceptions.RequestException:
                    pass

            if msg.get("submitted"):
                score = 0
                for qi, q in enumerate(msg["quiz_data"]):
                    user_ans = msg["user_answers"].get(qi, "")
                    qtype = q.get("type", "mcq")
                    if qtype == "mcq":
                        is_correct = user_ans == q["correct_answer"]
                        correct_display = q["correct_answer"]
                    else:
                        is_correct = (
                            user_ans.strip().lower()
                            in q["correct_answer"].strip().lower()
                            or q["correct_answer"].strip().lower()
                            in user_ans.strip().lower()
                        )
                        correct_display = q["correct_answer"]
                    if is_correct:
                        score += 1
                        st.success(f"Q{qi+1}: Correct!")
                        st.markdown(q["explanation"])
                    else:
                        st.error(
                            f"Q{qi+1}: You answered '{user_ans or 'nothing'}', correct was:"
                        )
                        st.markdown(correct_display)
                        st.markdown(q["explanation"])
                st.markdown(f"### Score: {score}/{len(msg['quiz_data'])}")

        elif msg_type == "flashcards":
            st.markdown("**Here are your flashcards:**")
            for ci, card in enumerate(msg["cards"]):
                with st.expander(f"**{card['front']}**"):
                    st.markdown(card["back"])

        elif msg_type == "progress":
            p = msg["progress_data"]
            if p["total_questions_answered"] == 0:
                st.write(
                    "No quiz attempts yet. Take a quiz first and I'll track your progress!"
                )
            else:
                st.markdown(f"**Your Progress**")
                st.write(f"Questions answered: {p['total_questions_answered']}")
                st.write(f"Correct: {p['correct']} | Wrong: {p['wrong']}")
                st.write(f"Accuracy: {p['accuracy_percent']}%")
                if p["weak_pages"]:
                    st.write(
                        f"Pages you're struggling with: {p['weak_pages']} — future quizzes will focus more here."
                    )
                else:
                    st.write("No specific weak areas detected yet — keep it up!")

        else:
            st.markdown(msg["content"])
            if msg.get("sources"):
                label = f"Sources: pages {msg['sources']}"
                if msg.get("used_web_search"):
                    label += " + web search"
                st.caption(label)

if question := st.chat_input(
    "Ask a question, say 'quiz me', 'flashcards', or 'explain question 3'..."
):
    st.session_state.messages.append(
        {"role": "user", "content": question, "type": "text"}
    )
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        if is_quiz_request(question):
            num_q = extract_num(question, default=5, max_val=10)
            qtype = detect_quiz_type(question)
            with st.spinner(
                f"Generating {num_q} {qtype.replace('_', ' ')} questions..."
            ):
                try:
                    response = requests.post(
                        f"{API_URL}/quiz",
                        json={
                            "topic": "",
                            "num_questions": num_q,
                            "question_type": qtype,
                        },
                        timeout=90,
                    )
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("error"):
                            st.error(result["error"])
                            st.session_state.messages.append(
                                {
                                    "role": "assistant",
                                    "type": "text",
                                    "content": result["error"],
                                }
                            )
                        else:
                            st.session_state.messages.append(
                                {
                                    "role": "assistant",
                                    "type": "quiz",
                                    "quiz_data": result["questions"],
                                    "user_answers": {},
                                    "submitted": False,
                                }
                            )
                            st.rerun()
                    else:
                        st.error("Something went wrong generating the quiz.")
                except requests.exceptions.RequestException as e:
                    st.error(
                        f"Could not reach the backend server. Is it running? ({e})"
                    )

        elif is_flashcard_request(question):
            num_c = extract_num(question, default=8, max_val=15)
            with st.spinner(f"Generating {num_c} flashcards..."):
                try:
                    response = requests.post(
                        f"{API_URL}/flashcards",
                        json={"topic": "", "num_cards": num_c},
                        timeout=90,
                    )
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("error"):
                            st.error(result["error"])
                            st.session_state.messages.append(
                                {
                                    "role": "assistant",
                                    "type": "text",
                                    "content": result["error"],
                                }
                            )
                        else:
                            st.session_state.messages.append(
                                {
                                    "role": "assistant",
                                    "type": "flashcards",
                                    "cards": result["cards"],
                                }
                            )
                            st.rerun()
                    else:
                        st.error("Something went wrong generating flashcards.")
                except requests.exceptions.RequestException as e:
                    st.error(
                        f"Could not reach the backend server. Is it running? ({e})"
                    )

        elif is_progress_request(question):
            try:
                response = requests.get(f"{API_URL}/progress", timeout=15)
                if response.status_code == 200:
                    result = response.json()
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "type": "progress",
                            "progress_data": result,
                        }
                    )
                    st.rerun()
                else:
                    st.error("Could not fetch progress.")
            except requests.exceptions.RequestException as e:
                st.error(f"Could not reach the backend server. Is it running? ({e})")

        else:
            with st.spinner("Thinking..."):
                history_payload = build_history_payload(st.session_state.messages[:-1])
                try:
                    response = requests.post(
                        f"{API_URL}/ask",
                        json={"question": question, "history": history_payload},
                        timeout=60,
                    )
                    if response.status_code == 200:
                        result = response.json()
                        st.markdown(result["answer"])
                        label = f"Sources: pages {result['sources']}"
                        if result.get("used_web_search"):
                            label += " + web search"
                        st.caption(label)
                        st.session_state.messages.append(
                            {
                                "role": "assistant",
                                "type": "text",
                                "content": result["answer"],
                                "sources": result["sources"],
                                "used_web_search": result.get("used_web_search", False),
                            }
                        )
                    else:
                        st.error("Something went wrong getting the answer.")
                except requests.exceptions.RequestException as e:
                    st.error(
                        f"Could not reach the backend server. Is it running? ({e})"
                    )
