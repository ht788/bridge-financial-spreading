"""
Main entry point for the FastAPI backend server.

Run with: python backend/main.py
Or with hot reload: uvicorn backend.main:app --reload
"""

import uvicorn
import os
from pathlib import Path

# Load environment variables from parent directory
from dotenv import load_dotenv
parent_dir = Path(__file__).parent.parent
env_path = parent_dir / ".env"
load_dotenv(env_path)


def main():
    """Start the FastAPI server with uvicorn"""
    
    # Configuration
    # Render.com sets PORT environment variable, use it if available
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("PORT") or os.getenv("API_PORT", "8000"))
    reload = False  # Reload doesn't work when passing app object directly
    
    print("="*60)
    print("Bridge Financial Spreader - API Server")
    print("="*60)
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  Reload: {reload}")
    print(f"  Docs: http://{host}:{port}/docs")
    print("="*60)
    
    # Import the app directly to avoid module path issues
    import sys
    sys.path.insert(0, str(parent_dir))
    from backend.api import app
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )


if __name__ == "__main__":
    main()
