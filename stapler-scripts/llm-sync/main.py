import sys
from pathlib import Path

# Add src to python path
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))

from cli import main

if __name__ == "__main__":
    main()
