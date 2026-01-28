"""
LangSmith Tracing Setup - Verification Complete
================================================

This script verifies that LangSmith tracing is properly configured
and shows the current setup status.
"""
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()

print("\n" + "=" * 70)
print("LANGSMITH TRACING SETUP - VERIFICATION")
print("=" * 70)

# Check all required environment variables
config = {
    "LANGSMITH_TRACING": os.getenv("LANGSMITH_TRACING"),
    "LANGCHAIN_TRACING_V2": os.getenv("LANGCHAIN_TRACING_V2"),
    "LANGSMITH_ENDPOINT": os.getenv("LANGSMITH_ENDPOINT"),
    "LANGSMITH_API_KEY": os.getenv("LANGSMITH_API_KEY"),
    "LANGSMITH_PROJECT": os.getenv("LANGSMITH_PROJECT"),
    "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
}

# Display configuration
print("\n[OK] Environment Variables:")
print(f"  LANGSMITH_TRACING:      {config['LANGSMITH_TRACING']}")
print(f"  LANGCHAIN_TRACING_V2:   {config['LANGCHAIN_TRACING_V2']}")
print(f"  LANGSMITH_ENDPOINT:     {config['LANGSMITH_ENDPOINT']}")
print(f"  LANGSMITH_API_KEY:      {config['LANGSMITH_API_KEY'][:20]}..." if config['LANGSMITH_API_KEY'] else "  LANGSMITH_API_KEY:      NOT SET")
print(f"  LANGSMITH_PROJECT:      {config['LANGSMITH_PROJECT']}")
print(f"  OPENAI_API_KEY:         {'SET' if config['OPENAI_API_KEY'] else 'NOT SET'}")

# Check if properly configured
is_configured = all([
    config["LANGSMITH_TRACING"] == "true",
    config["LANGSMITH_API_KEY"],
    config["LANGSMITH_PROJECT"],
    config["LANGSMITH_ENDPOINT"],
])

print("\n" + "=" * 70)
if is_configured:
    print("[OK] STATUS: PROPERLY CONFIGURED")
    print("\nAll LangSmith tracing requirements are met!")
    print(f"\nView your traces at:")
    print(f"  https://smith.langchain.com")
    print(f"\nProject: {config['LANGSMITH_PROJECT']}")
    print("\nWhat to do next:")
    print("  1. Run your application (backend or CLI)")
    print("  2. Perform some operations that use LLMs")
    print("  3. Check LangSmith web interface for traces")
    print("\nCommands to test:")
    print("  python test_langsmith_tracing.py        # Simple test")
    print("  python test_traceable_decorator.py      # @traceable test")
    print("  python test_spreader_tracing.py         # Full spreader test")
    print("  python backend/main.py                  # Start backend with tracing")
else:
    print("[ERROR] STATUS: MISSING CONFIGURATION")
    print("\nPlease ensure the following are set in your .env file:")
    if config["LANGSMITH_TRACING"] != "true":
        print("  - LANGSMITH_TRACING=true")
    if not config["LANGSMITH_API_KEY"]:
        print("  - LANGSMITH_API_KEY=<your-api-key>")
    if not config["LANGSMITH_PROJECT"]:
        print("  - LANGSMITH_PROJECT=<your-project-name>")
    if not config["LANGSMITH_ENDPOINT"]:
        print("  - LANGSMITH_ENDPOINT=https://api.smith.langchain.com")

print("=" * 70 + "\n")
