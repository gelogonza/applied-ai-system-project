"""
Streamlit UI for Mood Music.

Run from the project root:
    streamlit run src/app.py
"""

import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

import anthropic

from rag import retrieve_songs, run_rag, score_response, validate_output
from recommender import load_songs

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Mood Music",
    page_icon="🎵",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Cached resources (loaded once per session)
# ---------------------------------------------------------------------------
@st.cache_data
def get_songs():
    data_path = Path(__file__).parent.parent / "data" / "songs.csv"
    return load_songs(str(data_path))


@st.cache_resource
def get_client(api_key: str):
    return anthropic.Anthropic(api_key=api_key)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuration")

    env_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if env_key:
        st.success("API key loaded from environment.")
        api_key = env_key
    else:
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            placeholder="sk-ant-...",
            help="Or add ANTHROPIC_API_KEY to a .env file in the project root.",
        )

    st.divider()

    songs = get_songs()
    st.metric("Songs in catalog", len(songs))

    genres = sorted({s["genre"] for s in songs})
    moods = sorted({s["mood"] for s in songs})
    st.caption(f"**Genres:** {', '.join(genres)}")
    st.caption(f"**Moods:** {', '.join(moods)}")

    st.divider()
    st.caption("Model: Claude Sonnet 4.6")
    st.caption("Retrieval: keyword scoring")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
st.title("🎵 Mood Music")
st.caption(
    "Describe what you're in the mood for in plain English. "
    "The system retrieves matching songs from the catalog, then Claude "
    "recommends the best fits using their actual audio attributes."
)

st.divider()

# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------
query = st.text_input(
    "What kind of music are you in the mood for?",
    placeholder="e.g. something chill to study to",
    label_visibility="visible",
)

run_btn = st.button("Get Recommendations", type="primary", disabled=not api_key)

if not api_key:
    st.warning("Add your Anthropic API key in the sidebar to get started.")

# ---------------------------------------------------------------------------
# Run pipeline
# ---------------------------------------------------------------------------
if run_btn and query and api_key:
    client = get_client(api_key)

    with st.spinner("Retrieving songs and generating recommendation..."):
        retrieved = retrieve_songs(query, songs, k=5)
        response = run_rag(query, songs, client)
        confidence = score_response(response, retrieved)
        guardrail_ok, _ = validate_output(response, retrieved)

    # --- Retrieved songs ---
    with st.expander(f"📚 Retrieved {len(retrieved)} songs from catalog", expanded=False):
        for i, song in enumerate(retrieved, 1):
            cols = st.columns([3, 1, 1, 1])
            cols[0].markdown(f"**{i}. {song['title']}** — *{song['artist']}*")
            cols[1].caption(f"{song['genre']}")
            cols[2].caption(f"{song['mood']}")
            cols[3].caption(f"⚡ {song['energy']}")

    # --- Recommendation ---
    st.subheader("🎧 Recommendation")
    st.markdown(response)

    # --- Metrics ---
    st.divider()
    col1, col2, col3 = st.columns(3)

    col1.metric("Confidence Score", f"{confidence:.2f}")

    if confidence >= 0.5:
        col2.metric("Response Quality", "High", delta="attribute-rich")
    elif confidence >= 0.3:
        col2.metric("Response Quality", "Medium", delta="some attributes cited")
    else:
        col2.metric("Response Quality", "Low", delta="generic response", delta_color="inverse")

    col3.metric("Guardrail", "✓ Pass" if guardrail_ok else "✗ Fail")

    st.progress(confidence, text=f"Confidence: {confidence:.0%}")

    # --- Save to session history ---
    if "history" not in st.session_state:
        st.session_state.history = []
    st.session_state.history.insert(0, {
        "query": query,
        "retrieved": retrieved,
        "response": response,
        "confidence": confidence,
        "guardrail": guardrail_ok,
    })

# ---------------------------------------------------------------------------
# Query history
# ---------------------------------------------------------------------------
if st.session_state.get("history"):
    history = st.session_state.history
    # Skip the first entry if we just ran a query (already shown above)
    past = history[1:] if (run_btn and query and api_key) else history

    if past:
        st.divider()
        st.subheader("🕘 Previous Queries")
        for item in past:
            label = f'"{item["query"]}" — confidence {item["confidence"]:.2f}'
            with st.expander(label, expanded=False):
                st.markdown(item["response"])
                sub_cols = st.columns(3)
                sub_cols[0].caption(f"Confidence: {item['confidence']:.2f}")
                sub_cols[1].caption(f"Guardrail: {'Pass' if item['guardrail'] else 'Fail'}")
                sub_cols[2].caption(f"Songs retrieved: {len(item['retrieved'])}")
