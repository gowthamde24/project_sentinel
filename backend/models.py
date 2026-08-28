from pydantic import BaseModel, Field
from datetime import datetime

class HardwareTelemetry(BaseModel):
    cpu_percent: float = Field(..., ge=0.0, le=100.0, description="CPU usage percentage")
    ram_percent: float = Field(..., ge=0.0, le=100.0, description="RAM usage percentage")
    power_draw_w: float = Field(..., ge=0.0, description="Power draw in watts")

class IMUCoordinates(BaseModel):
    x: float = Field(..., description="X-axis linear acceleration")
    y: float = Field(..., description="Y-axis linear acceleration")
    z: float = Field(..., description="Z-axis linear acceleration")
    roll: float = Field(..., description="Roll orientation")
    pitch: float = Field(..., description="Pitch orientation")
    yaw: float = Field(..., description="Yaw orientation")

class DriftMetric(BaseModel):
    drift_x: float = Field(..., description="Drift in X axis")
    drift_y: float = Field(..., description="Drift in Y axis")
    drift_z: float = Field(..., description="Drift in Z axis")
    cumulative_drift: float = Field(..., description="Total cumulative drift")

class SensorData(BaseModel):
    timestamp: datetime = Field(..., description="Time of measurement")
    hardware: HardwareTelemetry
    imu: IMUCoordinates
    drift: DriftMetric
    slam_failure: bool = Field(default=False, description="Flag indicating if SLAM failed")

