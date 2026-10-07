import joblib
import pandas as pd
import os
import math
from datetime import datetime, timezone

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

    def calculate_solar_position(self, dt: datetime, lat: float, lon: float):
        # dt should be UTC datetime
        t = dt.replace(tzinfo=timezone.utc).timestamp()
        n = (t / 86400.0) - 10957.5
        
        L = (280.460 + 0.9856474 * n) % 360.0
        g = (357.528 + 0.9856003 * n) % 360.0
        
        lambda_ = L + 1.915 * math.sin(math.radians(g)) + 0.020 * math.sin(math.radians(2 * g))
        epsilon = 23.439 - 0.0000004 * n
        
        delta = math.asin(math.sin(math.radians(epsilon)) * math.sin(math.radians(lambda_)))
        
        alpha = math.degrees(math.atan2(math.cos(math.radians(epsilon)) * math.sin(math.radians(lambda_)), math.cos(math.radians(lambda_))))
        alpha = alpha % 360.0
        
        GMST = (280.46061837 + 360.98564736629 * n) % 360.0
        LST = (GMST + lon) % 360.0
        
        H = (LST - alpha) % 360.0
        if H > 180.0:
            H -= 360.0
        elif H < -180.0:
            H += 360.0
            
        lat_rad = math.radians(lat)
        H_rad = math.radians(H)
        
        el_rad = math.asin(math.sin(lat_rad) * math.sin(delta) + math.cos(lat_rad) * math.cos(delta) * math.cos(H_rad))
        elevation = math.degrees(el_rad)
        
        az_rad = math.atan2(math.sin(H_rad), math.cos(H_rad) * math.sin(lat_rad) - math.tan(delta) * math.cos(lat_rad))
        azimuth = (math.degrees(az_rad) + 180.0) % 360.0
        
        return azimuth, elevation

    def predict(self, recent_data: dict, lat: float = 22.738318, lon: float = 88.479709):
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
        
        # Calculate Sun Position
        azimuth, elevation = self.calculate_solar_position(datetime.utcnow(), lat, lon)
        
        return {
            "rain_tomorrow": bool(rain_pred),
            "predicted_max_temp": round(float(temp_pred), 1),
            "sun_azimuth": round(azimuth, 2),
            "sun_elevation": round(elevation, 2)
        }

predictor = MLModel()
