#include <Adafruit_BMP085.h>
#include <DHT.h>
#include <ESP8266HTTPClient.h>
#include <ESP8266WiFi.h>
#include <Wire.h>
#include <time.h>

// ==============================
// WiFi
// ==============================
const char *ssid = "moto";
const char *password = "1234567890";

// ==============================
// Backend API
// ==============================
const char *serverURL = "http://10.193.21.125:8000/api/ingest";

// ==============================
// Pins
// ==============================
#define DHTPIN D4
#define DHTTYPE DHT11

#define MQ135_PIN A0
#define LDR_PIN D5
#define RAIN_PIN D6

DHT dht(DHTPIN, DHTTYPE);
Adafruit_BMP085 bmp;

unsigned long lastSend = 0;
const unsigned long sendInterval = 300000; // 5 minutes

bool bmpAvailable = false;

// ==============================
// Print current sensor readings
// ==============================
void sendWeatherData() {

  Serial.println();
  Serial.println("====================================");
  Serial.println("            WEATHER DATA");
  Serial.println("====================================");

  // Read sensors
  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  int airQuality = analogRead(MQ135_PIN);
  int sunlight = digitalRead(LDR_PIN);
  int rain = digitalRead(RAIN_PIN);

  float pressure = 0;

  if (bmpAvailable) {
    pressure = bmp.readPressure() / 100.0;
  }

  // DHT11 validation
  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("[ERROR] DHT11 reading failed!");
    return;
  }

  // Convert digital sensor readings
  String sunlightStatus = (sunlight == LOW) ? "Bright" : "Dark";

  String rainStatus = (rain == LOW) ? "Raining" : "No Rain";

  // Get timestamp
  time_t now = time(nullptr);
  struct tm *timeinfo = localtime(&now);

  char timeStringBuff[30];

  if (timeinfo != nullptr && now > 100000) {
    strftime(timeStringBuff, sizeof(timeStringBuff), "%Y-%m-%d %H:%M:%S",
             timeinfo);
  } else {
    strcpy(timeStringBuff, "Time not synchronized");
  }

  // ==============================
  // SERIAL MONITOR OUTPUT
  // ==============================
  Serial.println("[SENSOR READINGS]");

  Serial.print("Temperature : ");
  Serial.print(temperature, 1);
  Serial.println(" °C");

  Serial.print("Humidity    : ");
  Serial.print(humidity, 1);
  Serial.println(" %");

  Serial.print("Air Quality : ");
  Serial.print(airQuality);
  Serial.println(" (raw ADC value)");

  Serial.print("Pressure    : ");

  if (bmpAvailable) {
    Serial.print(pressure, 2);
    Serial.println(" hPa");
  } else {
    Serial.println("BMP180 unavailable");
  }

  Serial.print("Sunlight    : ");
  Serial.print(sunlightStatus);
  Serial.print(" (Digital: ");
  Serial.print(sunlight);
  Serial.println(")");

  Serial.print("Rain        : ");
  Serial.print(rainStatus);
  Serial.print(" (Digital: ");
  Serial.print(rain);
  Serial.println(")");

  Serial.print("Device Time : ");
  Serial.println(timeStringBuff);

  Serial.println("------------------------------------");

  // ==============================
  // CREATE JSON
  // ==============================
  String json = "{";

  json += "\"temperature\":";
  json += String(temperature, 1);

  json += ",\"humidity\":";
  json += String(humidity, 1);

  json += ",\"air_quality\":";
  json += String(airQuality);

  json += ",\"pressure\":";
  json += String(pressure, 2);

  json += ",\"sunlight\":\"";
  json += sunlightStatus;
  json += "\"";

  json += ",\"rain\":\"";
  json += rainStatus;
  json += "\"";

  json += ",\"device_time\":\"";
  json += String(timeStringBuff);
  json += "\"";

  json += "}";

  Serial.println("[JSON DATA]");
  Serial.println(json);

  // ==============================
  // SEND TO BACKEND
  // ==============================
  if (WiFi.status() == WL_CONNECTED) {

    WiFiClient client;
    HTTPClient http;

    Serial.println("[BACKEND] Sending data...");

    if (http.begin(client, serverURL)) {

      http.addHeader("Content-Type", "application/json");

      int httpResponseCode = http.POST(json);

      Serial.print("HTTP Status: ");
      Serial.println(httpResponseCode);

      if (httpResponseCode > 0) {
        Serial.print("Server Response: ");
        Serial.println(http.getString());
      } else {
        Serial.print("HTTP Error: ");
        Serial.println(http.errorToString(httpResponseCode));
      }

      http.end();

    } else {
      Serial.println("[ERROR] Could not initialize HTTP client!");
    }

  } else {
    Serial.println("[ERROR] WiFi disconnected!");
  }

  Serial.println("====================================");
  Serial.println("Next reading in 5 minutes.");
  Serial.println("====================================");
}

// ==============================
// SETUP
// ==============================
void setup() {

  Serial.begin(9600);
  delay(1000);

  Serial.println();
  Serial.println("====================================");
  Serial.println("     ESP8266 WEATHER STATION");
  Serial.println("====================================");

  dht.begin();
  Wire.begin();

  bmpAvailable = bmp.begin();

  if (bmpAvailable) {
    Serial.println("[OK] BMP180/BMP085 detected.");
  } else {
    Serial.println("[WARNING] BMP180/BMP085 not detected!");
  }

  pinMode(LDR_PIN, INPUT);
  pinMode(RAIN_PIN, INPUT);

  Serial.println("[OK] Sensors initialized.");

  // Connect to WiFi
  WiFi.begin(ssid, password);

  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.println("[OK] WiFi Connected!");

  Serial.print("ESP8266 IP: ");
  Serial.println(WiFi.localIP());

  Serial.print("Backend URL: ");
  Serial.println(serverURL);

  // Synchronize time to IST
  configTime(19800, 0, "pool.ntp.org", "time.nist.gov");

  Serial.print("Synchronizing time");

  time_t now = time(nullptr);

  while (now < 100000) {
    delay(500);
    Serial.print(".");
    now = time(nullptr);
  }

  Serial.println();
  Serial.println("[OK] Time synchronized!");

  Serial.println("====================================");
  Serial.println("Starting sensor monitoring...");
  Serial.println("====================================");

  // Send the first reading immediately
  lastSend = millis() - sendInterval;
}

// ==============================
// LOOP
// ==============================
void loop() {

  if (millis() - lastSend >= sendInterval) {

    lastSend = millis();
    sendWeatherData();
  }

  // Keep ESP8266 responsive
  yield();
}