#!/usr/bin/env python3
"""
main.py - The Entry Point (LangSmith-Native)

CLI entry point with FULL LangSmith integration.
All operations are automatically traced when LANGSMITH_API_KEY is set.

LangSmith Integration:
- Set LANGSMITH_API_KEY → automatic tracing of all LLM calls
- Set LANGSMITH_PROJECT → organize traces by project
- View traces at: https://smith.langchain.com

Usage:
    python main.py <pdf_path> <doc_type> [--period PERIOD] [--output FILE]
    
Examples:
    python main.py financials.pdf income --period "FY2024"
    python main.py balance_sheet.pdf balance --output result.json
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Load environment variables FIRST (before any LangSmith imports)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# LangSmith tracing activates automatically when LANGSMITH_API_KEY is set
# No explicit initialization needed - the SDK handles it


def setup_logging(verbose: bool = False) -> None:
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("langsmith").setLevel(logging.INFO)


def validate_environment() -> bool:
    """
    Validate that required environment variables are set.
    
    LANGSMITH CONFIGURATION:
    - LANGSMITH_API_KEY: Required for tracing (get from smith.langchain.com)
    - LANGSMITH_PROJECT: Project name for organizing traces
    - LANGSMITH_TRACING: Set to "true" to enable (default if API key set)
    """
    logger = logging.getLogger(__name__)
    
    # Required for LLM calls (Anthropic Claude is the primary provider)
    required_vars = ["ANTHROPIC_API_KEY"]
    
    # Required for full LangSmith integration
    langsmith_vars = ["LANGSMITH_API_KEY"]
    
    # Optional but recommended
    optional_vars = ["LANGSMITH_PROJECT"]
    
    missing_required = []
    missing_langsmith = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    for var in langsmith_vars:
        if not os.getenv(var):
            missing_langsmith.append(var)
    
    if missing_required:
        logger.error(
            f"[ERROR] Missing required environment variables: {', '.join(missing_required)}\n"
            f"   Please set these in your .env file."
        )
        return False
    
    # LangSmith configuration check
    if missing_langsmith:
        logger.warning(
            f"[WARNING] Missing LangSmith variables: {', '.join(missing_langsmith)}\n"
            f"   LLM calls will NOT be traced. Set LANGSMITH_API_KEY for full observability.\n"
            f"   Get your API key at: https://smith.langchain.com/settings"
        )
    else:
        project = os.getenv("LANGSMITH_PROJECT", "default")
        logger.info(f"[OK] LangSmith tracing enabled -> Project: {project}")
        logger.info(f"   View traces at: https://smith.langchain.com/projects/{project}")
    
    return True


def print_langsmith_info():
    """Print LangSmith configuration info."""
    print("\n" + "="*60)
    print("LANGSMITH CONFIGURATION")
    print("="*60)
    
    api_key = os.getenv("LANGSMITH_API_KEY")
    project = os.getenv("LANGSMITH_PROJECT", "default")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    # Anthropic status (primary provider)
    if anthropic_key:
        masked_anthropic = anthropic_key[:10] + "..." + anthropic_key[-4:] if len(anthropic_key) > 14 else "***"
        print(f"  ANTHROPIC_API_KEY:  {masked_anthropic} [OK]")
    else:
        print("  ANTHROPIC_API_KEY:  NOT SET [ERROR]")
    
    # LangSmith status
    if api_key:
        masked_key = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else "***"
        print(f"  LANGSMITH_API_KEY:  {masked_key} [OK]")
        print(f"  LANGSMITH_PROJECT:  {project}")
        print(f"  Status:             TRACING ENABLED")
        print(f"\n  View traces at:")
        print(f"     https://smith.langchain.com/projects/{project}")
    else:
        print("  LANGSMITH_API_KEY:  NOT SET [WARNING]")
        print("  Status:             TRACING DISABLED")
        print(f"\n  To enable tracing, add to your .env file:")
        print(f"     LANGSMITH_API_KEY=lsv2_pt_your_key_here")
        print(f"     LANGSMITH_PROJECT=financial-spreader-v1")
    
    print("="*60 + "\n")


def create_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        prog="financial-spreader",
        description="Spread financial statements from PDF to structured JSON (LangSmith-traced)",
        epilog="""
Examples:
  %(prog)s financials.pdf income
  %(prog)s balance_sheet.pdf balance --period "Q4 2024"
  %(prog)s annual_report.pdf income --output results.json --verbose

LangSmith:
  All LLM calls are automatically traced when LANGSMITH_API_KEY is set.
  View your traces at: https://smith.langchain.com
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Positional arguments (optional if using --show-config)
    parser.add_argument(
        "pdf_path",
        type=str,
        nargs="?",  # Makes it optional
        help="Path to the PDF financial statement"
    )
    
    parser.add_argument(
        "doc_type",
        type=str,
        nargs="?",  # Makes it optional
        choices=["income", "balance"],
        help="Type of financial statement to extract"
    )
    
    # Optional arguments
    parser.add_argument(
        "--period", "-p",
        type=str,
        default="Latest",
        help="Fiscal period to extract (default: 'Latest')"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Output file path (default: stdout)"
    )
    
    parser.add_argument(
        "--model", "-m",
        type=str,
        default=None,
        help="Override model (for testing; production uses LangSmith Hub config)"
    )
    
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Maximum pages to process (default: all)"
    )
    
    parser.add_argument(
        "--dpi",
        type=int,
        default=200,
        help="DPI for PDF image conversion (default: 200)"
    )
    
    # NOTE: --fallback-prompt has been removed.
    # All prompts MUST come from LangSmith Hub.
    # If Hub is unavailable, the CLI will fail with a clear error.
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output"
    )
    
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="Show LangSmith configuration and exit"
    )
    
    return parser


def main() -> int:
    """
    Main entry point for the CLI.
    
    All operations are automatically traced to LangSmith when
    LANGSMITH_API_KEY is set in the environment.
    """
    # Parse arguments
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)
    
    # Show config if requested (doesn't require pdf_path)
    if args.show_config:
        print_langsmith_info()
        return 0
    
    # Validate that required args are present (if not --show-config)
    if not args.pdf_path or not args.doc_type:
        parser.error("pdf_path and doc_type are required (unless using --show-config)")
    
    # Validate environment
    if not validate_environment():
        return 1
    
    # Validate PDF path
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        logger.error(f"[ERROR] PDF file not found: {args.pdf_path}")
        return 1
    
    if not pdf_path.suffix.lower() == ".pdf":
        logger.error(f"[ERROR] File is not a PDF: {args.pdf_path}")
        return 1
    
    # Import spreader (after environment is validated)
    try:
        from spreader import spread_financials
    except ImportError as e:
        logger.error(f"[ERROR] Failed to import spreader module: {e}")
        logger.error("   Ensure all dependencies are installed: pip install -r requirements.txt")
        return 1
    
    # Process the file
    logger.info(f"Processing: {args.pdf_path}")
    logger.info(f"Document type: {args.doc_type}")
    logger.info(f"Period: {args.period}")
    
    if os.getenv("LANGSMITH_API_KEY"):
        project = os.getenv("LANGSMITH_PROJECT", "default")
        logger.info(f"Tracing to LangSmith project: {project}")
    
    try:
        # Prompts are loaded from LangSmith Hub (fail-fast if unavailable)
        result = spread_financials(
            file_path=str(pdf_path),
            doc_type=args.doc_type,
            period=args.period,
            model_override=args.model,
            max_pages=args.max_pages,
            dpi=args.dpi
        )
    except FileNotFoundError as e:
        logger.error(f"[ERROR] File not found: {e}")
        return 1
    except ValueError as e:
        logger.error(f"[ERROR] Validation error: {e}")
        return 1
    except Exception as e:
        logger.error(f"[ERROR] Processing failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    # Convert result to JSON
    json_kwargs = {"indent": 2} if args.pretty else {}
    json_output = json.dumps(result.model_dump(), **json_kwargs)
    
    # Output result
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(json_output)
        logger.info(f"Results written to: {args.output}")
    else:
        print(json_output)
    
    logger.info("Processing complete!")
    
    # Show LangSmith link
    if os.getenv("LANGSMITH_API_KEY"):
        project = os.getenv("LANGSMITH_PROJECT", "default")
        logger.info(f"View trace at: https://smith.langchain.com/projects/{project}")
    
    return 0


def run_interactive_mode():
    """Interactive mode for development and testing."""
    logger = logging.getLogger(__name__)
    setup_logging(verbose=True)
    
    if not validate_environment():
        return
    
    print_langsmith_info()
    
    print("\n" + "="*60)
    print("Financial Statement Spreader - Interactive Mode")
    print("="*60)
    print("\nCommands:")
    print("  spread <pdf_path> <income|balance> [period]")
    print("  config                    - Show current configuration")
    print("  quit                      - Exit")
    print()
    
    from spreader import spread_financials
    
    while True:
        try:
            user_input = input("spreader> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        
        if not user_input:
            continue
        
        parts = user_input.split()
        cmd = parts[0].lower()
        
        if cmd == "quit" or cmd == "exit":
            print("Goodbye!")
            break
        
        elif cmd == "config":
            print_langsmith_info()
        
        elif cmd == "spread":
            if len(parts) < 3:
                print("Usage: spread <file_path> <income|balance> [period]")
                continue
            
            file_path = parts[1]
            doc_type = parts[2]
            period = parts[3] if len(parts) > 3 else "Latest"
            
            try:
                result = spread_financials(file_path, doc_type, period)
                print(json.dumps(result.model_dump(), indent=2))
            except Exception as e:
                print(f"Error: {e}")
        
        else:
            print(f"Unknown command: {cmd}")
            print("Use 'spread', 'config', or 'quit'")


if __name__ == "__main__":
    if "--interactive" in sys.argv or "-i" in sys.argv:
        sys.argv = [a for a in sys.argv if a not in ("--interactive", "-i")]
        run_interactive_mode()
    else:
        sys.exit(main())
