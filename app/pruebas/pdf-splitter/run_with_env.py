#!/usr/bin/env python3
"""
Wrapper script to run pdf-splitter with environment variables loaded.
"""

import sys
from pathlib import Path

# Load .env file from project root
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"

if env_file.exists():
    from dotenv import load_dotenv
    load_dotenv(env_file)
    print(f"✅ Loaded environment variables from {env_file}")
else:
    print(f"⚠️  .env file not found at {env_file}")

# Now import and run main
from main import main

if __name__ == "__main__":
    sys.exit(main())
