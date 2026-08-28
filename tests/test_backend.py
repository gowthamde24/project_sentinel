import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import SensorData
from backend import generator
from datetime import datetime, timezone

client = TestClient(app)

@pytest.fixture(autouse=True)
def mock_telemetry():
    generator.latest_telemetry = SensorData(
        timestamp=datetime.now(timezone.utc),
        hardware={"cpu_percent": 45.0, "ram_percent": 60.0, "power_draw_w": 120.0},
        imu={"x": 0.0, "y": 0.0, "z": 9.8, "roll": 0.0, "pitch": 0.0, "yaw": 0.0},
        drift={"drift_x": 0.1, "drift_y": 0.1, "drift_z": 0.0, "cumulative_drift": 0.2},
        slam_failure=False
    )
    generator.telemetry_history = [generator.latest_telemetry]

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_get_current_telemetry():
    response = client.get("/telemetry/current")
    assert response.status_code == 200
    data = response.json()
    assert "hardware" in data
    assert data["hardware"]["cpu_percent"] == 45.0

def test_get_telemetry_history():
    response = client.get("/telemetry/history?limit=1")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["hardware"]["power_draw_w"] == 120.0

