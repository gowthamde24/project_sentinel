# Project Sentinel

Project Sentinel is a spatial/telemetry monitoring system for autonomous systems, demonstrating an enterprise AI stack (FastAPI, MCP, LangGraph, Vector DBs, LangSmith).

This project is built incrementally in 4 phases.

## Phase 1: Backend Core

The Backend Core is a FastAPI application that simulates hardware telemetry and perception/spatial data (IMU coordinates, drift, SLAM failures) in a continuous background task without blocking the main API thread.

### Setup and Running

1. Activate the virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Install dependencies (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

3. Run the FastAPI application:
   ```bash
   PYTHONPATH=. uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

### Testing the Endpoints (curl)

Once the server is running, you can test the endpoints in another terminal:

**1. Health Check:**
```bash
curl http://localhost:8000/health
```

**2. Get Current Telemetry:**
```bash
curl http://localhost:8000/telemetry/current
```

**3. Get Telemetry History:**
```bash
curl "http://localhost:8000/telemetry/history?limit=5"
```

### Running Unit Tests

To run the test suite:
```bash
PYTHONPATH=. pytest tests/
```


## Phase 2: MCP Server

The MCP (Model Context Protocol) Server exposes two tools that agents can use to inspect the Sentinel system:
1. `get_current_telemetry`: Fetches live data from the FastAPI backend.
2. `query_system_logs`: Reads the local system log file and returns matching entries.

### Testing the MCP Server

You can run the MCP client test script to verify that the tools work correctly. The test script will start a session with the MCP server and call both tools.

1. Ensure you are in the project root and virtual environment is active.
2. Run the test script:
   ```bash
   PYTHONPATH=. python3 tests/test_mcp_client.py
   ```

*(Note: If the FastAPI backend from Phase 1 is not running, `get_current_telemetry` will gracefully return a connection error. Start the backend in another terminal to see live telemetry data.)*

## Phase 3: Multi-Agent Workflow (LangGraph)

The LangGraph workflow implements a two-agent system for monitoring telemetry and diagnosing issues via RAG.
- **Monitor Agent**: Connects to the MCP server, fetches telemetry, and evaluates it for anomalies (e.g., SLAM failure or high power draw).
- **Resolver Agent**: If an anomaly is detected, queries a Pinecone Vector DB using HuggingFace embeddings for relevant technical documentation, and uses a HuggingFace-hosted LLM (Qwen2.5-72B-Instruct) to produce a diagnosis and recommended action.

### Setup and Running

To run Phase 3, you must configure your HuggingFace Hub API Token and Pinecone API Key.

1. Ensure the `.env` file (or your terminal environment) contains:
   ```bash
   export HUGGINGFACEHUB_API_TOKEN="your-huggingface-token"
   export PINECONE_API_KEY="your-pinecone-key"
   ```

2. Run the ingestion script to create the Pinecone index (`sentinel-docs`) and embed the sample technical documents:
   ```bash
   PYTHONPATH=. python3 agents/ingest.py
   ```

3. Run the LangGraph workflow:
   ```bash
   PYTHONPATH=. python3 agents/workflow.py
   ```

*(Note: Ensure your FastAPI backend from Phase 1 is running for the Monitor Agent to receive healthy telemetry; if it isn't running, the Monitor Agent will flag a connection anomaly and still route to the Resolver Agent.)*

## Phase 4: Evaluation (LangSmith)

The LangSmith integration provides observability and evaluation for the LangGraph workflow. It evaluates 20 simulated test scenarios to check anomaly detection accuracy and the relevancy of the LLM's diagnosis.

### Setup and Running

1. Ensure your LangSmith API key is in the `.env` file:
   ```bash
   export LANGCHAIN_API_KEY="your-langsmith-key"
   export LANGCHAIN_TRACING_V2=true
   export LANGCHAIN_PROJECT="project_sentinel"
   ```

2. Run the evaluation script:
   ```bash
   PYTHONPATH=. python3 eval/run_eval.py
   ```

3. Open the [LangSmith UI](https://smith.langchain.com/) to view the trace outputs, token usage, latency, and evaluator scores.
4. Read `EVALUATION.md` for a summary of architectural findings and optimization ideas.
