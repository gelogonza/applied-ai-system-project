"""
Interactive CLI for the RAG music recommender.

Usage:
    python src/main_rag.py

Requires:
    ANTHROPIC_API_KEY environment variable (or a .env file in the project root).
"""

import os
import sys
from pathlib import Path

# Allow running as `python src/main_rag.py` from the project root.
sys.path.insert(0, str(Path(__file__).parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; key can be set directly in the environment

import anthropic

from rag import run_rag
from recommender import load_songs


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "Error: ANTHROPIC_API_KEY is not set.\n"
            "Set it with:  export ANTHROPIC_API_KEY=your_key_here\n"
            "Or add it to a .env file in the project root."
        )
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    # Resolve data path relative to this file so the script works from any cwd.
    data_path = Path(__file__).parent.parent / "data" / "songs.csv"
    songs = load_songs(str(data_path))
    print(f"Loaded {len(songs)} songs into the knowledge base.")
    print("=" * 60)
    print("  Music Recommender — RAG powered by Claude")
    print("  Type 'quit' or press Ctrl-C to exit.")
    print("=" * 60)

    while True:
        try:
            query = input("\nWhat kind of music are you in the mood for?\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if query.lower() in {"quit", "exit", "q"}:
            print("Goodbye!")
            break

        if not query:
            continue

        print("\nSearching and generating recommendation...\n")
        response = run_rag(query, songs, client)
        print(response)


if __name__ == "__main__":
    main()
