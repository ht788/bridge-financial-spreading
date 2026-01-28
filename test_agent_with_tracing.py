"""
Test agent with tracing - following LangSmith documentation exactly.
This creates an agent with a simple tool and invokes it.
"""
import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

print("=" * 60)
print("Testing LangSmith Agent Tracing")
print("=" * 60)
print(f"LANGSMITH_TRACING: {os.getenv('LANGSMITH_TRACING')}")
print(f"LANGSMITH_ENDPOINT: {os.getenv('LANGSMITH_ENDPOINT')}")
print(f"LANGSMITH_API_KEY: {os.getenv('LANGSMITH_API_KEY')[:20]}...")
print(f"LANGSMITH_PROJECT: {os.getenv('LANGSMITH_PROJECT')}")
print("=" * 60)

from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate

# Define a simple tool (like the get_weather example)
@tool
def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

# Create the model
model = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Create a simple prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant"),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

# Create the agent
print("\nCreating agent with tools...")
agent = create_tool_calling_agent(model, [get_weather], prompt)

# Create agent executor
agent_executor = AgentExecutor(agent=agent, tools=[get_weather], verbose=True)

# Run the agent
print("\nInvoking agent...")
print("Question: What is the weather in San Francisco?")
print("-" * 60)

result = agent_executor.invoke({
    "input": "What is the weather in San Francisco?"
})

print("-" * 60)
print(f"\nAgent Response: {result['output']}")

print("\n" + "=" * 60)
print("SUCCESS! Agent executed with tracing enabled.")
print("Check your traces at:")
print(f"https://smith.langchain.com/o/default/projects/p/{os.getenv('LANGSMITH_PROJECT')}")
print("=" * 60)
