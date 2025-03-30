from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class MotorControl(BaseModel):
    motor1_speed: int
    motor2_speed: int
    action: str

@app.post("/control")
async def control_motors(data: MotorControl):
    print(f"Received Data: {data}")
    print(f"Motor 1 Speed: {data.motor1_speed}, Motor 2 Speed: {data.motor2_speed}")
    return {"status": "Success", "message": "Data received"}

