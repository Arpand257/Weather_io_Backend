#include <DHT.h>
#include <ESP8266HTTPClient.h>
#include <ESP8266WiFi.h>
#include <time.h>

// ==============================
// WiFi
// ==============================
const char *ssid = "Wifi_Name";
const char *password = "Wifi_Password";

// ==============================
// Backend API
// ==============================
const char *serverURL = "http://192.168.29.226:8000/api/ingest";

// ==============================
// Pins
// ==============================
#define DHTPIN D4
#define DHTTYPE DHT11

#define MQ135_PIN A0
#define LDR_PIN D5
#define RAIN_PIN D6

DHT dht(DHTPIN, DHTTYPE);

unsigned long lastSend = 0;
const unsigned long sendInterval = 300000; // 5 minutes (5 * 60 * 1000 ms)

void sendWeatherData() {

  float temperature = dht.readTemperature();
  float humidity = dht.readHumidity();

  int airQuality = analogRead(MQ135_PIN);
  int sunlight = digitalRead(LDR_PIN);
  int rain = digitalRead(RAIN_PIN);

  if (isnan(temperature) || isnan(humidity)) {
    Serial.println("DHT11 reading failed!");
    return;
  }

  String sunlightStatus;

  if (sunlight == LOW) {
    sunlightStatus = "Bright";
  } else {
    sunlightStatus = "Dark";
  }

  String rainStatus;

  if (rain == LOW) {
    rainStatus = "Raining";
  } else {
    rainStatus = "No Rain";
  }

  // Get current time from NTP (already in IST based on setup config)
  time_t now = time(nullptr);
  struct tm *timeinfo = localtime(&now);
  char timeStringBuff[50];
  strftime(timeStringBuff, sizeof(timeStringBuff), "%Y-%m-%d %H:%M:%S",
           timeinfo);

  // ==============================
  // Create JSON
  // ==============================

  String json = "{";

  json += "\"temperature\":";
  json += String(temperature, 1);

  json += ",\"humidity\":";
  json += String(humidity, 1);

  json += ",\"air_quality\":";
  json += String(airQuality);

  // Add dummy pressure since the FastAPI backend requires it!
  json += ",\"pressure\":1013.25";

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

  Serial.println();
  Serial.println("Sending data:");
  Serial.println(json);

  // ==============================
  // HTTP POST
  // ==============================

  if (WiFi.status() == WL_CONNECTED) {

    WiFiClient client;
    HTTPClient http;

    http.begin(client, serverURL);

    http.addHeader("Content-Type", "application/json");

    int httpResponseCode = http.POST(json);

    Serial.print("HTTP Response: ");
    Serial.println(httpResponseCode);

    if (httpResponseCode > 0) {

      String response = http.getString();

      Serial.print("Server response: ");
      Serial.println(response);

    } else {

      Serial.print("Error sending data: ");
      Serial.println(http.errorToString(httpResponseCode));
    }

    http.end();

  } else {

    Serial.println("WiFi disconnected!");
  }
}

void setup() {

  Serial.begin(9600);

  dht.begin();

  pinMode(LDR_PIN, INPUT);
  pinMode(RAIN_PIN, INPUT);

  Serial.println();
  Serial.println("==============================");
  Serial.println("ESP8266 WEATHER STATION");
  Serial.println("==============================");

  WiFi.begin(ssid, password);

  Serial.print("Connecting to WiFi");

  while (WiFi.status() != WL_CONNECTED) {

    delay(500);
    Serial.print(".");
  }

  Serial.println();

  Serial.println("WiFi Connected!");

  Serial.print("ESP8266 IP: ");
  Serial.println(WiFi.localIP());

  // Initialize time with IST offset (5.5 hours * 3600 seconds = 19800)
  configTime(19800, 0, "pool.ntp.org", "time.nist.gov");
  Serial.print("Synchronizing time");
  time_t now = time(nullptr);
  while (now < 8 * 3600 * 2) {
    delay(500);
    Serial.print(".");
    now = time(nullptr);
  }
  Serial.println("\nTime synchronized!");

  Serial.print("Backend: ");
  Serial.println(serverURL);

  Serial.println("==============================");
}

void loop() {

  if (millis() - lastSend >= sendInterval) {

    lastSend = millis();

    sendWeatherData();
  }
}
