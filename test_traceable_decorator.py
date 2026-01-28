"""
Test agent with @traceable decorator - following LangSmith documentation exactly.
This is the pattern shown in the screenshot instructions.
"""
import os
from dotenv import load_dotenv

# Load environment variables FIRST (before any langchain imports)
load_dotenv()

print("=" * 60)
print("Testing LangSmith @traceable Decorator")
print("=" * 60)
print(f"LANGSMITH_TRACING: {os.getenv('LANGSMITH_TRACING')}")
print(f"LANGSMITH_ENDPOINT: {os.getenv('LANGSMITH_ENDPOINT')}")
print(f"LANGSMITH_API_KEY: {os.getenv('LANGSMITH_API_KEY')[:20]}...")
print(f"LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT')}")
print("=" * 60)

from langsmith import traceable
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# Define a simple function with @traceable
@traceable
def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

# Define a traced agent function
@traceable(name="weather_agent")
def run_weather_agent(question: str) -> str:
    """Simple agent that answers weather questions."""
    
    # Create model
    model = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    # Check if question is about weather
    if "weather" in question.lower():
        # Extract city from question
        city = "San Francisco"  # Simple extraction for demo
        if "San Francisco" in question:
            city = "San Francisco"
        
        # Call our tool
        weather_info = get_weather(city)
        
        # Have model format response
        messages = [
            SystemMessage(content="You are a helpful assistant that provides weather information."),
            HumanMessage(content=f"The weather data says: {weather_info}. Please respond to the user's question: {question}")
        ]
        
        response = model.invoke(messages)
        return response.content
    else:
        # Just use model directly
        response = model.invoke([HumanMessage(content=question)])
        return response.content

# Run the agent
print("\nRunning weather agent...")
print("Question: What is the weather in San Francisco?")
print("-" * 60)

result = run_weather_agent("What is the weather in San Francisco?")

print("-" * 60)
print(f"\nAgent Response: {result}")

print("\n" + "=" * 60)
print("SUCCESS! Agent executed with @traceable decorator.")
print("Check your traces at:")
print(f"https://smith.langchain.com/o/default/projects/p/{os.getenv('LANGSMITH_PROJECT')}")
print("Or directly at: https://smith.langchain.com")
print("=" * 60)
