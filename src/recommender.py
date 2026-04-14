from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        # TODO: Implement explanation logic
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """Read a songs CSV and return a list of dicts with numeric fields cast to int/float."""
    import csv

    int_fields = {"id", "tempo_bpm"}
    float_fields = {"energy", "valence", "danceability", "acousticness"}

    songs = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for field in int_fields:
                row[field] = int(row[field])
            for field in float_fields:
                row[field] = float(row[field])
            songs.append(row)
    return songs

# --- Scoring weights (edit here to experiment with sensitivity) ---
# Weight-shift experiment: energy doubled, genre halved
#   Original  →  mood 4 | genre 3 | energy 3/2/1 | valence 2/1
#   Current   →  mood 4 | genre 2 | energy 6/4/2 | valence 2/1
W_MOOD          = 4   # unchanged
W_GENRE         = 2   # halved from 3 (3 ÷ 2 rounded up)
W_ENERGY_CLOSE  = 6   # doubled from 3  (Δ ≤ 0.10)
W_ENERGY_MID    = 4   # doubled from 2  (Δ ≤ 0.20)
W_ENERGY_FAR    = 2   # doubled from 1  (Δ ≤ 0.35)
W_VALENCE_CLOSE = 2   # unchanged       (Δ ≤ 0.10)
W_VALENCE_MID   = 1   # unchanged       (Δ ≤ 0.25)

# Derived max — import this in main.py so the display stays in sync
MAX_SCORE = W_MOOD + W_GENRE + W_ENERGY_CLOSE + W_VALENCE_CLOSE  # 14


def score_song(song: Dict, user_prefs: Dict) -> Tuple[int, List[str]]:
    """Score one song against user_prefs using the weight constants above; return (score, reasons)."""
    score = 0
    reasons: List[str] = []

    # --- Mood (max W_MOOD pts) ---
    if song["mood"] == user_prefs["mood"]:
        score += W_MOOD
        reasons.append(f"mood match '{song['mood']}' (+{W_MOOD})")
    else:
        reasons.append(f"mood '{song['mood']}' != '{user_prefs['mood']}' (+0)")

    # --- Genre (max W_GENRE pts) ---
    if song["genre"] == user_prefs["genre"]:
        score += W_GENRE
        reasons.append(f"genre match '{song['genre']}' (+{W_GENRE})")
    else:
        reasons.append(f"genre '{song['genre']}' != '{user_prefs['genre']}' (+0)")

    # --- Energy (max W_ENERGY_CLOSE pts) ---
    delta_energy = abs(song["energy"] - user_prefs["energy"])
    if delta_energy <= 0.10:
        score += W_ENERGY_CLOSE
        reasons.append(f"energy Δ{delta_energy:.2f} ≤ 0.10 (+{W_ENERGY_CLOSE})")
    elif delta_energy <= 0.20:
        score += W_ENERGY_MID
        reasons.append(f"energy Δ{delta_energy:.2f} ≤ 0.20 (+{W_ENERGY_MID})")
    elif delta_energy <= 0.35:
        score += W_ENERGY_FAR
        reasons.append(f"energy Δ{delta_energy:.2f} ≤ 0.35 (+{W_ENERGY_FAR})")
    else:
        reasons.append(f"energy Δ{delta_energy:.2f} > 0.35 (+0)")

    # --- Valence (max W_VALENCE_CLOSE pts) ---
    delta_valence = abs(song["valence"] - user_prefs["valence"])
    if delta_valence <= 0.10:
        score += W_VALENCE_CLOSE
        reasons.append(f"valence Δ{delta_valence:.2f} ≤ 0.10 (+{W_VALENCE_CLOSE})")
    elif delta_valence <= 0.25:
        score += W_VALENCE_MID
        reasons.append(f"valence Δ{delta_valence:.2f} ≤ 0.25 (+{W_VALENCE_MID})")
    else:
        reasons.append(f"valence Δ{delta_valence:.2f} > 0.25 (+0)")

    return score, reasons


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """Score every song with score_song, sort by score descending, and return the top k results."""
    results = []
    for song in songs:
        score, reasons = score_song(song, user_prefs)
        results.append((song, score, "; ".join(reasons)))

    return sorted(results, key=lambda item: item[1], reverse=True)[:k]
