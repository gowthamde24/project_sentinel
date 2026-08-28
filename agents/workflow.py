import asyncio
import os
import sys
from dotenv import load_dotenv
load_dotenv()
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_pinecone import PineconeVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp.client.session import ClientSession

class Anomaly(BaseModel):
    is_anomaly: bool = Field(default=False)
    description: str = Field(default="")
    context: Dict[str, Any] = Field(default_factory=dict)

class SentinelState(BaseModel):
    telemetry: Optional[Dict[str, Any]] = None
    anomaly: Optional[Anomaly] = None
    diagnosis: Optional[str] = None
    mcp_server_script: str = ""

async def get_mcp_telemetry(script_path: str) -> dict:
    server_params = StdioServerParameters(command=sys.executable, args=[script_path])
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool("get_current_telemetry", {})
            # extract dictionary from result
            # structured_content is the dict if it returned json
            if hasattr(result, "structured_content"):
                return result.structured_content
            # fallback string parsing
            return {"raw": str(result.content)}

async def monitor_agent(state: SentinelState) -> SentinelState:
    print("-> Monitor Agent: Fetching telemetry from MCP server...")
    try:
        telemetry = await get_mcp_telemetry(state.mcp_server_script)
        state.telemetry = telemetry
        
        # Check for anomaly
        is_anomaly = False
        desc = ""
        
        if "error" in telemetry:
            is_anomaly = True
            desc = f"Backend Connection Error: {telemetry['error']}"
        elif "drift" in telemetry:
            drift = telemetry["drift"]
            cum_drift = drift.get("cumulative_drift", 0.0)
            if cum_drift > 10.0 or telemetry.get("slam_failure"):
                is_anomaly = True
                desc = f"High cumulative drift detected: {cum_drift} or SLAM failure flag is true."
            elif telemetry.get("hardware", {}).get("power_draw_w", 0) > 250:
                is_anomaly = True
                desc = "High power draw detected."

        state.anomaly = Anomaly(is_anomaly=is_anomaly, description=desc, context=telemetry)
        if is_anomaly:
            print(f"   [!] Anomaly Flagged: {desc}")
        else:
            print("   [OK] Telemetry looks nominal.")
        return state
    except Exception as e:
        print(f"   [Error] Monitor Agent failed: {e}")
        state.anomaly = Anomaly(is_anomaly=True, description=f"Monitor Agent Error: {e}", context={})
        return state

def should_resolve(state: SentinelState) -> str:
    if state.anomaly and state.anomaly.is_anomaly:
        print("-> Routing to Resolver Agent...")
        return "resolver"
    print("-> No anomaly. Routing to END.")
    return END

async def resolver_agent(state: SentinelState) -> SentinelState:
    print("-> Resolver Agent: Querying Vector DB for diagnosis...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = PineconeVectorStore(index_name="sentinel-docs", embedding=embeddings)
    
    # RAG search based on the anomaly description
    query = state.anomaly.description
    docs = vectorstore.similarity_search(query, k=2)
    doc_context = "\n".join([doc.page_content for doc in docs])
    llm_endpoint = HuggingFaceEndpoint(
        repo_id="Qwen/Qwen2.5-72B-Instruct",
        task="text-generation",
        temperature=0.1
    )
    llm = ChatHuggingFace(llm=llm_endpoint)
    
    prompt = f"""
    You are an AI diagnostic assistant for an autonomous system. 
    An anomaly was detected:
    {state.anomaly.description}
    
    Telemetry Context:
    {state.anomaly.context}
    
    Technical Documentation:
    {doc_context}
    
    Provide a brief diagnosis and a recommended action.
    """
    
    response = await llm.ainvoke(prompt)
    state.diagnosis = response.content
    print(f"   [Diagnosis]: {state.diagnosis}")
    
    return state

# Build the Graph
workflow = StateGraph(SentinelState)
workflow.add_node("monitor", monitor_agent)
workflow.add_node("resolver", resolver_agent)

workflow.set_entry_point("monitor")
workflow.add_conditional_edges("monitor", should_resolve)
workflow.add_edge("resolver", END)

app = workflow.compile()

async def run_workflow():
    script_path = os.path.join(os.path.dirname(__file__), "..", "mcp_server", "server.py")
    initial_state = SentinelState(mcp_server_script=script_path)
    
    print("--- Starting Sentinel Workflow ---")
    final_state = await app.ainvoke(initial_state)
    print("--- Workflow Complete ---")

if __name__ == "__main__":
    if "HUGGINGFACEHUB_API_TOKEN" not in os.environ:
        print("Please set HUGGINGFACEHUB_API_TOKEN before running the workflow.")
    elif "PINECONE_API_KEY" not in os.environ:
        print("Please set PINECONE_API_KEY before running the workflow.")
    else:
        asyncio.run(run_workflow())

