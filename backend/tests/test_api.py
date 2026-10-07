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
