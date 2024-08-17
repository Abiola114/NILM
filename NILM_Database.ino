#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <PZEM004Tv30.h>
#include <ESP8266WebServer.h>
#include <math.h>

#define PZEM_RX_PIN D5
#define PZEM_TX_PIN D6
#define RELAY_PIN D3

SoftwareSerial pzemSWSerial(PZEM_RX_PIN, PZEM_TX_PIN);
PZEM004Tv30 pzem(pzemSWSerial);

const char* ssid = "Abiola";
const char* password = "porter1234567";

ESP8266WebServer server(80);
const char* host = "script.google.com";
const int httpsPort = 443;

unsigned long previousMillis = 0;
const unsigned long onDuration = 60000;  // Relay ON for 60 seconds
const unsigned long offDuration = 15000; // Relay OFF for 15 seconds
bool relayState = LOW; // Initial state of the relay (OFF)
int cycleCount = 0; // Initialize the cycle counter

WiFiClientSecure client;

String GAS_ID = "AKfycbxrnlSi7GkXU7EkDmo0vLFK0IiNG1cDes_lxX7N0rOUOsDSwDMijB4EaH08dBZwXZ7_";

void setup() {
  Serial.begin(115200);
  delay(500);
  pzem.resetEnergy();
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, relayState); // Set initial relay state

  WiFi.begin(ssid, password);
  Serial.println("");
  
  Serial.print("Connecting");
  while (WiFi.status() != WL_CONNECTED) {
    Serial.print(".");
    delay(500); // Add a small delay to avoid overwhelming the Serial output
  }
  Serial.println("");
  Serial.print("Successfully connected to: ");
  Serial.println(ssid);
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());
  client.setInsecure();
  server.begin();
}

void loop() {
  if (cycleCount >= 50) {
    Serial.println("Cycle limit reached. Stopping data transmission.");
    return; // Stop the loop after 50 cycles
  }

  if (!client.connect(host, httpsPort)) {
    Serial.println("Connection failed");
    return;
  }

  float v = pzem.voltage();
  float c = pzem.current();
  float p = pzem.power();
  float e = pzem.energy();
  float f = pzem.frequency();
  float pf = pzem.pf();

  if (isnan(v)) v = 0;
  if (isnan(c)) c = 0;
  if (isnan(p)) p = 0;
  if (isnan(e)) e = 0;
  if (isnan(f)) f = 0;
  if (isnan(pf)) pf = 0;

  String string_voltage = String(v);
  String string_current = String(c);
  String string_pf = String(pf);
  String string_energy = String(e);
  String string_power = String(p);
  String string_frequency = String(f);

  String url = "/macros/s/" + GAS_ID + "/exec?Voltage=" + string_voltage + 
               "&Current=" + string_current + "&pf=" + string_pf + 
               "&Energy=" + string_energy + "&Power=" + string_power + 
               "&frequency=" + string_frequency;

  Serial.print("Requesting URL: ");
  Serial.println(url);

  // Relay control logic
  unsigned long currentMillis = millis();

  if (relayState == LOW && (currentMillis - previousMillis >= offDuration)) {
    relayState = HIGH;
    digitalWrite(RELAY_PIN, relayState);
    previousMillis = currentMillis;
  } else if (relayState == HIGH && (currentMillis - previousMillis >= onDuration)) {
    relayState = LOW;
    digitalWrite(RELAY_PIN, relayState);
    previousMillis = currentMillis;
    cycleCount++; // Increment the cycle counter each time the relay turns OFF
  }

  client.print(String("GET ") + url + " HTTP/1.1\r\n" +
               "Host: " + host + "\r\n" +
               "User-Agent: BuildFailureDetectorESP8266\r\n" +
               "Connection: close\r\n\r\n");

  Serial.println("Request sent");

  while (client.connected()) {
    String line = client.readStringUntil('\n');
    if (line.startsWith("HTTP/1.1")) {
      Serial.print("Status: ");
      Serial.println(line);
    }
    Serial.println(line);
  }

  Serial.println("Closing connection");
  Serial.println("==========");
  Serial.println();
}
