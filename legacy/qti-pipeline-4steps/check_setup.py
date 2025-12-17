#!/usr/bin/env python3
"""Verification script for PDF to QTI setup.

Checks dependencies, environment variables, and module imports.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("PDF to QTI Setup Verification")
print("=" * 60)
print()

# Check dependencies
print("📦 Checking dependencies...")
missing_deps = []
required_deps = {
    "click": "click",
    "requests": "requests",
    "google.genai": "google-genai",
    "openai": "openai",
    "boto3": "boto3",
    "PIL": "Pillow",
    "pydantic": "pydantic",
    "dotenv": "python-dotenv",
}

for module_name, package_name in required_deps.items():
    try:
        __import__(module_name)
        print(f"  ✅ {package_name}")
    except ImportError:
        print(f"  ❌ {package_name} (missing)")
        missing_deps.append(package_name)

if missing_deps:
    print()
    print(f"⚠️  Missing dependencies: {', '.join(missing_deps)}")
    print(f"   Install with: pip install {' '.join(missing_deps)}")
else:
    print("  ✅ All dependencies installed")
print()

# Check environment variables
print("🔑 Checking environment variables...")
try:
    from config import Config
    
    providers_available = []
    
    if Config.GEMINI_API_KEY:
        print("  ✅ GEMINI_API_KEY")
        providers_available.append("gemini")
    else:
        print("  ⚠️  GEMINI_API_KEY (not set)")
    
    # Note: Only Gemini is used in this project
    if Config.OPENAI_API_KEY:
        print("  ℹ️  OPENAI_API_KEY (not needed - using Gemini only)")
    else:
        print("  ℹ️  OPENAI_API_KEY (not needed - using Gemini only)")
    
    if Config.AWS_ACCESS_KEY_ID and Config.AWS_SECRET_ACCESS_KEY:
        print("  ℹ️  AWS credentials (not needed - using Gemini only)")
    else:
        print("  ℹ️  AWS credentials (not needed - using Gemini only)")
    
    if Config.EXTEND_API_KEY:
        print("  ✅ EXTEND_API_KEY (for PDF parsing)")
    else:
        print("  ⚠️  EXTEND_API_KEY (not set - required for parse step)")
    
    print()
    if providers_available:
        if "gemini" in providers_available:
            print(f"  ✅ Gemini configured (will be used by default)")
        else:
            print(f"  ✅ Available AI providers: {', '.join(providers_available)}")
    else:
        print("  ❌ No AI providers configured!")
        print("     Set GEMINI_API_KEY in .env file")
    
except Exception as e:
    print(f"  ❌ Error loading config: {e}")
print()

# Check module imports
print("📚 Checking module imports...")
try:
    from config import Config
    from models import PipelineReport
    from pipeline import PDFParser, Segmenter, Generator, Validator
    print("  ✅ All modules import successfully")
except ImportError as e:
    print(f"  ❌ Import error: {e}")
    print("     Make sure you're running from the pdf-to-qti directory")
    sys.exit(1)
except Exception as e:
    print(f"  ❌ Error: {e}")
    sys.exit(1)
print()

# Summary
print("=" * 60)
if missing_deps:
    print("❌ Setup incomplete - missing dependencies")
    sys.exit(1)
elif not providers_available:
    print("⚠️  Setup incomplete - no AI providers configured")
    print("   You can still test imports, but pipeline won't run")
    sys.exit(0)
elif not Config.EXTEND_API_KEY:
    print("⚠️  Setup mostly complete")
    print("   Missing EXTEND_API_KEY - parse step won't work")
    print("   But you can use pre-parsed JSON files")
    sys.exit(0)
else:
    print("✅ Setup complete! Ready to convert PDFs to QTI")
    sys.exit(0)
