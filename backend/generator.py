import asyncio
import random
from datetime import datetime, timezone
from backend.models import SensorData, HardwareTelemetry, IMUCoordinates, DriftMetric
from backend.logger import get_logger

logger = get_logger("telemetry_generator")

# In-memory queue to store recent telemetry history
MAX_HISTORY = 100
telemetry_history = []
latest_telemetry = None

async def generate_telemetry():
    """Background task to continuously generate telemetry data."""
    global latest_telemetry
    logger.info("Starting telemetry generation background task...")
    
    cumulative_drift = 0.0
    
    while True:
        try:
            # Simulate hardware metrics
            cpu = round(random.uniform(10.0, 95.0), 2)
            ram = round(random.uniform(20.0, 85.0), 2)
            power = round(random.uniform(50.0, 300.0), 2)
            
            # Simulate IMU
            x = round(random.uniform(-1.0, 1.0), 4)
            y = round(random.uniform(-1.0, 1.0), 4)
            z = round(random.uniform(9.0, 10.0), 4) # Gravity
            roll = round(random.uniform(-0.1, 0.1), 4)
            pitch = round(random.uniform(-0.1, 0.1), 4)
            yaw = round(random.uniform(0.0, 360.0), 4)
            
            # Simulate Drift & SLAM failure occasionally
            drift_x = round(random.uniform(0.0, 0.5), 4)
            drift_y = round(random.uniform(0.0, 0.5), 4)
            drift_z = round(random.uniform(0.0, 0.1), 4)
            
            cumulative_drift += (drift_x + drift_y + drift_z)
            slam_failure = cumulative_drift > 10.0
            
            data = SensorData(
                timestamp=datetime.now(timezone.utc),
                hardware=HardwareTelemetry(cpu_percent=cpu, ram_percent=ram, power_draw_w=power),
                imu=IMUCoordinates(x=x, y=y, z=z, roll=roll, pitch=pitch, yaw=yaw),
                drift=DriftMetric(drift_x=drift_x, drift_y=drift_y, drift_z=drift_z, cumulative_drift=cumulative_drift),
                slam_failure=slam_failure
            )
            
            latest_telemetry = data
            telemetry_history.append(data)
            
            if len(telemetry_history) > MAX_HISTORY:
                telemetry_history.pop(0)
                
            # If SLAM failed, we might want to log it or reset drift to simulate recovery
            if slam_failure:
                logger.warning(f"SLAM Failure detected! Cumulative drift: {cumulative_drift:.2f}")
                # Reset after failure to continue simulation
                cumulative_drift = 0.0
                
            await asyncio.sleep(1) # Generate data every second
        except Exception as e:
            logger.error(f"Error in telemetry generator: {e}")
            await asyncio.sleep(1)

