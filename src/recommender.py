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

def score_song(song: Dict, user_prefs: Dict) -> Tuple[int, List[str]]:
    """Score one song against user_prefs on a 12-point scale and return (score, reasons)."""
    score = 0
    reasons: List[str] = []

    # --- Mood (max 4 pts) ---
    if song["mood"] == user_prefs["mood"]:
        score += 4
        reasons.append(f"mood match '{song['mood']}' (+4)")
    else:
        reasons.append(f"mood '{song['mood']}' != '{user_prefs['mood']}' (+0)")

    # --- Genre (max 3 pts) ---
    if song["genre"] == user_prefs["genre"]:
        score += 3
        reasons.append(f"genre match '{song['genre']}' (+3)")
    else:
        reasons.append(f"genre '{song['genre']}' != '{user_prefs['genre']}' (+0)")

    # --- Energy (max 3 pts) ---
    delta_energy = abs(song["energy"] - user_prefs["energy"])
    if delta_energy <= 0.10:
        score += 3
        reasons.append(f"energy Δ{delta_energy:.2f} ≤ 0.10 (+3)")
    elif delta_energy <= 0.20:
        score += 2
        reasons.append(f"energy Δ{delta_energy:.2f} ≤ 0.20 (+2)")
    elif delta_energy <= 0.35:
        score += 1
        reasons.append(f"energy Δ{delta_energy:.2f} ≤ 0.35 (+1)")
    else:
        reasons.append(f"energy Δ{delta_energy:.2f} > 0.35 (+0)")

    # --- Valence (max 2 pts) ---
    delta_valence = abs(song["valence"] - user_prefs["valence"])
    if delta_valence <= 0.10:
        score += 2
        reasons.append(f"valence Δ{delta_valence:.2f} ≤ 0.10 (+2)")
    elif delta_valence <= 0.25:
        score += 1
        reasons.append(f"valence Δ{delta_valence:.2f} ≤ 0.25 (+1)")
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
