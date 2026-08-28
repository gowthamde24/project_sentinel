from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import asyncio
from backend import generator
from backend.models import SensorData
from backend.logger import get_logger

logger = get_logger("fastapi_app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start background task
    task = asyncio.create_task(generator.generate_telemetry())
    yield
    # Cancel task on shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("Shutdown complete.")

app = FastAPI(title="Project Sentinel Backend", version="1.0.0", lifespan=lifespan)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/telemetry/current", response_model=SensorData)
async def get_current_telemetry():
    if not generator.latest_telemetry:
        raise HTTPException(status_code=404, detail="Telemetry data not available yet")
    return generator.latest_telemetry

@app.get("/telemetry/history", response_model=list[SensorData])
async def get_telemetry_history(limit: int = 10):
    if not generator.telemetry_history:
        return []
    return generator.telemetry_history[-limit:]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
