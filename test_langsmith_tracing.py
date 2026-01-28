"""
Test script to verify LangSmith tracing is working.
This follows the exact setup from LangSmith documentation.
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("LANGSMITH ENVIRONMENT CHECK")
print("=" * 60)

# Check environment variables
env_vars = {
    "LANGSMITH_TRACING": os.getenv("LANGSMITH_TRACING"),
    "LANGCHAIN_TRACING_V2": os.getenv("LANGCHAIN_TRACING_V2"),
    "LANGSMITH_ENDPOINT": os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
    "LANGCHAIN_ENDPOINT": os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com"),
    "LANGSMITH_API_KEY": os.getenv("LANGSMITH_API_KEY", "")[:20] + "..." if os.getenv("LANGSMITH_API_KEY") else "NOT SET",
    "LANGCHAIN_API_KEY": os.getenv("LANGCHAIN_API_KEY", "")[:20] + "..." if os.getenv("LANGCHAIN_API_KEY") else "NOT SET",
    "LANGSMITH_PROJECT": os.getenv("LANGSMITH_PROJECT"),
    "LANGCHAIN_PROJECT": os.getenv("LANGCHAIN_PROJECT"),
    "OPENAI_API_KEY": "SET" if os.getenv("OPENAI_API_KEY") else "NOT SET"
}

for key, value in env_vars.items():
    print(f"  {key:25s} = {value}")

print("=" * 60)

# Now test with a simple LangChain call
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

print("\nCreating test model...")

# Create the model
model = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

print(f"Model created: {model.model_name}")

# Simple invoke test
print("\nInvoking model with a simple message...")
print("This should create a trace in LangSmith...")

response = model.invoke([
    HumanMessage(content="Say 'LangSmith tracing test successful!' and nothing else.")
])

print(f"\nResponse: {response.content}")

print("\n" + "=" * 60)
print("SUCCESS! The model was invoked successfully.")
print("Check LangSmith at: https://smith.langchain.com")
print(f"Project: {os.getenv('LANGSMITH_PROJECT') or os.getenv('LANGCHAIN_PROJECT')}")
print("=" * 60)
