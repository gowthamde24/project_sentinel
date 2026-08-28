import asyncio
import os
import uuid
from dotenv import load_dotenv
load_dotenv()
from typing import Any, Dict
from langsmith import Client, evaluate
from langsmith.evaluation import EvaluationResult
from langgraph.graph import StateGraph

# Import the workflow components
import agents.workflow as workflow_module
from agents.workflow import app, SentinelState

client = Client()

DATASET_NAME = f"Sentinel_Telemetry_Eval_{uuid.uuid4().hex[:6]}"

def create_dataset():
    """Creates a dataset of 20 telemetry scenarios in LangSmith."""
    dataset = client.create_dataset(
        dataset_name=DATASET_NAME,
        description="Evaluation dataset for Project Sentinel containing normal and anomalous telemetry."
    )
    
    scenarios = []
    # 5 Normal Scenarios
    for i in range(5):
        scenarios.append(
            {"telemetry": {"hardware": {"power_draw_w": 100 + i}, "drift": {"cumulative_drift": 1.0 + i}, "slam_failure": False}, "expected_anomaly": False}
        )
    # 5 High Power Scenarios
    for i in range(5):
        scenarios.append(
            {"telemetry": {"hardware": {"power_draw_w": 260 + i}, "drift": {"cumulative_drift": 1.0}, "slam_failure": False}, "expected_anomaly": True, "expected_topic": "power"}
        )
    # 5 High Drift Scenarios
    for i in range(5):
        scenarios.append(
            {"telemetry": {"hardware": {"power_draw_w": 100}, "drift": {"cumulative_drift": 11.0 + i}, "slam_failure": False}, "expected_anomaly": True, "expected_topic": "drift"}
        )
    # 5 SLAM Failure Scenarios
    for i in range(5):
        scenarios.append(
            {"telemetry": {"hardware": {"power_draw_w": 100}, "drift": {"cumulative_drift": 5.0}, "slam_failure": True}, "expected_anomaly": True, "expected_topic": "SLAM"}
        )

    for s in scenarios:
        client.create_example(
            inputs={"telemetry": s["telemetry"]},
            outputs={"expected_anomaly": s["expected_anomaly"], "expected_topic": s.get("expected_topic", "")},
            dataset_id=dataset.id,
        )
    
    return dataset

# Mock the MCP call to return the telemetry from inputs
async def mock_get_mcp_telemetry(script_path: str):
    # This will be dynamically overridden per invocation
    pass

def predict(inputs: dict) -> dict:
    """Wrapper function to invoke the LangGraph workflow."""
    # We patch the mcp function just for this run to return the input telemetry
    async def _mock_telemetry(script_path: str):
        return inputs["telemetry"]
    
    workflow_module.get_mcp_telemetry = _mock_telemetry
    
    initial_state = SentinelState(mcp_server_script="mocked")
    # Run sync since LangSmith predict expects sync for standard eval, though async is supported via ainvoke
    final_state = asyncio.run(app.ainvoke(initial_state))
    
    return {
        "is_anomaly": final_state["anomaly"].is_anomaly,
        "diagnosis": final_state.get("diagnosis", "")
    }

def rubric_evaluator(run: Any, example: Any) -> EvaluationResult:
    """Simple rubric-based scoring to check if diagnosis makes sense and anomaly detection matches."""
    outputs = run.outputs
    reference = example.outputs
    
    score = 1.0
    
    # 1. Did it correctly identify anomaly state?
    if outputs["is_anomaly"] != reference["expected_anomaly"]:
        return EvaluationResult(key="correctness", score=0.0, comment="Failed to identify anomaly state correctly.")
    
    # 2. If it was an anomaly, did the diagnosis mention the right topic?
    if reference["expected_anomaly"]:
        diagnosis = outputs.get("diagnosis", "").lower()
        topic = reference["expected_topic"].lower()
        if topic not in diagnosis:
            score = 0.5 # Partial credit if it flagged it but missed the specific topic
            return EvaluationResult(key="correctness", score=score, comment=f"Diagnosis didn't mention {topic}")
    
    return EvaluationResult(key="correctness", score=score, comment="Passed")

if __name__ == "__main__":
    if "HUGGINGFACEHUB_API_TOKEN" not in os.environ:
        print("Please set HUGGINGFACEHUB_API_TOKEN before running the evaluation.")
    else:
        print("Creating dataset...")
        create_dataset()
        print(f"Dataset {DATASET_NAME} created. Running evaluation...")
        
        evaluate(
            predict,
            data=DATASET_NAME,
            evaluators=[rubric_evaluator],
            experiment_prefix="Sentinel-Eval-",
        )
        print("Evaluation complete. View results in the LangSmith UI.")

