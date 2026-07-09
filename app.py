import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI Study Buddy", page_icon="📚")
st.title("📚 AI-Powered Study Buddy")

# ---- Sync frontend state with backend reality on load ----
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

# ---- Sidebar: PDF upload ----
with st.sidebar:
    st.header("Upload Study Material")

    if st.session_state.get("current_filename"):
        st.caption(f"📄 Currently loaded: **{st.session_state.current_filename}**")

    uploaded_file = st.file_uploader("Choose a PDF", type=["pdf"])

    if uploaded_file is not None and st.button("Process Document"):
        with st.spinner("Extracting, chunking, embedding, and summarizing..."):
            files = {
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    "application/pdf",
                )
            }
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
                        st.session_state.messages = []  # fresh chat for a new document
                else:
                    st.error("Upload failed. Check the backend server.")
            except requests.exceptions.RequestException as e:
                st.error(f"Could not reach the backend server. Is it running? ({e})")

# ---- Main chat area ----
if not st.session_state.document_uploaded:
    st.info("Upload a PDF from the sidebar to get started.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg.get("sources"):
            label = f"Sources: pages {msg['sources']}"
            if msg.get("used_web_search"):
                label += " + web search"
            st.caption(label)

if question := st.chat_input("Ask a question about your document..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            history_payload = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]
            ]
            try:
                response = requests.post(
                    f"{API_URL}/ask",
                    json={"question": question, "history": history_payload},
                    timeout=60,
                )
                if response.status_code == 200:
                    result = response.json()
                    st.write(result["answer"])
                    label = f"Sources: pages {result['sources']}"
                    if result.get("used_web_search"):
                        label += " + web search"
                    st.caption(label)
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": result["answer"],
                            "sources": result["sources"],
                            "used_web_search": result.get("used_web_search", False),
                        }
                    )
                else:
                    st.error("Something went wrong getting the answer.")
            except requests.exceptions.RequestException as e:
                st.error(f"Could not reach the backend server. Is it running? ({e})")
