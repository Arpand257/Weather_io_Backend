import urllib.request
import json
import time
import random

def simulate():
    print("Starting simulated live data feed...")
    temp = 25.0
    hum = 60.0
    pres = 1012.0
    air = 40.0

    while True:
        # fluctuate values slightly
        temp += random.uniform(-0.5, 0.5)
        hum += random.uniform(-1.0, 1.0)
        pres += random.uniform(-0.5, 0.5)
        air += random.uniform(-2.0, 2.0)

        # keep in bounds
        hum = max(0, min(100, hum))
        air = max(0, air)

        data = {
            "temperature": round(temp, 1),
            "humidity": round(hum, 1),
            "pressure": round(pres, 2),
            "air_quality": round(air, 1)
        }

        try:
            req = urllib.request.Request(
                'http://127.0.0.1:8000/api/ingest', 
                data=json.dumps(data).encode(), 
                headers={'Content-Type': 'application/json'}
            )
            urllib.request.urlopen(req)
            print(f"Sent live data: {data}")
        except Exception as e:
            print(f"Failed to send data: {e}")

        time.sleep(5)

if __name__ == "__main__":
    simulate()
