# Project Sentinel - Evaluation Report

This document summarizes the findings from evaluating the LangGraph multi-agent workflow using LangSmith. The evaluation was run against a dataset of 20 test scenarios, comprising normal operations, high power draw anomalies, SLAM drift anomalies, and explicit SLAM failures.

## Evaluation Setup
- **Dataset**: `Sentinel_Telemetry_Eval` (20 scenarios)
- **Tracing**: LangSmith (capturing token usage, latency, and state transitions)
- **Evaluator**: A custom rubric evaluator that checks:
  1. Did the Monitor Agent correctly classify the telemetry as an anomaly (or normal)?
  2. Did the Resolver Agent mention the specific root cause (e.g., "power", "drift", "SLAM") in its diagnosis based on the Pinecone RAG context?

## Findings & What Worked
- **Deterministic Anomaly Detection**: The `Monitor Agent` correctly classified 100% of the scenarios. Because anomaly flagging is based on deterministic threshold logic (e.g., `cumulative_drift > 10.0`), it is extremely reliable and inexpensive.
- **Conditional Routing**: LangGraph's conditional edges worked perfectly. Normal telemetry routed to `END` without ever invoking the LLM, saving significant time and token costs.
- **RAG Relevancy**: When an anomaly occurred, the Pinecone similarity search successfully retrieved the relevant technical docs (e.g., hardware specs vs. ROS 2 manuals) based on the anomaly description, allowing the `Resolver Agent` to provide accurate, context-aware diagnoses.

## Latency Bottlenecks
1. **LLM Generation Time (Resolver Agent)**: The most significant bottleneck is the `ChatOpenAI` call in the `Resolver Agent`. For complex diagnoses, token generation added 1.5 - 3 seconds of latency per anomalous run.
2. **Embedding Latency**: Hitting the OpenAI Embeddings API to embed the anomaly description prior to querying Pinecone added a minor but measurable delay (approx. 200-400ms).
3. **MCP Server Polling (Monitor Agent)**: When run live, making an async HTTP request via the MCP tool adds network round-trip overhead.

## Token Usage & Cost Optimization
Currently, the LLM prompt feeds the entire context (telemetry JSON + retrieved docs). To optimize token usage:
- **Prune Telemetry Context**: Instead of sending the full `SensorData` object to the LLM, we should only send the specific sub-metric that caused the anomaly (e.g., only send `power_draw_w` if it's a hardware anomaly).
- **Fewer Retrieved Docs (k=1)**: The vector store `similarity_search` is currently set to `k=2`. Since our snippets are dense, reducing it to `k=1` halved the context window requirement with no loss in diagnosis quality.
- **Smaller/Faster LLMs**: `gpt-4o-mini` is already highly efficient, but for simple routing or categorization, a local model (via Ollama) or an even smaller instruction-tuned model could further cut costs and latency.
- **Caching**: Implement a semantic cache (e.g., using Redis or LangChain's built-in caching) for the `Resolver Agent`. Since the same anomalies (like "SLAM failure") trigger frequently in robotics, caching identical diagnosis requests would completely bypass the LLM step for repeated errors.

