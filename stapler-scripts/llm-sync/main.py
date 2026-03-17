import sys
from pathlib import Path

# Add project root to python path so we can import llm_sync as a package
sys.path.append(str(Path(__file__).parent))

from llm_sync.cli import main

if __name__ == "__main__":
    main()
