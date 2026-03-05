"""Legacy compatibility wrapper.

Canonical entrypoint: scripts.qa_scan
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.qa_scan import *  # noqa: F401,F403
from scripts.qa_scan import main


if __name__ == "__main__":
    main()
