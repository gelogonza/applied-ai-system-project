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

from rag import retrieve_songs, run_rag, score_response, validate_output, ATTRIBUTE_KEYWORDS
from recommender import load_songs

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Mood Music",
    page_icon="🎵",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Theme state
# ---------------------------------------------------------------------------
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True


def inject_theme(dark: bool) -> None:
    if dark:
        css = """
        /* === GLOBAL RESET === */
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(150deg, #060c1a 0%, #0d1b3e 55%, #060c1a 100%) !important;
            min-height: 100vh;
        }
        [data-testid="stHeader"] {
            background: rgba(6, 12, 26, 0.92) !important;
            backdrop-filter: blur(8px);
            border-bottom: 1px solid rgba(59, 130, 246, 0.15) !important;
        }
        .main .block-container {
            background: transparent !important;
        }

        /* === SIDEBAR === */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d1b3e 0%, #060c1a 100%) !important;
            border-right: 1px solid rgba(59, 130, 246, 0.18) !important;
        }
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] li {
            color: #cbd5e1 !important;
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #93c5fd !important;
        }
        [data-testid="stSidebar"] [data-testid="stMetricValue"] {
            color: #93c5fd !important;
        }
        [data-testid="stSidebar"] [data-testid="stMetricLabel"] {
            color: #64748b !important;
        }

        /* === TYPOGRAPHY === */
        h1 { color: #93c5fd !important; font-weight: 700 !important; letter-spacing: -0.5px; }
        h2 { color: #60a5fa !important; font-weight: 600 !important; }
        h3 { color: #60a5fa !important; font-weight: 600 !important; }
        p, li, span { color: #cbd5e1 !important; }
        label { color: #94a3b8 !important; }

        /* === BUTTONS === */
        button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 20px rgba(37, 99, 235, 0.4) !important;
            transition: all 0.25s ease !important;
        }
        button[data-testid="baseButton-primary"]:hover {
            background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%) !important;
            box-shadow: 0 6px 28px rgba(59, 130, 246, 0.55) !important;
            transform: translateY(-2px) !important;
        }
        button[data-testid="baseButton-secondary"] {
            background: linear-gradient(135deg, rgba(30,58,138,0.35) 0%, rgba(37,99,235,0.18) 100%) !important;
            color: #93c5fd !important;
            border: 1px solid rgba(59, 130, 246, 0.38) !important;
            border-radius: 10px !important;
            transition: all 0.2s ease !important;
        }
        button[data-testid="baseButton-secondary"]:hover {
            background: linear-gradient(135deg, rgba(37,99,235,0.4) 0%, rgba(59,130,246,0.25) 100%) !important;
            border-color: rgba(96, 165, 250, 0.6) !important;
        }

        /* === TEXT INPUT === */
        [data-testid="stTextInput"] input {
            background: rgba(13, 27, 62, 0.85) !important;
            color: #e2e8f0 !important;
            border: 1px solid rgba(59, 130, 246, 0.35) !important;
            border-radius: 10px !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }
        [data-testid="stTextInput"] input:focus {
            border-color: #3b82f6 !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.18) !important;
        }
        [data-testid="stTextInput"] input::placeholder { color: #475569 !important; }

        /* === EXPANDER === */
        [data-testid="stExpander"] {
            background: rgba(13, 27, 62, 0.55) !important;
            border: 1px solid rgba(59, 130, 246, 0.2) !important;
            border-radius: 12px !important;
            backdrop-filter: blur(6px);
        }
        [data-testid="stExpander"] summary {
            color: #93c5fd !important;
        }

        /* === METRICS === */
        [data-testid="stMetricValue"] {
            color: #93c5fd !important;
            font-weight: 700 !important;
        }
        [data-testid="stMetricLabel"] { color: #94a3b8 !important; }
        [data-testid="stMetricDelta"] svg { fill: #34d399 !important; }

        /* === PROGRESS BAR === */
        [data-testid="stProgress"] > div {
            background: rgba(30, 58, 138, 0.3) !important;
            border-radius: 99px !important;
        }
        [data-testid="stProgress"] > div > div {
            background: linear-gradient(90deg, #1e3a8a, #3b82f6) !important;
            border-radius: 99px !important;
        }

        /* === DIVIDER === */
        [data-testid="stDivider"] hr {
            border-color: rgba(59, 130, 246, 0.2) !important;
        }

        /* === ALERTS === */
        [data-testid="stAlert"] {
            background: rgba(13, 27, 62, 0.7) !important;
            border-radius: 10px !important;
            backdrop-filter: blur(4px);
        }
        [data-testid="stAlert"][data-baseweb="notification"] {
            border-left-color: #3b82f6 !important;
        }

        /* === CAPTIONS === */
        [data-testid="stCaptionContainer"] p { color: #64748b !important; }

        /* === TOGGLE === */
        [data-testid="stToggle"] input[type="checkbox"] { accent-color: #3b82f6 !important; }

        /* === SUCCESS / WARNING === */
        div[data-testid="stAlert"][kind="success"] {
            background: rgba(16, 185, 129, 0.08) !important;
            border-left: 4px solid #10b981 !important;
        }
        div[data-testid="stAlert"][kind="warning"] {
            background: rgba(245, 158, 11, 0.08) !important;
            border-left: 4px solid #f59e0b !important;
        }

        /* === MISC === */
        [data-testid="column"] { padding: 0.4rem !important; }
        """
    else:
        css = """
        /* === GLOBAL RESET === */
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(150deg, #ffffff 0%, #dbeafe 55%, #eff6ff 100%) !important;
            min-height: 100vh;
        }
        [data-testid="stHeader"] {
            background: rgba(255, 255, 255, 0.88) !important;
            backdrop-filter: blur(8px);
            border-bottom: 1px solid rgba(30, 58, 138, 0.12) !important;
        }
        .main .block-container {
            background: transparent !important;
        }

        /* === SIDEBAR === */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%) !important;
            border-right: 1px solid rgba(30, 58, 138, 0.15) !important;
        }
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] li {
            color: #1e3a8a !important;
        }
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #1e3a8a !important;
        }
        [data-testid="stSidebar"] [data-testid="stMetricValue"] {
            color: #1e3a8a !important;
        }
        [data-testid="stSidebar"] [data-testid="stMetricLabel"] {
            color: #475569 !important;
        }

        /* === TYPOGRAPHY === */
        h1 { color: #1e3a8a !important; font-weight: 700 !important; letter-spacing: -0.5px; }
        h2 { color: #1d4ed8 !important; font-weight: 600 !important; }
        h3 { color: #1d4ed8 !important; font-weight: 600 !important; }
        p, li, span { color: #1e293b !important; }
        label { color: #334155 !important; }

        /* === BUTTONS === */
        button[data-testid="baseButton-primary"] {
            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%) !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 16px rgba(30, 58, 138, 0.28) !important;
            transition: all 0.25s ease !important;
        }
        button[data-testid="baseButton-primary"]:hover {
            background: linear-gradient(135deg, #2563eb 0%, #3b82f6 100%) !important;
            box-shadow: 0 6px 22px rgba(37, 99, 235, 0.38) !important;
            transform: translateY(-2px) !important;
        }
        button[data-testid="baseButton-secondary"] {
            background: linear-gradient(135deg, rgba(219,234,254,0.85) 0%, rgba(191,219,254,0.65) 100%) !important;
            color: #1e3a8a !important;
            border: 1px solid rgba(30, 58, 138, 0.28) !important;
            border-radius: 10px !important;
            transition: all 0.2s ease !important;
        }
        button[data-testid="baseButton-secondary"]:hover {
            background: linear-gradient(135deg, rgba(191,219,254,0.9) 0%, rgba(147,197,253,0.6) 100%) !important;
        }

        /* === TEXT INPUT === */
        [data-testid="stTextInput"] input {
            background: rgba(255, 255, 255, 0.88) !important;
            color: #0f172a !important;
            border: 1px solid rgba(30, 58, 138, 0.28) !important;
            border-radius: 10px !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
        }
        [data-testid="stTextInput"] input:focus {
            border-color: #2563eb !important;
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.14) !important;
        }
        [data-testid="stTextInput"] input::placeholder { color: #94a3b8 !important; }

        /* === EXPANDER === */
        [data-testid="stExpander"] {
            background: rgba(255, 255, 255, 0.72) !important;
            border: 1px solid rgba(30, 58, 138, 0.15) !important;
            border-radius: 12px !important;
            backdrop-filter: blur(6px);
        }
        [data-testid="stExpander"] summary {
            color: #1d4ed8 !important;
        }

        /* === METRICS === */
        [data-testid="stMetricValue"] {
            color: #1e3a8a !important;
            font-weight: 700 !important;
        }
        [data-testid="stMetricLabel"] { color: #475569 !important; }
        [data-testid="stMetricDelta"] svg { fill: #059669 !important; }

        /* === PROGRESS BAR === */
        [data-testid="stProgress"] > div {
            background: rgba(219, 234, 254, 0.8) !important;
            border-radius: 99px !important;
        }
        [data-testid="stProgress"] > div > div {
            background: linear-gradient(90deg, #1e3a8a, #3b82f6) !important;
            border-radius: 99px !important;
        }

        /* === DIVIDER === */
        [data-testid="stDivider"] hr {
            border-color: rgba(30, 58, 138, 0.15) !important;
        }

        /* === ALERTS === */
        [data-testid="stAlert"] {
            background: rgba(255, 255, 255, 0.75) !important;
            border-radius: 10px !important;
        }

        /* === CAPTIONS === */
        [data-testid="stCaptionContainer"] p { color: #64748b !important; }

        /* === TOGGLE === */
        [data-testid="stToggle"] input[type="checkbox"] { accent-color: #2563eb !important; }

        /* === SUCCESS / WARNING === */
        div[data-testid="stAlert"][kind="success"] {
            background: rgba(16, 185, 129, 0.08) !important;
            border-left: 4px solid #10b981 !important;
        }
        div[data-testid="stAlert"][kind="warning"] {
            background: rgba(245, 158, 11, 0.08) !important;
            border-left: 4px solid #f59e0b !important;
        }

        /* === MISC === */
        [data-testid="column"] { padding: 0.4rem !important; }
        """

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# Inject theme before rendering anything else
inject_theme(st.session_state.dark_mode)

# ---------------------------------------------------------------------------
# Cached resources
# ---------------------------------------------------------------------------
@st.cache_data
def get_songs():
    data_path = Path(__file__).parent.parent / "data" / "songs.csv"
    return load_songs(str(data_path))


@st.cache_resource
def get_client(api_key: str):
    return anthropic.Anthropic(api_key=api_key)


def compute_detailed_scores(response: str, retrieved_songs: list) -> dict:
    if not response or not response.strip():
        return {"cited_count": 0, "total_songs": len(retrieved_songs),
                "attrs_found": [], "attrs_missing": list(ATTRIBUTE_KEYWORDS),
                "song_rate": 0.0, "attr_density": 0.0}

    response_lower = response.lower()
    cited_count = sum(1 for s in retrieved_songs if s["title"].lower() in response_lower)
    attrs_found  = sorted(a for a in ATTRIBUTE_KEYWORDS if a in response_lower)
    attrs_missing = sorted(a for a in ATTRIBUTE_KEYWORDS if a not in response_lower)

    return {
        "cited_count":   cited_count,
        "total_songs":   len(retrieved_songs),
        "attrs_found":   attrs_found,
        "attrs_missing": attrs_missing,
        "song_rate":     cited_count / max(len(retrieved_songs), 1),
        "attr_density":  len(attrs_found) / len(ATTRIBUTE_KEYWORDS),
    }


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuration")

    # Theme toggle
    dark = st.toggle("🌙 Dark mode", value=st.session_state.dark_mode)
    if dark != st.session_state.dark_mode:
        st.session_state.dark_mode = dark
        st.rerun()

    st.divider()

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
    moods  = sorted({s["mood"]  for s in songs})
    st.caption(f"**Genres:** {', '.join(genres)}")
    st.caption(f"**Moods:** {', '.join(moods)}")

    avg_energy = sum(s["energy"] for s in songs) / len(songs)
    avg_bpm    = sum(s["tempo_bpm"] for s in songs) / len(songs)
    st.caption(f"**Avg energy:** {avg_energy:.2f}  |  **Avg BPM:** {avg_bpm:.0f}")

    st.divider()
    st.caption("Model: Claude Sonnet 4.6")
    st.caption("Retrieval: keyword scoring")

    # Session stats
    if st.session_state.get("history"):
        history  = st.session_state.history
        avg_conf = sum(h["confidence"] for h in history) / len(history)
        pass_rt  = sum(1 for h in history if h["guardrail"]) / len(history)
        st.divider()
        st.subheader("📊 Session Stats")
        st.metric("Queries run", len(history))
        st.metric("Avg confidence", f"{avg_conf:.2f}")
        st.metric("Guardrail pass rate", f"{pass_rt:.0%}")
        st.caption(
            "Avg confidence tracks how specifically Claude cited song data "
            "across all your queries this session."
        )

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
accent = "#93c5fd" if st.session_state.dark_mode else "#1e3a8a"
sub    = "#60a5fa" if st.session_state.dark_mode else "#2563eb"

st.markdown(
    f"""
    <h1 style="
        background: linear-gradient(90deg, {accent}, {sub});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        font-size: 2.4rem;
        margin-bottom: 0;
    ">🎵 Mood Music</h1>
    """,
    unsafe_allow_html=True,
)
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
        retrieved    = retrieve_songs(query, songs, k=5)
        response     = run_rag(query, songs, client)
        confidence   = score_response(response, retrieved)
        guardrail_ok, _ = validate_output(response, retrieved)
        detail       = compute_detailed_scores(response, retrieved)

    # --- Retrieved songs ---
    with st.expander(f"📚 Retrieved {len(retrieved)} songs from catalog", expanded=False):
        st.caption(
            "Top-5 songs matched to your query by keyword scoring on mood, genre, and energy. "
            "Claude can only recommend from this list — nothing outside it."
        )
        for i, song in enumerate(retrieved, 1):
            st.markdown(f"**{i}. {song['title']}** — *{song['artist']}*")
            a, b, c, d = st.columns(4)
            a.caption(f"🎸 {song['genre']}")
            b.caption(f"😌 {song['mood']}")
            c.caption(f"🎵 {song['tempo_bpm']} BPM")
            d.caption(f"💃 dance {song['danceability']:.2f}")

            e1, e2, e3 = st.columns(3)
            e1.caption("Energy")
            e1.progress(float(song["energy"]), text=f"{song['energy']:.2f}")
            e2.caption("Valence (positivity)")
            e2.progress(float(song["valence"]), text=f"{song['valence']:.2f}")
            e3.caption("Acousticness")
            e3.progress(float(song["acousticness"]), text=f"{song['acousticness']:.2f}")
            st.divider()

    # --- Recommendation ---
    st.subheader("🎧 Recommendation")
    st.markdown(response)

    # --- Metrics ---
    st.divider()
    st.subheader("📈 Response Metrics")

    col1, col2, col3 = st.columns(3)

    col1.metric("Confidence Score", f"{confidence:.2f}")
    col1.caption(
        "Combined 0–1 score: half from how many retrieved songs Claude named, "
        "half from how many audio attributes it referenced. Higher = more grounded."
    )

    col2.metric("Songs Cited", f"{detail['cited_count']} / {detail['total_songs']}")
    col2.caption(
        "How many of the retrieved songs Claude mentioned by name. "
        "Citing more shows the response engaged with the full context, not just one pick."
    )

    col3.metric("Attributes Used", f"{len(detail['attrs_found'])} / {len(ATTRIBUTE_KEYWORDS)}")
    col3.caption(
        "How many of the 8 trackable audio attributes Claude referenced "
        "(energy, BPM, tempo, mood, genre, acousticness, valence, danceability). "
        "More = specific explanation, not a generic one."
    )

    col4, col5, _ = st.columns(3)

    if confidence >= 0.5:
        q_label, q_delta, q_color = "High", "grounded in data", "normal"
    elif confidence >= 0.3:
        q_label, q_delta, q_color = "Medium", "some attributes cited", "normal"
    else:
        q_label, q_delta, q_color = "Low", "generic response", "inverse"

    col4.metric("Response Quality", q_label, delta=q_delta, delta_color=q_color)
    col4.caption(
        "High ≥ 0.50 · Medium 0.30–0.49 · Low < 0.30. "
        "Reflects whether Claude was specific about why each song fits your request."
    )

    col5.metric("Guardrail", "✓ Pass" if guardrail_ok else "✗ Fail")
    col5.caption(
        "Hard check: response must be non-empty and name at least one retrieved song. "
        "Failure triggers a safe fallback message instead of showing Claude's output."
    )

    st.progress(confidence, text=f"Confidence: {confidence:.0%}")

    # Attribute detail
    with st.expander("🔍 Attribute coverage detail", expanded=False):
        st.caption(
            "The 8 audio attributes the system checks for in Claude's response. "
            "✅ referenced · ⬜ not mentioned."
        )
        found_str   = "  ".join(f"✅ `{a}`" for a in detail["attrs_found"])
        missing_str = "  ".join(f"⬜ `{a}`" for a in detail["attrs_missing"])
        if found_str:
            st.markdown(found_str)
        if missing_str:
            st.markdown(missing_str)

    # Save to session history
    if "history" not in st.session_state:
        st.session_state.history = []
    st.session_state.history.insert(0, {
        "query":      query,
        "retrieved":  retrieved,
        "response":   response,
        "confidence": confidence,
        "guardrail":  guardrail_ok,
        "detail":     detail,
    })

# ---------------------------------------------------------------------------
# Query history
# ---------------------------------------------------------------------------
if st.session_state.get("history"):
    history = st.session_state.history
    past = history[1:] if (run_btn and query and api_key) else history

    if past:
        st.divider()
        st.subheader("🕘 Previous Queries")
        for item in past:
            label = f'"{item["query"]}" — confidence {item["confidence"]:.2f}'
            with st.expander(label, expanded=False):
                st.markdown(item["response"])
                d = item.get("detail", {})
                c1, c2, c3, c4 = st.columns(4)
                c1.caption(f"Confidence: {item['confidence']:.2f}")
                c2.caption(f"Guardrail: {'Pass' if item['guardrail'] else 'Fail'}")
                c3.caption(f"Songs cited: {d.get('cited_count','?')}/{d.get('total_songs','?')}")
                c4.caption(f"Attrs used: {len(d.get('attrs_found',[]))}/{len(ATTRIBUTE_KEYWORDS)}")
