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
async def predict_weather():
    # For now, we'll pass a mock recent reading to get a prediction
    # Later, you can fetch the latest reading from the database here
    recent_data = {
        "temperature": 25.0,
        "humidity": 60.0,
        "pressure": 1012.0,
        "air_quality": 45.0
    }
    prediction = predictor.predict(recent_data)
    return prediction

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
