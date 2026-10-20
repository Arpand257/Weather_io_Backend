/*
 * ======================================================================================
 * SmartWeatherDash - ESP8266 Onboarding Station with WiFiManager
 * ======================================================================================
 * Features:
 * 1. Captive Portal Onboarding:
 *    - If no Wi-Fi credentials exist (or cannot connect), launches a Hotspot:
 * "SmartWeather-Setup"
 *    - Connect to it on your phone/laptop to open setup page (192.168.4.1)
 *    - Enter Home Wi-Fi SSID, Password, and your Backend Server URL
 *    - Credentials are saved permanently to ESP8266 internal Flash/EEPROM
 * 2. Automatic Reconnection:
 *    - On future power-ups, connects directly to saved Wi-Fi within 2-3 seconds
 * 3. Factory Reset:
 *    - Type "reset" in Serial Monitor OR hold FLASH button (GPIO 0 / D3) on
 * boot to re-trigger setup hotspot
 * 4. Sensors:
 *    - DHT11 (D4): Temperature & Humidity
 *    - BMP085/BMP180 (I2C): Barometric Pressure
 *    - MQ-135 (A0): Air Quality
 *    - LDR (D5): Sunlight detection
 *    - Rain Sensor (D6): Rain detection
 * ======================================================================================
 * Required Arduino Libraries:
 * - WiFiManager by tzapu (install via Arduino Library Manager)
 * - DHT sensor library by Adafruit
 * - Adafruit BMP085 / BMP180 Library
 * - Adafruit Unified Sensor
 * ======================================================================================
 */

#include <Adafruit_BMP085.h>
#include <DHT.h>
#include <DNSServer.h>
#include <EEPROM.h>
#include <ESP8266WebServer.h>
#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiManager.h> // https://github.com/tzapu/WiFiManager
#include <Wire.h>
#include <time.h>

// ==============================
// Sensor Pins
// ==============================
#define DHTPIN D4
#define DHTTYPE DHT11

#define MQ135_PIN A0
#define LDR_PIN D5
#define RAIN_PIN D6
#define RESET_PIN D3 // Flash button on NodeMCU (GPIO 0)

DHT dht(DHTPIN, DHTTYPE);
Adafruit_BMP085 bmp;

// ==============================
// Storage & Configuration
// ==============================
#define EEPROM_SIZE 256
#define SERVER_URL_MAX_LEN 128

// Default fallback server URL if none entered (updated with PC Wi-Fi IP: 10.163.219.125)
char serverURL[SERVER_URL_MAX_LEN] = "http://10.163.219.125:8000/api/ingest";

bool shouldSaveConfig = false;
bool bmpAvailable = false;

unsigned long lastSend = 0;
const unsigned long sendInterval = 300000; // 5 minutes (in milliseconds)

// Callback notifying us of the need to save config
void saveConfigCallback() {
  Serial.println("[WIFI-MGR] Configuration updated by user in captive portal.");
  shouldSaveConfig = true;
}

// Save server URL to EEPROM
void saveCustomConfigToEEPROM(const char *url) {
  EEPROM.begin(EEPROM_SIZE);
  for (int i = 0; i < SERVER_URL_MAX_LEN; i++) {
    if (i < strlen(url)) {
      EEPROM.write(i, url[i]);
    } else {
      EEPROM.write(i, '\0');
    }
  }
  EEPROM.commit();
  EEPROM.end();
  Serial.println("[EEPROM] Server URL successfully saved to flash memory.");
}

// Load server URL from EEPROM
void loadCustomConfigFromEEPROM() {
  EEPROM.begin(EEPROM_SIZE);
  char loaded[SERVER_URL_MAX_LEN];
  for (int i = 0; i < SERVER_URL_MAX_LEN; i++) {
    loaded[i] = EEPROM.read(i);
  }
  EEPROM.end();

  // If valid URL string exists in EEPROM and is not the outdated placeholder, use it
  if (loaded[0] == 'h' && loaded[1] == 't' && loaded[2] == 't' &&
      loaded[3] == 'p' && strstr(loaded, "192.168.1.100") == nullptr) {
    strncpy(serverURL, loaded, SERVER_URL_MAX_LEN - 1);
    serverURL[SERVER_URL_MAX_LEN - 1] = '\0';
    Serial.print("[EEPROM] Loaded saved Server URL: ");
    Serial.println(serverURL);
  } else {
    Serial.print("[EEPROM] Using default Server URL: ");
    Serial.println(serverURL);
  }
}

// ==============================
// Send sensor readings to backend
// ==============================
void sendWeatherData() {
  Serial.println();
  Serial.println("====================================");
  Serial.println("       WEATHER STATION DATA");
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

  // Get synchronized timestamp
  time_t now = time(nullptr);
  struct tm *timeinfo = localtime(&now);

  char timeStringBuff[30];
  if (timeinfo != nullptr && now > 100000) {
    strftime(timeStringBuff, sizeof(timeStringBuff), "%Y-%m-%d %H:%M:%S",
             timeinfo);
  } else {
    strcpy(timeStringBuff, "Time not synchronized");
  }

  // Serial Monitor Output
  Serial.print("Temperature : ");
  Serial.print(temperature, 1);
  Serial.println(" °C");
  Serial.print("Humidity    : ");
  Serial.print(humidity, 1);
  Serial.println(" %");
  Serial.print("Air Quality : ");
  Serial.print(airQuality);
  Serial.println(" (raw ADC)");
  Serial.print("Pressure    : ");
  if (bmpAvailable) {
    Serial.print(pressure, 2);
    Serial.println(" hPa");
  } else {
    Serial.println("BMP180 unavailable");
  }
  Serial.print("Sunlight    : ");
  Serial.println(sunlightStatus);
  Serial.print("Rain        : ");
  Serial.println(rainStatus);
  Serial.print("Device Time : ");
  Serial.println(timeStringBuff);
  Serial.print("Target URL  : ");
  Serial.println(serverURL);

  // Build JSON Payload
  String json = "{";
  json += "\"temperature\":" + String(temperature, 1);
  json += ",\"humidity\":" + String(humidity, 1);
  json += ",\"air_quality\":" + String(airQuality);
  json += ",\"pressure\":" + String(pressure, 2);
  json += ",\"sunlight\":\"" + sunlightStatus + "\"";
  json += ",\"rain\":\"" + rainStatus + "\"";
  json += ",\"device_time\":\"" + String(timeStringBuff) + "\"";
  json += "}";

  Serial.println("[JSON DATA] " + json);

  // Send to Backend
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
      Serial.println("[ERROR] Could not initialize HTTP client to " +
                     String(serverURL));
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

  pinMode(RESET_PIN, INPUT_PULLUP);
  pinMode(LDR_PIN, INPUT);
  pinMode(RAIN_PIN, INPUT);

  Serial.println();
  Serial.println("=================================================");
  Serial.println("   SMART WEATHER DASHBOARD - ONBOARDING BOOT");
  Serial.println("=================================================");

  // Load custom server URL from EEPROM
  loadCustomConfigFromEEPROM();

  // Initialize sensors
  dht.begin();
  Wire.begin();
  bmpAvailable = bmp.begin();
  if (bmpAvailable) {
    Serial.println("[OK] BMP180/BMP085 barometric sensor detected.");
  } else {
    Serial.println("[WARNING] BMP180 not detected, continuing without it.");
  }

  // Check if factory reset requested via button hold (pin D3 / Flash)
  if (digitalRead(RESET_PIN) == LOW) {
    Serial.println(
        "[RESET] Flash button held on boot. Clearing Wi-Fi credentials!");
    WiFiManager wm;
    wm.resetSettings();
    delay(1000);
  }

  // ============================================================
  // WiFiManager Setup Flow
  // ============================================================
  WiFiManager wifiManager;

  // Set callback for when config is saved in web portal
  wifiManager.setSaveConfigCallback(saveConfigCallback);

  // Custom text field in portal for the Backend URL
  WiFiManagerParameter custom_server_url("server",
                                         "Backend Ingest URL (http://...)",
                                         serverURL, SERVER_URL_MAX_LEN);
  wifiManager.addParameter(&custom_server_url);

  // Hotspot portal configuration
  // Portal will timeout after 180 seconds if untouched (resumes loop or
  // re-attempts)
  wifiManager.setConfigPortalTimeout(180);

  Serial.println("[WIFI-MGR] Connecting to saved Wi-Fi...");
  Serial.println(
      "           (If not found, Hotspot 'SmartWeather-Setup' will start)");

  // Hotspot SSID: "SmartWeather-Setup", Password: "password123" (or NULL for
  // open)
  if (!wifiManager.autoConnect("SmartWeather-Setup", "password123")) {
    Serial.println("[WIFI-MGR] Portal timed out without connection. Restarting "
                   "ESP8266...");
    delay(3000);
    ESP.restart();
    delay(5000);
  }

  // Successfully connected to Wi-Fi!
  Serial.println();
  Serial.println("[OK] Connected to Home Wi-Fi successfully!");
  Serial.print("ESP8266 IP Address: ");
  Serial.println(WiFi.localIP());

  // Save updated custom URL if changed in the captive portal
  if (shouldSaveConfig) {
    strncpy(serverURL, custom_server_url.getValue(), SERVER_URL_MAX_LEN - 1);
    serverURL[SERVER_URL_MAX_LEN - 1] = '\0';
    saveCustomConfigToEEPROM(serverURL);
  }

  // Synchronize time with NTP servers (IST offset: UTC + 5:30 = 19800 seconds)
  configTime(19800, 0, "pool.ntp.org", "time.nist.gov");
  Serial.print("Synchronizing time");
  time_t now = time(nullptr);
  int retries = 0;
  while (now < 100000 && retries < 20) {
    delay(500);
    Serial.print(".");
    now = time(nullptr);
    retries++;
  }
  Serial.println();
  if (now > 100000) {
    Serial.println("[OK] Time synchronized successfully.");
  } else {
    Serial.println(
        "[WARNING] NTP time sync took too long, will retry in background.");
  }

  Serial.println("=================================================");
  Serial.println("Monitoring active. Initial reading starting...");
  Serial.println("=================================================");

  // Send first reading immediately
  lastSend = millis() - sendInterval;
}

// ==============================
// LOOP
// ==============================
void loop() {
  // Check if user types "reset" in Serial Monitor to wipe Wi-Fi for testing
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.equalsIgnoreCase("reset")) {
      Serial.println(
          "[COMMAND] 'reset' received. Clearing saved Wi-Fi and rebooting...");
      WiFiManager wm;
      wm.resetSettings();
      delay(1000);
      ESP.restart();
    }
  }

  // Periodic sensor transmission every 5 minutes
  if (millis() - lastSend >= sendInterval) {
    lastSend = millis();
    sendWeatherData();
  }

  yield();
}
