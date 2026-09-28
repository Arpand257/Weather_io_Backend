import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import os

print("Loading dataset...")
df = pd.read_csv("dataset/Weather_Data.csv")

# We will map our dataset features to match the IoT device's payload:
# IoT Payload: temperature, humidity, pressure, air_quality
# We use 9am readings from the dataset as a proxy for "current" readings.

print("Preprocessing data...")
# Extract relevant features
X = pd.DataFrame()
X["temperature"] = df["Temp9am"]
X["humidity"] = df["Humidity9am"]
X["pressure"] = df["Pressure9am"]
# The dataset doesn't have air quality, so we synthesize it for the sake of the model
# (e.g., higher wind speed = better air quality)
X["air_quality"] = 150 - df["WindSpeed9am"].fillna(10) * 2 

# Target variables
y_rain = df["RainTomorrow"].map({"Yes": 1, "No": 0})
y_temp = df["MaxTemp"] # Predicting the max temp for the day

# Handle missing values
X = X.fillna(X.median())
y_rain = y_rain.fillna(0)
y_temp = y_temp.fillna(y_temp.median())

# Train/Test Split
X_train, X_test, y_rain_train, y_rain_test, y_temp_train, y_temp_test = train_test_split(
    X, y_rain, y_temp, test_size=0.2, random_state=42
)

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print("Training Rain Predictor (Classifier)...")
rain_model = RandomForestClassifier(n_estimators=50, random_state=42)
rain_model.fit(X_train_scaled, y_rain_train)
rain_acc = rain_model.score(X_test_scaled, y_rain_test)
print(f"Rain Model Accuracy: {rain_acc:.2%}")

print("Training Temperature Predictor (Regressor)...")
temp_model = RandomForestRegressor(n_estimators=50, random_state=42)
temp_model.fit(X_train_scaled, y_temp_train)
temp_r2 = temp_model.score(X_test_scaled, y_temp_test)
print(f"Temp Model R2 Score: {temp_r2:.4f}")

print("Saving models to models/ directory...")
os.makedirs("models", exist_ok=True)
joblib.dump(scaler, "models/scaler.pkl")
joblib.dump(rain_model, "models/rain_model.pkl")
joblib.dump(temp_model, "models/temp_model.pkl")

print("Training complete! Models saved successfully.")
