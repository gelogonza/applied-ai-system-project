"""
RAG pipeline for the music recommender.

Retrieval: keyword-based scoring against songs.csv (deterministic, no LLM).
Generation: Claude reasons over the retrieved songs to produce a recommendation
            that actively cites song attributes — genre, mood, energy, etc.
"""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import anthropic

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

LOG_FILE = Path("rag_log.jsonl")

# Attributes we expect Claude to reference when actively using the retrieved data
ATTRIBUTE_KEYWORDS = {
    "energy", "bpm", "tempo", "mood", "genre",
    "acousticness", "valence", "danceability",
}

# ---------------------------------------------------------------------------
# Keyword maps for retrieval
# Maps each catalog mood/genre value to natural-language synonyms.
# ---------------------------------------------------------------------------
MOOD_SYNONYMS: Dict[str, List[str]] = {
    "chill":       ["chill", "calm", "mellow", "laid-back", "relax", "relaxing", "easy"],
    "happy":       ["happy", "upbeat", "cheerful", "joyful", "fun", "positive"],
    "intense":     ["intense", "powerful", "epic", "strong"],
    "angry":       ["angry", "aggressive", "mad", "furious", "heavy"],
    "moody":       ["moody", "dark", "atmospheric", "brooding"],
    "energetic":   ["energetic", "hype", "hyped", "pumped", "workout", "gym", "run"],
    "focused":     ["focused", "focus", "study", "concentrate", "work", "productive"],
    "romantic":    ["romantic", "love", "date", "intimate"],
    "melancholic": ["melancholic", "sad", "melancholy", "emotional", "lonely"],
    "relaxed":     ["relaxed", "lounge", "slow"],
    "peaceful":    ["peaceful", "gentle", "soft", "quiet", "tranquil", "sleep"],
}

GENRE_SYNONYMS: Dict[str, List[str]] = {
    "lofi":      ["lofi", "lo-fi", "lo fi"],
    "pop":       ["pop"],
    "rock":      ["rock"],
    "jazz":      ["jazz"],
    "classical": ["classical", "orchestra", "piano", "orchestral"],
    "hip-hop":   ["hip-hop", "hip hop", "rap", "hiphop"],
    "ambient":   ["ambient", "background", "space"],
    "synthwave": ["synthwave", "synth", "electronic", "retro"],
    "indie pop": ["indie", "indie pop"],
    "r&b":       ["r&b", "rnb", "rhythm and blues", "soul"],
    "folk":      ["folk", "acoustic", "singer-songwriter"],
    "metal":     ["metal", "heavy metal"],
}

ENERGY_HIGH_WORDS = {
    "energetic", "intense", "workout", "gym", "run", "pump", "hype",
    "pumped", "heavy", "angry", "aggressive",
}
ENERGY_LOW_WORDS = {
    "calm", "chill", "peaceful", "study", "focus", "relax", "relaxing",
    "sleep", "gentle", "soft", "quiet", "mellow",
}

# ---------------------------------------------------------------------------
# System prompt (static — cached on every call to save tokens)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are a music recommendation assistant.

You will receive:
1. A user's free-text request describing what kind of music they want.
2. A numbered list of candidate songs retrieved from the catalog.

Your job:
- Recommend 1–3 songs from the retrieved list ONLY. Do not invent or mention songs
  that are not in the list.
- For EACH recommendation, explain WHY it fits the request by referencing specific
  song attributes from the data: genre, mood, energy level, tempo (BPM), valence,
  danceability, acousticness, or artist.
- Be concise — 2–4 sentences per recommendation.
- Do not recommend songs outside the retrieved list, even if you know better ones.
"""


# ---------------------------------------------------------------------------
# 1. Input guardrail
# ---------------------------------------------------------------------------
def validate_input(query: str) -> Tuple[bool, str]:
    """Return (is_valid, error_message). Empty error means valid."""
    if not query or not query.strip():
        return False, "Query is empty."
    if len(query.strip()) < 3:
        return False, "Query is too short (minimum 3 characters)."
    if len(query) > 500:
        return False, "Query is too long (maximum 500 characters)."
    return True, ""


# ---------------------------------------------------------------------------
# 2. Retrieval engine (deterministic — no LLM calls)
# ---------------------------------------------------------------------------
def retrieve_songs(query: str, songs: List[Dict], k: int = 5) -> List[Dict]:
    """
    Score each song against the query using keyword matching.
    Returns the top-k highest-scoring songs, sorted by score descending.
    """
    tokens = set(query.lower().split())
    scored: List[Tuple[Dict, float]] = []

    for song in songs:
        score = 0.0

        # Mood: +3 if any synonym of this song's mood appears in the query
        mood_synonyms = MOOD_SYNONYMS.get(song["mood"], [])
        if tokens & set(mood_synonyms):
            score += 3.0

        # Genre: +2 if any synonym of this song's genre appears in the query
        genre_synonyms = GENRE_SYNONYMS.get(song["genre"], [])
        if tokens & set(genre_synonyms):
            score += 2.0

        # Energy direction: reward high-energy songs for high-energy queries, and vice versa
        if tokens & ENERGY_HIGH_WORDS:
            score += song["energy"] * 2.0
        elif tokens & ENERGY_LOW_WORDS:
            score += (1.0 - song["energy"]) * 2.0

        scored.append((song, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_k = [song for song, _ in scored[:k]]
    log.info(
        "Retrieved %d songs for query %r: %s",
        len(top_k),
        query,
        [s["title"] for s in top_k],
    )
    return top_k


# ---------------------------------------------------------------------------
# 3. Context builder
# ---------------------------------------------------------------------------
def build_context(songs: List[Dict]) -> str:
    """Format retrieved songs into a structured block for the LLM prompt."""
    lines = []
    for i, s in enumerate(songs, 1):
        lines.append(
            f"{i}. \"{s['title']}\" by {s['artist']}"
            f" | genre: {s['genre']} | mood: {s['mood']}"
            f" | energy: {s['energy']} | valence: {s['valence']}"
            f" | tempo: {s['tempo_bpm']} BPM"
            f" | danceability: {s['danceability']}"
            f" | acousticness: {s['acousticness']}"
        )
    return "\n".join(lines)


def build_messages(query: str, retrieved_songs: List[Dict]) -> List[Dict]:
    context = build_context(retrieved_songs)
    user_content = (
        f"User request: {query}\n\n"
        f"Retrieved songs (recommend from these only):\n{context}"
    )
    return [{"role": "user", "content": user_content}]


# ---------------------------------------------------------------------------
# 4. Confidence scorer
# ---------------------------------------------------------------------------
def score_response(response: str, retrieved_songs: List[Dict]) -> float:
    """
    Return a confidence score 0.0–1.0 measuring how actively Claude used
    the retrieved song data.

    Combines two signals (equal weight):
    - song_citation_rate: fraction of retrieved songs mentioned by name
    - attribute_density:  fraction of key song attributes referenced
      (energy, bpm, tempo, mood, genre, acousticness, valence, danceability)

    A score near 1.0 means Claude cited multiple songs AND used their
    specific numeric/categorical attributes. A low score suggests the
    response was vague or ignored the retrieved context.
    """
    if not response or not response.strip():
        return 0.0

    response_lower = response.lower()

    cited = sum(1 for s in retrieved_songs if s["title"].lower() in response_lower)
    song_rate = cited / max(len(retrieved_songs), 1)

    attrs_present = sum(1 for a in ATTRIBUTE_KEYWORDS if a in response_lower)
    attr_density = attrs_present / len(ATTRIBUTE_KEYWORDS)

    return round(song_rate * 0.5 + attr_density * 0.5, 2)


# ---------------------------------------------------------------------------
# 5. Output guardrail
# ---------------------------------------------------------------------------
def validate_output(response: str, retrieved_songs: List[Dict]) -> Tuple[bool, str]:
    """Return (is_valid, error_message). Checks that the response is non-empty
    and mentions at least one retrieved song by name."""
    if not response or not response.strip():
        return False, "LLM returned an empty response."
    response_lower = response.lower()
    titles = [s["title"].lower() for s in retrieved_songs]
    if not any(title in response_lower for title in titles):
        return False, "Response does not mention any retrieved song by name."
    return True, ""


# ---------------------------------------------------------------------------
# 6. Logger
# ---------------------------------------------------------------------------
def log_to_file(
    query: str,
    retrieved_songs: List[Dict],
    response: str,
    guardrail_passed: bool,
    confidence: float = 0.0,
    error: str = "",
) -> None:
    """Append one JSON line to rag_log.jsonl for audit and debugging."""
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query": query,
        "retrieved_titles": [s["title"] for s in retrieved_songs],
        "response": response,
        "guardrail_passed": guardrail_passed,
        "confidence_score": confidence,
        "error": error,
    }
    with LOG_FILE.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    log.info("Logged interaction (guardrail_passed=%s)", guardrail_passed)


# ---------------------------------------------------------------------------
# 7. Main RAG pipeline
# ---------------------------------------------------------------------------
FALLBACK_RESPONSE = (
    "Sorry, I couldn't generate a valid recommendation. "
    "Please try rephrasing your request."
)


def run_rag(
    query: str,
    songs: List[Dict],
    client: anthropic.Anthropic,
    k: int = 5,
) -> str:
    """
    Full RAG pipeline:
      validate input → retrieve songs → build prompt →
      call Claude (with cached system prompt) → validate output → log → return.
    """
    # 1. Input guardrail
    valid, err = validate_input(query)
    if not valid:
        log.warning("Input guardrail blocked query: %s", err)
        return f"Invalid input: {err}"

    # 2. Retrieve
    retrieved = retrieve_songs(query, songs, k=k)

    # 3. Build messages
    messages = build_messages(query, retrieved)

    # 4. Call Claude
    # System prompt uses cache_control so the static instructions are cached
    # across repeated calls (saves tokens on every request after the first).
    log.info("Calling Claude (model=claude-sonnet-4-6)")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=messages,
    )
    response = message.content[0].text
    log.info(
        "Response received (%d chars) | cache_read=%s cache_create=%s",
        len(response),
        getattr(message.usage, "cache_read_input_tokens", "n/a"),
        getattr(message.usage, "cache_creation_input_tokens", "n/a"),
    )

    # 5. Score + output guardrail
    confidence = score_response(response, retrieved)
    valid_out, err_out = validate_output(response, retrieved)
    log_to_file(query, retrieved, response, valid_out, confidence=confidence, error=err_out)
    log.info("Confidence score: %.2f", confidence)

    if not valid_out:
        log.warning("Output guardrail failed: %s", err_out)
        return FALLBACK_RESPONSE

    return response
