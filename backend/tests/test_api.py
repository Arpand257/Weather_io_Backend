from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path to import main
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_ingest_data():
    payload = {
        "temperature": 25.5,
        "humidity": 60.0,
        "pressure": 1012.0,
        "air_quality": 45.0
    }
    response = client.post("/api/ingest", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "success", "recorded": True}

def test_get_current_weather():
    response = client.get("/api/weather/current")
    assert response.status_code == 200
    data = response.json()
    assert "temperature" in data
    assert "humidity" in data

def test_get_weather_history():
    response = client.get("/api/weather/history?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0

def test_predict_weather():
    response = client.get("/api/weather/predict")
    assert response.status_code == 200
    data = response.json()
    assert "rain_tomorrow" in data
    assert "predicted_max_temp" in data
    assert "sun_azimuth" in data
    assert "sun_elevation" in data
    assert "based_on_live_data" in data

def test_weather_score_get():
    response = client.get("/api/analytics/score")
    assert response.status_code == 200
    data = response.json()
    assert "score" in data
    assert "label" in data
    assert "factors" in data
    assert "explanation" in data

def test_weather_score_post():
    payload = {
        "temperature": 24.0,
        "humidity": 50.0,
        "air_quality": 35.0,
        "uvIndex": 2.0,
        "pressure": 1014.0,
        "windSpeed": 8.0,
        "rainProbability": 0.0
    }
    response = client.post("/api/analytics/score", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["score"] >= 80
    assert data["label"] in ["Excellent", "Very Comfortable"]

def test_device_health():
    response = client.get("/api/iot/health")
    assert response.status_code == 200
    data = response.json()
    assert "device" in data
    assert "sensors" in data
    assert data["device"]["id"] == "ESP8266-WX-001"
    assert len(data["sensors"]) >= 4

def test_anomalies_get():
    response = client.get("/api/analytics/anomalies")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_anomalies_post_detection():
    payload = {
        "history": [
            {"temperature": 22.0, "air_quality": 40.0, "pressure": 1013.0},
            {"temperature": 22.5, "air_quality": 42.0, "pressure": 1013.5},
            {"temperature": 23.0, "air_quality": 41.0, "pressure": 1013.0},
        ],
        "current": {
            "temperature": 45.0,  # Extreme temp spike anomaly
            "air_quality": 42.0,
            "pressure": 1013.0
        }
    }
    response = client.post("/api/analytics/anomalies", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["type"] == "temperature"
