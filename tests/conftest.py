"""
Add src/ to sys.path so that `from recommender import ...` works inside
src/rag.py when pytest imports it as src.rag from the project root.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
