import json
import streamlit as st
from service.graph_rag import GraphRAG
from config import settings
import sentence_transformers as st_models

original_sentence_transformer = st_models.SentenceTransformer

def sentence_transformer_cpu(model_name, *args, **kwargs):
    """Force model to load on CPU."""
    kwargs["device"] = "cpu"
    return original_sentence_transformer(model_name, *args, **kwargs)

st_models.SentenceTransformer = sentence_transformer_cpu

def rerun():
    """Force Streamlit to rerun the app."""
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()

def get_rag() -> GraphRAG:
    """Get or create the GraphRAG (HF) instance in session state."""
    if "rag" not in st.session_state:
        st.session_state.rag = GraphRAG(
            hf_token=settings.HF_TOKEN,
            top_k=3,
            neighbors_k=3,
        )
    return st.session_state.rag

def ask_hf(user_query: str):
    """Ask using the HuggingFace-based GraphRAG pipeline. Returns (answer, prompt_json)."""
    rag = get_rag()
    captured = {"prompt": None}
    original_generate = rag.generate_messages

    def capture_messages(*args, **kwargs):
        captured["prompt"] = original_generate(*args, **kwargs)
        return captured["prompt"]

    rag.generate_messages = capture_messages
    answer = rag.chat_interface(user_query)
    rag.generate_messages = original_generate

    prompt_json = (
        json.dumps(captured["prompt"], indent=2, ensure_ascii=False)
        if captured["prompt"]
        else "⟨prompt not captured⟩"
    )
    return answer, prompt_json

def ask_crewai_backend(user_query: str):
    """Ask using the CrewAI/Groq pipeline. Returns (answer, prompt_json)."""
    # Imported lazily so the Neo4j/embedding connections inside crewai_rag_main
    # only get created the first time this backend is actually used.
    from service.crewai_rag_main import ask_crewai
    answer = ask_crewai(user_query)
    return answer, "⟨prompt capture not implemented for CrewAI backend⟩"

def render():
    """Render the chat UI and handle user interaction."""
    st.title("Ask Me Anything About Your Docs!")

    backend = st.radio(
        "Choose answer engine",
        options=["HuggingFace (GraphRAG)", "CrewAI + Groq"],
        horizontal=True,
        key="backend_choice",
    )

    if "chat_turns" not in st.session_state:
        st.session_state.chat_turns = []

    for question, answer, prompt, used_backend in st.session_state.chat_turns:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            st.caption(f"Answered using: {used_backend}")
            st.write(answer)
            with st.expander("📝 Prompt + context", expanded=False):
                st.code(prompt, language="json")

    user_query = st.chat_input("Ask your question…")

    if user_query:
        with st.spinner(f"Thinking using {backend}…"):
            if backend == "HuggingFace (GraphRAG)":
                assistant_answer, prompt_json = ask_hf(user_query)
            else:
                assistant_answer, prompt_json = ask_crewai_backend(user_query)

        st.session_state.chat_turns.append((user_query, assistant_answer, prompt_json, backend))
        rerun()

    if st.session_state.get("chat_turns") and st.button("🗑️ Clear chat"):
        st.session_state.chat_turns = []
        if "rag" in st.session_state:
            st.session_state.rag.clear_history()
        rerun()