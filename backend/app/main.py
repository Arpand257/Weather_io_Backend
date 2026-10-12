import sys
import os

# Ensure backend root is in sys.path so 'from app import ...' works from any directory
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from app import database
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SmartWeatherDash API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SensorData(BaseModel):
    temperature: float
    humidity: float
    pressure: float
    air_quality: float
    sunlight: str = None
    rain: str = None
    device_time: str = None

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/api/ingest")
async def ingest_data(data: SensorData, db: Session = Depends(database.get_db)):
    database.insert_reading(db, data.model_dump())
    return {"status": "success", "recorded": True}

@app.get("/api/weather/current")
async def get_current_weather(db: Session = Depends(database.get_db)):
    latest = database.get_latest_reading(db)
    if not latest:
        raise HTTPException(status_code=404, detail="No weather data found")
    return latest

@app.get("/api/weather/history")
async def get_weather_history(limit: int = 24, db: Session = Depends(database.get_db)):
    history = database.get_history(db, limit)
    return history

from app.ml_model import predictor

@app.get("/api/weather/predict")
async def predict_weather(db: Session = Depends(database.get_db)):
    latest = database.get_latest_reading(db)
    if latest:
        recent_data = {
            "temperature": latest.temperature if latest.temperature is not None else 25.0,
            "humidity": latest.humidity if latest.humidity is not None else 60.0,
            "pressure": latest.pressure if (latest.pressure is not None and latest.pressure > 500) else 1013.25,
            "air_quality": latest.air_quality if latest.air_quality is not None else 45.0
        }
        based_on_live = True
    else:
        # Default baseline if no sensor readings have been ingested yet
        recent_data = {
            "temperature": 25.0,
            "humidity": 60.0,
            "pressure": 1013.25,
            "air_quality": 45.0
        }
        based_on_live = False

    prediction = predictor.predict(recent_data)
    if isinstance(prediction, dict):
        prediction["based_on_live_data"] = based_on_live
    return prediction

from app.analytics import calculate_weather_score, calculate_device_health, detect_anomalies
from datetime import datetime, timezone
from fastapi import Body

def _resolve_score(payload: dict, db: Session):
    if payload and any(payload.values()):
        score_data = payload
    else:
        latest = database.get_latest_reading(db)
        if latest:
            score_data = {
                "temperature": latest.temperature,
                "humidity": latest.humidity,
                "air_quality": latest.air_quality,
                "pressure": latest.pressure,
                "rain": latest.rain,
                "sunlight": latest.sunlight,
            }
        else:
            score_data = {
                "temperature": 25.0,
                "humidity": 60.0,
                "air_quality": 45.0,
                "pressure": 1013.25,
            }
    return calculate_weather_score(score_data)

@app.get("/api/analytics/score")
@app.get("/api/v1/analytics/score")
async def get_weather_score_get(db: Session = Depends(database.get_db)):
    return _resolve_score(None, db)

@app.post("/api/analytics/score")
@app.post("/api/v1/analytics/score")
async def get_weather_score_post(payload: dict = Body(default=None), db: Session = Depends(database.get_db)):
    return _resolve_score(payload, db)

@app.get("/api/iot/health")
@app.get("/api/v1/iot/health")
async def get_device_health_endpoint(db: Session = Depends(database.get_db)):
    latest = database.get_latest_reading(db)
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    count_today = database.get_readings_count_since(db, today_start)
    first_reading = database.get_first_reading(db)
    return calculate_device_health(latest, count_today, first_reading)

def _resolve_anomalies(payload: dict, db: Session):
    history_data = []
    current_data = {}
    if payload and ("history" in payload or "current" in payload):
        history_data = payload.get("history", [])
        current_data = payload.get("current", {})

    if not history_data or not current_data:
        latest = database.get_latest_reading(db)
        readings = database.get_history(db, limit=24)
        if latest:
            current_data = {
                "temperature": latest.temperature,
                "humidity": latest.humidity,
                "air_quality": latest.air_quality,
                "pressure": latest.pressure,
            }
        if readings:
            history_data = [
                {
                    "temperature": r.temperature,
                    "humidity": r.humidity,
                    "air_quality": r.air_quality,
                    "pressure": r.pressure,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                }
                for r in reversed(readings)
            ]
    return detect_anomalies(history_data, current_data)

@app.get("/api/analytics/anomalies")
@app.get("/api/v1/analytics/anomalies")
async def get_anomalies_get(db: Session = Depends(database.get_db)):
    return _resolve_anomalies(None, db)

@app.post("/api/analytics/anomalies")
@app.post("/api/v1/analytics/anomalies")
async def get_anomalies_post(payload: dict = Body(default=None), db: Session = Depends(database.get_db)):
    return _resolve_anomalies(payload, db)

from fastapi.staticfiles import StaticFiles
import os

# Get path to weather-io folder (two directories up from app, then into weather-io)
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "weather-io")

app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True, app_dir=backend_dir)
