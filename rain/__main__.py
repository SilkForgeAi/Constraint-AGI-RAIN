"""Run Rain via python -m rain (same as python run.py)."""
import sys
from pathlib import Path
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))
from run import main
if __name__ == "__main__":
    main()

