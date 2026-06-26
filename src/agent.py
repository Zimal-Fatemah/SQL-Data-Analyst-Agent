import json
import os
import re
import sys
from typing import List, TypedDict
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from langchain_core.messages import SystemMessage, ToolMessage, AnyMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END

from src.tools import get_database_schema, execute_agent_query

# Load environment configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print(f"\n❌ CONFIGURATION ERROR: GROQ_API_KEY missing from {ENV_PATH}\n")
    sys.exit(1)

# =====================================================================
# 1. THE DATA SANDWICH SCHEMA
# =====================================================================
class AnalystResponse(BaseModel):
    """The triad of BI reporting: The Hook, The Data, and The Strategy."""
    executive_headline: str = Field(
        description="A single, punchy 10-15 word sentence summarizing the most important trend."
    )
    data_table_markdown: str = Field(
        description="A strict, plain Markdown table containing only the raw database results. No prose."
    )
    strategic_takeaways: List[str] = Field(
        description="Exactly two 'So What?' actionable points. Focus on what to do, not just what the data says."
    )
    sql_query_used: str = Field(description="The SQL executed.")

class AgentState(TypedDict):
    messages: List[AnyMessage]
    final_analysis: AnalystResponse | None

# =====================================================================
# 2. TOOLS & ENGINES
# =====================================================================
@tool
def run_sql_query(query: str) -> str:
    """Executes a read-only SQLite query against the Olist e-commerce database."""
    return execute_agent_query(query)

TOOLS_REGISTRY = {run_sql_query.name: run_sql_query}

def get_groq_reasoning_engine():
    return ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=GROQ_API_KEY).bind_tools([run_sql_query])

def get_groq_json_engine():
    return ChatGroq(
        model="llama-3.3-70b-versatile", 
        temperature=0, 
        api_key=GROQ_API_KEY,
        model_kwargs={"response_format": {"type": "json_object"}}
    )

# =====================================================================
# 3. GRAPH NODES
# =====================================================================
def groq_reasoning(state: AgentState):
    messages = state["messages"]
    schema = get_database_schema()
    prompt = SystemMessage(content=f"You are an expert BI agent. Generate a SELECT query using `run_sql_query` based on schema:\n\n{schema}")
    return {"messages": [get_groq_reasoning_engine().invoke([prompt] + messages)]}

def execute_tools(state: AgentState):
    messages = state["messages"]
    last = messages[-1]
    tool_messages = [ToolMessage(content=str(TOOLS_REGISTRY[tc["name"]].invoke(tc["args"])), 
                                 tool_call_id=tc["id"], name=tc["name"]) for tc in last.tool_calls]
    return {"messages": tool_messages}

def groq_synthesis(state: AgentState):
    messages = state["messages"]
    schema_instr = json.dumps(AnalystResponse.model_json_schema(), indent=2)
    prompt = SystemMessage(content=(
        "You are a Senior Data Analyst. Review SQL and tool output.\n"
        "Output ONLY raw JSON with keys: 'executive_headline', 'data_table_markdown', 'strategic_takeaways', 'sql_query_used'.\n"
        f"Strictly follow this schema:\n{schema_instr}"
    ))
    raw = get_groq_json_engine().invoke([prompt] + messages)
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw.content.strip(), flags=re.MULTILINE)
    try:
        return {"final_analysis": AnalystResponse.model_validate(json.loads(cleaned))}
    except (json.JSONDecodeError, ValidationError):
        return {"final_analysis": None}

# =====================================================================
# 4. WORKFLOW & CLI
# =====================================================================
workflow = StateGraph(AgentState)
workflow.add_node("groq_reasoning", groq_reasoning)
workflow.add_node("tools", execute_tools)
workflow.add_node("groq_synthesis", groq_synthesis)

workflow.add_edge(START, "groq_reasoning")
workflow.add_conditional_edges("groq_reasoning", lambda s: "tools" if s["messages"][-1].tool_calls else "groq_synthesis")
workflow.add_edge("tools", "groq_synthesis")
workflow.add_edge("groq_synthesis", END)

agent_app = workflow.compile()

if __name__ == "__main__":
    print(" SQL DATA ANALYST")
    while True:
        u = input("\n👤 User: ")
        if u.lower() in ["exit", "quit"]: break
        if not u.strip(): continue
        
        final = agent_app.invoke({"messages": [("user", u)]})
        res: AnalystResponse = final.get("final_analysis")
        
        if res:
            print(f"\n {res.executive_headline.upper()}\n")
            print(f"{res.data_table_markdown}\n")
            print("📈 STRATEGIC TAKEAWAYS:")
            for i in res.strategic_takeaways: print(f"  • {i}")
            print("-" * 60)