"""
Tests for the RAG pipeline.

All tests are deterministic — they do NOT call the Claude API.
The consistency test verifies that the retrieval layer always returns
the same songs in the same order for the same query (no randomness).
"""

from src.rag import (
    build_context,
    retrieve_songs,
    score_response,
    validate_input,
    validate_output,
)

# ---------------------------------------------------------------------------
# A small, fixed catalog used by every test (subset of data/songs.csv)
# ---------------------------------------------------------------------------
CATALOG = [
    {
        "id": 2, "title": "Midnight Coding", "artist": "LoRoom",
        "genre": "lofi", "mood": "chill",
        "energy": 0.42, "tempo_bpm": 78, "valence": 0.56,
        "danceability": 0.62, "acousticness": 0.71,
    },
    {
        "id": 4, "title": "Library Rain", "artist": "Paper Lanterns",
        "genre": "lofi", "mood": "chill",
        "energy": 0.35, "tempo_bpm": 72, "valence": 0.60,
        "danceability": 0.58, "acousticness": 0.86,
    },
    {
        "id": 5, "title": "Gym Hero", "artist": "Max Pulse",
        "genre": "pop", "mood": "intense",
        "energy": 0.93, "tempo_bpm": 132, "valence": 0.77,
        "danceability": 0.88, "acousticness": 0.05,
    },
    {
        "id": 14, "title": "Iron Abyss", "artist": "Dreadmoor",
        "genre": "metal", "mood": "angry",
        "energy": 0.96, "tempo_bpm": 178, "valence": 0.22,
        "danceability": 0.43, "acousticness": 0.02,
    },
    {
        "id": 11, "title": "Street Anthem", "artist": "Kael Cipher",
        "genre": "hip-hop", "mood": "energetic",
        "energy": 0.87, "tempo_bpm": 138, "valence": 0.73,
        "danceability": 0.92, "acousticness": 0.04,
    },
]


# ---------------------------------------------------------------------------
# Input guardrail tests
# ---------------------------------------------------------------------------

class TestValidateInput:
    def test_empty_string(self):
        ok, err = validate_input("")
        assert not ok
        assert "empty" in err.lower()

    def test_whitespace_only(self):
        ok, _ = validate_input("   ")
        assert not ok

    def test_too_short(self):
        ok, err = validate_input("hi")
        assert not ok
        assert "short" in err.lower()

    def test_too_long(self):
        ok, _ = validate_input("x" * 501)
        assert not ok

    def test_valid_query(self):
        ok, err = validate_input("something chill to study to")
        assert ok
        assert err == ""

    def test_boundary_exactly_3_chars(self):
        ok, _ = validate_input("lof")
        assert ok

    def test_boundary_exactly_500_chars(self):
        ok, _ = validate_input("a" * 500)
        assert ok


# ---------------------------------------------------------------------------
# Retrieval tests
# ---------------------------------------------------------------------------

class TestRetrieveSongs:
    def test_returns_k_songs(self):
        results = retrieve_songs("chill study", CATALOG, k=2)
        assert len(results) == 2

    def test_chill_query_surfaces_lofi(self):
        results = retrieve_songs("something chill and calm to relax", CATALOG, k=3)
        genres = [s["genre"] for s in results]
        assert "lofi" in genres

    def test_workout_query_surfaces_high_energy(self):
        results = retrieve_songs("intense workout gym music", CATALOG, k=2)
        top = results[0]
        assert top["energy"] >= 0.85, f"Expected high energy, got {top['energy']}"

    def test_lofi_keyword_matches_genre(self):
        results = retrieve_songs("lofi beats", CATALOG, k=2)
        genres = [s["genre"] for s in results]
        assert "lofi" in genres

    def test_k_greater_than_catalog(self):
        results = retrieve_songs("anything", CATALOG, k=100)
        assert len(results) == len(CATALOG)

    def test_retrieval_is_deterministic(self):
        """Same query must always return the same songs in the same order."""
        query = "chill lofi focus study music"
        run1 = [s["title"] for s in retrieve_songs(query, CATALOG, k=3)]
        run2 = [s["title"] for s in retrieve_songs(query, CATALOG, k=3)]
        assert run1 == run2, "Retrieval is non-deterministic — same query gave different results"

    def test_consistency_across_multiple_runs(self):
        """Run the same query 5 times; all results must be identical."""
        query = "energetic hip-hop hype"
        baseline = [s["title"] for s in retrieve_songs(query, CATALOG, k=3)]
        for _ in range(4):
            result = [s["title"] for s in retrieve_songs(query, CATALOG, k=3)]
            assert result == baseline


# ---------------------------------------------------------------------------
# Output guardrail tests
# ---------------------------------------------------------------------------

class TestValidateOutput:
    def test_empty_response(self):
        ok, err = validate_output("", CATALOG)
        assert not ok
        assert "empty" in err.lower()

    def test_whitespace_only_response(self):
        ok, _ = validate_output("   ", CATALOG)
        assert not ok

    def test_response_with_no_song_title(self):
        ok, err = validate_output("Great music for your workout!", CATALOG)
        assert not ok
        assert "song" in err.lower() or "name" in err.lower()

    def test_response_mentioning_song(self):
        ok, err = validate_output(
            "You should listen to Midnight Coding — perfect for studying.",
            CATALOG,
        )
        assert ok
        assert err == ""

    def test_response_case_insensitive(self):
        ok, _ = validate_output("try MIDNIGHT CODING for a chill vibe.", CATALOG)
        assert ok

    def test_response_mentioning_second_song(self):
        ok, _ = validate_output("Iron Abyss will power your workout session.", CATALOG)
        assert ok


# ---------------------------------------------------------------------------
# Confidence scorer tests
# ---------------------------------------------------------------------------

class TestScoreResponse:
    def test_empty_response_scores_zero(self):
        assert score_response("", CATALOG) == 0.0

    def test_whitespace_scores_zero(self):
        assert score_response("   ", CATALOG) == 0.0

    def test_generic_response_scores_low(self):
        # No song titles, no attribute keywords
        score = score_response("I recommend some great music for you!", CATALOG)
        assert score < 0.3

    def test_response_with_song_and_attributes_scores_high(self):
        # Cites 1 of 5 songs + 7 of 8 attributes → song_rate=0.10, attr=0.44 → ~0.54
        response = (
            "Midnight Coding by LoRoom has a chill mood with energy 0.42 "
            "and high acousticness. Its slow tempo of 78 BPM and lofi genre "
            "make it perfect for studying. The valence is 0.56."
        )
        score = score_response(response, CATALOG)
        assert score >= 0.5

    def test_score_is_between_zero_and_one(self):
        response = "Library Rain — energy 0.35, 72 BPM, acousticness 0.86, mood chill."
        score = score_response(response, CATALOG)
        assert 0.0 <= score <= 1.0

    def test_more_songs_cited_raises_score(self):
        one_song = "Try Midnight Coding — it has low energy and good acousticness."
        two_songs = (
            "Try Midnight Coding — it has low energy and good acousticness. "
            "Library Rain is also great for its slow tempo and chill mood."
        )
        assert score_response(two_songs, CATALOG) > score_response(one_song, CATALOG)


# ---------------------------------------------------------------------------
# Context builder smoke test
# ---------------------------------------------------------------------------

class TestBuildContext:
    def test_all_songs_present(self):
        ctx = build_context(CATALOG)
        for song in CATALOG:
            assert song["title"] in ctx

    def test_attributes_present(self):
        ctx = build_context(CATALOG[:1])
        assert "energy" in ctx
        assert "mood" in ctx
        assert "genre" in ctx
        assert "BPM" in ctx
