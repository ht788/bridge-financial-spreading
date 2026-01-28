# Financial Statement Spreader

A production-grade Python application for "spreading" financial statements—converting PDF documents into a standardized Chart of Accounts using vision-capable LLMs.

**Now with full LangSmith integration for automatic tracing of all LLM calls.**

## 🎯 What is Financial Spreading?

Financial spreading is the process of taking raw financial statements (income statements, balance sheets) and mapping them to a standardized chart of accounts. This enables:
- **Comparability**: Compare financials across companies with different naming conventions
- **Analysis**: Run consistent financial ratios and metrics
- **Automation**: Feed structured data into downstream systems

## 🏗️ Architecture (LangSmith-Native)

This application follows an **LLMOps-native** design pattern with **full LangSmith integration**:

```
┌─────────────────────────────────────────────────────────────────┐
│                        LangSmith Hub                             │
│  ┌─────────────────┐  ┌─────────────────┐                       │
│  │ income-statement │  │ balance-sheet   │  ← Prompts managed   │
│  │     prompt       │  │    prompt       │    remotely           │
│  └────────┬────────┘  └────────┬────────┘                       │
└───────────┼────────────────────┼────────────────────────────────┘
            │                    │
            │    hub.pull()      │
            ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Python Application                           │
│                     (All functions @traceable)                   │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐     │
│  │  main.py │ → │spreader.py│ → │ utils.py │   │ models.py│     │
│  │   CLI    │   │  Engine  │   │ Helpers  │   │ Schemas  │     │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘     │
│                       │                             │           │
│                       │ .with_structured_output()   │           │
│                       └─────────────────────────────┘           │
│                                                                  │
│                    ALL CALLS AUTO-TRACED ↓                      │
└─────────────────────────────────────────────────────────────────┘
            │
            │  Automatic Tracing (tokens, latency, cost)
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangSmith Dashboard                           │
│         (Full visibility: tokens, cost, latency, errors)        │
│         https://smith.langchain.com                              │
└─────────────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Hub-Controlled Configuration**: Model name, parameters (`reasoning_effort`), and prompts are configured in LangSmith Hub UI—change models without code deploys.

2. **Automatic LangSmith Tracing**: Set `LANGSMITH_API_KEY` and all LLM calls are traced automatically—no code changes needed.

3. **@traceable Decorators**: All significant functions use `@traceable` for visibility into preprocessing, prompt loading, and LLM invocation.

4. **Vision-First Processing**: PDFs are converted to images because financial statement layout carries semantic meaning.

5. **Strict Schema Enforcement**: Output is validated against Pydantic schemas using `.with_structured_output()`.

## 📁 File Structure

```
financial-spreader/
├── main.py           # CLI entry point (LangSmith-aware)
├── spreader.py       # Core spreading logic (@traceable functions)
├── utils.py          # PDF/Excel processing (@traceable)
├── models.py         # Pydantic schemas
├── requirements.txt  # Python dependencies (includes langsmith)
├── env.example       # Environment variable template
├── .gitignore        # Git ignore rules
└── README.md         # This file
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- Poppler (for PDF processing)
  - **Windows**: Download from [poppler-windows](https://github.com/osmar81.de/poppler-windows/releases)
  - **macOS**: `brew install poppler`
  - **Linux**: `apt-get install poppler-utils`

### 2. Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd financial-spreader

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file with your API keys:

```bash
# Copy the example environment file
cp env.example .env
```

Then edit `.env`:

```env
# REQUIRED: OpenAI API Key
OPENAI_API_KEY=sk-your-openai-api-key-here

# REQUIRED FOR TRACING: LangSmith API Key
LANGSMITH_API_KEY=lsv2_pt_your-langsmith-api-key-here
LANGSMITH_PROJECT=financial-spreader-v1
```

### 4. Get Your LangSmith API Key

1. Go to [smith.langchain.com](https://smith.langchain.com)
2. Create an account (free tier available)
3. Navigate to **Settings → API Keys**
4. Click **Create API Key**
5. Copy the key (starts with `lsv2_pt_`)

### 5. Run

```bash
# Basic usage (all calls automatically traced)
python main.py financial_statement.pdf income --period "FY2024"

# With options
python main.py balance_sheet.pdf balance \
  --period "Q4 2024" \
  --output results.json \
  --pretty \
  --verbose

# Show LangSmith configuration
python main.py document.pdf income --show-config
```

## 🔍 LangSmith Tracing

### What Gets Traced Automatically

When `LANGSMITH_API_KEY` is set, you'll see in LangSmith:

```
┌────────────────────────────────────────────────────────────────┐
│ spread_pdf                                     │ 12.3s │ ✓    │
│ ├── convert_pdf_to_images                      │  2.1s │ ✓    │
│ │   └── pdf_to_base64_images                   │  2.0s │ ✓    │
│ ├── load_prompt_from_hub                       │  0.3s │ ✓    │
│ └── invoke_llm_for_spreading                   │  9.8s │ ✓    │
│     └── ChatOpenAI                             │  9.5s │ ✓    │
│         Input: 3,485 tokens │ Output: 1,200 tokens            │
│         Cost: $0.047                                          │
└────────────────────────────────────────────────────────────────┘
```

### Trace Details

Each trace shows:
- **Latency breakdown**: Time spent in each step
- **Token usage**: Input and output tokens per LLM call
- **Cost estimate**: Approximate $ cost per operation
- **Inputs/Outputs**: Full data for debugging
- **Errors**: Stack traces with full context
- **Tags**: Filter by `financial-spreading`, `pdf`, `vision`, etc.

### View Your Traces

After running any command:
```bash
python main.py document.pdf income --period "FY2024"
```

Go to: **https://smith.langchain.com/projects/financial-spreader-v1**

## 📋 CLI Reference

```
usage: financial-spreader [-h] [--period PERIOD] [--output OUTPUT] 
                          [--model MODEL] [--max-pages MAX_PAGES] 
                          [--dpi DPI] [--fallback-prompt] [--verbose] 
                          [--pretty] [--show-config]
                          pdf_path {income,balance}

positional arguments:
  pdf_path              Path to the PDF financial statement
  {income,balance}      Type of financial statement to extract

optional arguments:
  -h, --help            Show help message
  --period, -p PERIOD   Fiscal period to extract (default: 'Latest')
  --output, -o OUTPUT   Output file path (default: stdout)
  --model, -m MODEL     Override model (default: gpt-5.2)
  --max-pages MAX_PAGES Maximum pages to process
  --dpi DPI             DPI for PDF conversion (default: 200)
  --fallback-prompt     Use local fallback prompt
  --verbose, -v         Enable verbose logging
  --pretty              Pretty-print JSON output
  --show-config         Show LangSmith configuration
```

## ⚙️ Configuration

### Model Configuration Hierarchy

The model is determined in this priority order:

| Priority | Source | Use Case |
|----------|--------|----------|
| 1 | `--model` CLI flag | Testing/debugging |
| 2 | **LangSmith Hub** | ✅ Production (recommended) |
| 3 | `OPENAI_MODEL` env var | Fallback |
| 4 | Code default (`gpt-4o`) | Last resort |

**For production**: Configure the model in LangSmith Hub UI, not in code or `.env`.

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ Yes | OpenAI API key for LLM calls |
| `LANGSMITH_API_KEY` | ✅ Yes | LangSmith API key for tracing + Hub |
| `LANGSMITH_PROJECT` | Recommended | Project name (default: "default") |
| `OPENAI_MODEL` | No | Fallback model (Hub config takes priority) |
| `OPENAI_REASONING_EFFORT` | No | Fallback reasoning effort (Hub config takes priority) |

## 📊 Output Schema

### Income Statement

```json
{
  "revenue": {"value": 1000000, "confidence": 0.95, "raw_fields_used": ["Total Revenue"], "source_section_hint": null},
  "cogs": {"value": 400000, "confidence": 0.92, "raw_fields_used": ["Cost of Goods Sold"], "source_section_hint": null},
  "gross_profit": {"value": 600000, "confidence": 0.90, "raw_fields_used": ["Gross Profit"], "source_section_hint": null},
  "net_income": {"value": 280000, "confidence": 0.95, "raw_fields_used": ["Net Income"], "source_section_hint": null},
  "fiscal_period": "FY2024",
  "currency": "USD",
  "scale": "units"
}
```

## 🔧 Development

### Using Fallback Prompts (No Hub Required)

For development without LangSmith Hub prompts:

```bash
python main.py document.pdf income --fallback-prompt
```

### Interactive Mode

```bash
python main.py --interactive
```

## 📈 Performance & Cost

- **DPI**: Higher DPI (300+) improves accuracy but increases token usage
- **Token Estimates**: ~3,500 tokens per page at 200 DPI
- **Cost**: Varies by model; GPT-5.2 with extended thinking uses more tokens

View exact costs in LangSmith dashboard for each run.

## 🛡️ Security

- Never commit `.env` files with real API keys
- Use environment variables in production
- LangSmith traces may contain sensitive financial data—configure access controls

## 📜 License

[Your License Here]
