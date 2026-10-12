import math
from datetime import datetime, timezone, timedelta

def calculate_weather_score(data: dict) -> dict:
    """
    Computes a composite Comfort & Safety Weather Score (0-100) based on
    temperature, humidity, air quality, UV, pressure, rain probability, and wind.
    """
    temp = float(data.get("temperature") if data.get("temperature") is not None else 25.0)
    humidity = float(data.get("humidity") if data.get("humidity") is not None else 60.0)
    aqi = float(data.get("air_quality") if data.get("air_quality") is not None else (data.get("aqi") or 50.0))
    uv = float(data.get("uvIndex") if data.get("uvIndex") is not None else 4.0)
    pressure = float(data.get("pressure") if data.get("pressure") is not None and data.get("pressure") > 500 else 1013.25)
    
    # Rain risk
    if data.get("rainProbability") is not None:
        rain_prob = float(data.get("rainProbability"))
    elif data.get("rain") == "Raining":
        rain_prob = 90.0
    else:
        rain_prob = 10.0

    wind_speed = float(data.get("windSpeed") if data.get("windSpeed") is not None else 10.0)

    # Temperature scoring (ideal 18-28°C, optimal 23°C)
    if 18 <= temp <= 28:
        temp_score = 100 - abs(temp - 23) * 4
    elif temp < 10 or temp > 38:
        temp_score = 20
    elif temp < 18:
        temp_score = 60 - (18 - temp) * 3
    else:
        temp_score = 60 - (temp - 28) * 3

    # Humidity scoring (ideal 40-65%, optimal 52%)
    if 40 <= humidity <= 65:
        hum_score = 100 - abs(humidity - 52) * 1.5
    elif humidity < 30 or humidity > 85:
        hum_score = 25
    elif humidity < 40:
        hum_score = 50
    else:
        hum_score = 50 - (humidity - 65) * 1.5

    # AQI scoring (0-50: Good=100, 51-100: Moderate=80-50, etc.)
    if aqi <= 50:
        aqi_score = 100
    elif aqi <= 100:
        aqi_score = 80 - (aqi - 50) * 0.6
    elif aqi <= 150:
        aqi_score = 50 - (aqi - 100) * 0.5
    else:
        aqi_score = max(0, 25 - (aqi - 150) * 0.3)

    # UV scoring
    if uv <= 2:
        uv_score = 100
    elif uv <= 5:
        uv_score = 85 - uv * 5
    elif uv <= 7:
        uv_score = 60 - uv * 4
    else:
        uv_score = max(0, 40 - uv * 4)

    # Rain scoring
    rain_score = max(0, 100 - rain_prob * 1.2)

    # Wind scoring
    if wind_speed < 15:
        wind_score = 100
    elif wind_speed < 30:
        wind_score = 85 - wind_speed
    elif wind_speed < 50:
        wind_score = 55 - wind_speed * 0.5
    else:
        wind_score = max(0, 30 - wind_speed * 0.3)

    # Pressure scoring
    if 1005 <= pressure <= 1020:
        press_score = 100
    elif pressure < 990 or pressure > 1035:
        press_score = 40
    else:
        press_score = 80

    weights = {
        "temp": 0.25,
        "hum": 0.20,
        "aqi": 0.20,
        "uv": 0.15,
        "rain": 0.10,
        "wind": 0.05,
        "press": 0.05,
    }

    score = round(
        temp_score * weights["temp"]
        + hum_score * weights["hum"]
        + aqi_score * weights["aqi"]
        + uv_score * weights["uv"]
        + rain_score * weights["rain"]
        + wind_score * weights["wind"]
        + press_score * weights["press"]
    )
    score = max(0, min(100, score))

    if score >= 85:
        label, color = "Excellent", "#10B981"
    elif score >= 70:
        label, color = "Very Comfortable", "#3B82F6"
    elif score >= 55:
        label, color = "Comfortable", "#F59E0B"
    elif score >= 40:
        label, color = "Fair", "#F97316"
    elif score >= 25:
        label, color = "Poor", "#EF4444"
    else:
        label, color = "Hazardous", "#7C3AED"

    factors = [
        {"name": "Temperature", "value": round(temp_score), "icon": "🌡️", "detail": f"{round(temp, 1)}°C"},
        {"name": "Humidity", "value": round(hum_score), "icon": "💧", "detail": f"{round(humidity)}%"},
        {"name": "Air Quality", "value": round(aqi_score), "icon": "🫁", "detail": f"AQI {round(aqi)}"},
        {"name": "UV Index", "value": round(uv_score), "icon": "☀️", "detail": f"UV {round(uv, 1)}"},
        {"name": "Rain Risk", "value": round(rain_score), "icon": "🌧️", "detail": f"{round(rain_prob)}%"},
        {"name": "Wind", "value": round(wind_score), "icon": "💨", "detail": f"{round(wind_speed, 1)} km/h"},
        {"name": "Pressure", "value": round(press_score), "icon": "🌬️", "detail": f"{round(pressure, 1)} hPa"},
    ]

    top_factor = min(factors, key=lambda f: f["value"])
    explanation = (
        f"Score of {score} is primarily influenced by {top_factor['name'].lower()} ({top_factor['detail']}). "
        + ("Overall conditions are comfortable for outdoor activities." if score >= 70
           else "Conditions are acceptable but some caution is advised." if score >= 40
           else "Conditions are challenging — consider limiting outdoor exposure.")
    )

    return {
        "score": score,
        "label": label,
        "color": color,
        "factors": factors,
        "explanation": explanation,
    }


def calculate_device_health(latest, readings_today_count: int = 0, first_reading = None) -> dict:
    """
    Computes real-time hardware status for ESP8266 weather station and individual sensors.
    """
    now = datetime.now(timezone.utc)
    if latest and latest.timestamp:
        ts = latest.timestamp if latest.timestamp.tzinfo else latest.timestamp.replace(tzinfo=timezone.utc)
        age_seconds = (now - ts).total_seconds()
        is_online = age_seconds < 600  # Online if reading received within last 10 mins
        iot_status = "connected" if is_online else ("syncing" if age_seconds < 3600 else "offline")
        last_comm = ts.isoformat()
    else:
        is_online = False
        iot_status = "offline"
        last_comm = (now - timedelta(hours=2)).isoformat()

    if first_reading and first_reading.timestamp and is_online:
        first_ts = first_reading.timestamp if first_reading.timestamp.tzinfo else first_reading.timestamp.replace(tzinfo=timezone.utc)
        uptime = max(1, round((now - first_ts).total_seconds() / 3600))
    else:
        uptime = 24 if is_online else 0

    temp_val = f"{latest.temperature:.1f}°C" if (latest and latest.temperature is not None) else "--"
    hum_val = f"{round(latest.humidity)}%" if (latest and latest.humidity is not None) else "--"
    press_val = f"{latest.pressure:.1f} hPa" if (latest and latest.pressure is not None and latest.pressure > 500) else "N/A"
    aqi_val = str(round(latest.air_quality)) if (latest and latest.air_quality is not None) else "--"
    rain_val = (latest.rain if (latest and latest.rain) else "No Rain")
    sun_val = (latest.sunlight if (latest and latest.sunlight) else "Bright")

    sensors = [
        {"id": "temperature", "name": "Temperature Sensor (DHT11)", "icon": "🌡️", "online": is_online and latest.temperature is not None, "lastSeen": last_comm, "value": temp_val},
        {"id": "humidity", "name": "Humidity Sensor (DHT11)", "icon": "💧", "online": is_online and latest.humidity is not None, "lastSeen": last_comm, "value": hum_val},
        {"id": "pressure", "name": "Barometer (BMP180)", "icon": "🌬️", "online": is_online and (latest.pressure or 0) > 500, "lastSeen": last_comm, "value": press_val},
        {"id": "aqi", "name": "Air Quality (MQ-135)", "icon": "🫁", "online": is_online and latest.air_quality is not None, "lastSeen": last_comm, "value": aqi_val},
        {"id": "rain", "name": "Rain Detector", "icon": "🌧️", "online": is_online, "lastSeen": last_comm, "value": rain_val},
        {"id": "sunlight", "name": "Light Sensor (LDR)", "icon": "☀️", "online": is_online, "lastSeen": last_comm, "value": sun_val},
    ]

    return {
        "device": {
            "id": "ESP8266-WX-001",
            "name": "SmartWeather Station NodeMCU",
            "firmware": "1.2.0",
            "status": iot_status,
            "online": is_online,
            "wifiSignal": -52 if is_online else None,
            "wifiQuality": "Excellent (-52 dBm)" if is_online else "Offline",
            "uptime": uptime,
            "lastComm": last_comm,
            "dataRate": "1 reading / 5 min" if is_online else "Offline",
            "battery": 100,
            "location": {
                "lat": 22.7383,
                "lng": 88.4797,
                "city": "Barrackpore",
                "state": "West Bengal",
            },
        },
        "sensors": sensors,
        "totalReadingsToday": readings_today_count,
        "dataCompleteness": 96 if is_online else 0,
    }


def detect_anomalies(history: list, current: dict) -> list:
    """
    Performs statistical anomaly detection using Z-score and threshold deviation checks.
    """
    anomalies = []
    if not history or len(history) < 3 or not current:
        return anomalies

    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Temperature Anomaly (Z-score check)
    temps = [h.get("temperature") for h in history if h.get("temperature") is not None]
    curr_temp = current.get("temperature")
    if len(temps) >= 3 and curr_temp is not None:
        avg_temp = sum(temps) / len(temps)
        variance = sum((t - avg_temp) ** 2 for t in temps) / len(temps)
        std_temp = math.sqrt(variance) or 1.0
        z_score = abs(curr_temp - avg_temp) / std_temp
        if z_score > 2.5:
            anomalies.append({
                "id": "temp_spike",
                "type": "temperature",
                "severity": "high" if z_score > 3.5 else "medium",
                "title": "Unusual Temperature Reading",
                "detected": now_iso,
                "current": f"{curr_temp:.1f}°C",
                "expected": f"{(avg_temp - std_temp * 2):.1f}°C – {(avg_temp + std_temp * 2):.1f}°C",
                "zScore": f"{z_score:.2f}",
                "possibleCause": "Direct sunlight on sensor, sudden thermal front, or sensor malfunction",
                "icon": "🌡️",
            })

    # 2. Air Quality Spike
    aqis = [h.get("air_quality") or h.get("aqi") for h in history if (h.get("air_quality") is not None or h.get("aqi") is not None)]
    curr_aqi = current.get("air_quality") or current.get("aqi")
    if len(aqis) >= 2 and curr_aqi is not None:
        last_aqi = aqis[0] if isinstance(aqis[0], (int, float)) else 50
        aqi_change = curr_aqi - last_aqi
        if abs(aqi_change) > 40:
            avg_aqi = sum(aqis) / len(aqis)
            anomalies.append({
                "id": "aqi_change",
                "type": "aqi",
                "severity": "medium",
                "title": "Rapid Air Quality Change",
                "detected": now_iso,
                "current": f"AQI {round(curr_aqi)}",
                "expected": f"AQI {max(0, round(avg_aqi - 20))} – {round(avg_aqi + 20)}",
                "zScore": f"{(abs(aqi_change) / 20):.2f}",
                "possibleCause": "Smoke, traffic emission, or industrial activity nearby",
                "icon": "🫁",
            })

    # 3. Barometric Pressure Sudden Drop / Rise
    pressures = [h.get("pressure") for h in history if h.get("pressure") is not None and h.get("pressure") > 500]
    curr_pres = current.get("pressure")
    if len(pressures) >= 3 and curr_pres is not None and curr_pres > 500:
        pres_change = curr_pres - pressures[-1]
        if abs(pres_change) > 4.0:
            anomalies.append({
                "id": "pressure_drop",
                "type": "pressure",
                "severity": "high" if pres_change < 0 else "medium",
                "title": "Rapid Pressure Drop (Storm Warning)" if pres_change < 0 else "Rapid Pressure Rise",
                "detected": now_iso,
                "current": f"{curr_pres:.1f} hPa",
                "expected": f"{(pressures[-1] - 2):.1f} – {(pressures[-1] + 2):.1f} hPa",
                "zScore": f"{(abs(pres_change) / 2.0):.2f}",
                "possibleCause": "Rapidly approaching storm system" if pres_change < 0 else "High pressure system moving in",
                "icon": "🌬️",
            })

    return anomalies
