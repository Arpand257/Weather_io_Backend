import joblib
import pandas as pd
import os

class MLModel:
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        try:
            self.scaler = joblib.load(os.path.join(base_dir, "models/scaler.pkl"))
            self.rain_model = joblib.load(os.path.join(base_dir, "models/rain_model.pkl"))
            self.temp_model = joblib.load(os.path.join(base_dir, "models/temp_model.pkl"))
            self.is_loaded = True
        except FileNotFoundError:
            print("Warning: ML models not found. Run train_model.py first.")
            self.is_loaded = False

    def predict(self, recent_data: dict):
        if not self.is_loaded:
            return {"error": "Models not loaded"}
        
        # Ensure the data matches the training format
        # [temperature, humidity, pressure, air_quality]
        df = pd.DataFrame([{
            "temperature": recent_data.get("temperature", 0),
            "humidity": recent_data.get("humidity", 0),
            "pressure": recent_data.get("pressure", 0),
            "air_quality": recent_data.get("air_quality", 0)
        }])
        
        # Scale and predict
        scaled = self.scaler.transform(df)
        rain_pred = self.rain_model.predict(scaled)[0]
        temp_pred = self.temp_model.predict(scaled)[0]
        
        return {
            "rain_tomorrow": bool(rain_pred),
            "predicted_max_temp": round(float(temp_pred), 1)
        }

predictor = MLModel()
