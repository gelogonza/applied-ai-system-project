"""
Command line runner for the Music Recommender Simulation.
"""

from recommender import load_songs, recommend_songs, MAX_SCORE

SEPARATOR = "-" * 60


def show_recommendations(label: str, user_prefs: dict, songs: list, k: int = 5) -> None:
    print(f"\n{'=' * 60}")
    print(f"  Profile: {label}")
    print(f"{'=' * 60}")

    recommendations = recommend_songs(user_prefs, songs, k=k)

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n  #{rank}  {song['title']:<35} {score:>2.0f} / {MAX_SCORE}")
        print(f"       {SEPARATOR}")
        for reason in explanation.split("; "):
            print(f"       {reason}")


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded {len(songs)} songs.")

    # ------------------------------------------------------------------
    # Standard profiles
    # ------------------------------------------------------------------
    standard_profiles = [
        {
            "label": "Chill Lofi  |  lofi / chill  |  energy 0.38  |  valence 0.58",
            "prefs": {
                "genre": "lofi",
                "mood":  "chill",
                "energy":  0.38,
                "valence": 0.58,
            },
        },
        {
            "label": "High-Energy Pop  |  pop / intense  |  energy 0.90  |  valence 0.75",
            "prefs": {
                "genre": "pop",
                "mood":  "intense",
                "energy":  0.90,
                "valence": 0.75,
            },
        },
        {
            "label": "Deep Intense Rock  |  rock / intense  |  energy 0.92  |  valence 0.42",
            "prefs": {
                "genre": "rock",
                "mood":  "intense",
                "energy":  0.92,
                "valence": 0.42,
            },
        },
    ]

    # ------------------------------------------------------------------
    # Adversarial / edge-case profiles
    # Each one is designed to expose a known bias in the scoring system.
    # ------------------------------------------------------------------
    adversarial_profiles = [
        {
            # Genre says lofi (calm), mood says angry (intense) — direct contradiction.
            # Expected: angry mood (+4) outweighs the lofi genre preference (+3),
            # so a metal track (Iron Abyss) floats to #1 despite the user asking for lofi.
            "label": "Impossible Combo  |  lofi / angry  |  energy 0.95  |  valence 0.15",
            "prefs": {
                "genre": "lofi",
                "mood":  "angry",
                "energy":  0.95,
                "valence": 0.15,
            },
        },
        {
            # 'country' does not exist in the catalog — genre points (3 pts) are
            # permanently zeroed out for every song. Falls back entirely on mood + numerics.
            # Exposes genre string fragility: similar genres ('folk') earn nothing.
            "label": "Ghost Genre  |  country / chill  |  energy 0.35  |  valence 0.65",
            "prefs": {
                "genre": "country",
                "mood":  "chill",
                "energy":  0.35,
                "valence": 0.65,
            },
        },
        {
            # Both genre ('zydeco') and mood ('ethereal') are absent from the catalog.
            # No song ever earns the 7 categorical points — the ranking is decided
            # entirely by numeric proximity. Mid-range 0.50 / 0.50 gives partial
            # points to almost every song, producing a flat, noisy top-5.
            "label": "Dead Center  |  zydeco / ethereal  |  energy 0.50  |  valence 0.50",
            "prefs": {
                "genre": "zydeco",
                "mood":  "ethereal",
                "energy":  0.50,
                "valence": 0.50,
            },
        },
    ]

    print("\n\n>>> STANDARD PROFILES")
    for profile in standard_profiles:
        show_recommendations(profile["label"], profile["prefs"], songs)

    print("\n\n>>> ADVERSARIAL / EDGE-CASE PROFILES")
    for profile in adversarial_profiles:
        show_recommendations(profile["label"], profile["prefs"], songs)

    print()


if __name__ == "__main__":
    main()
