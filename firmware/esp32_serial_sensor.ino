/* ESP32 + DHT22 serial bridge example. NOT compiled or hardware-validated here.
   Arduino libraries: DHT sensor library + Adafruit Unified Sensor.
   Connect DHT22 DATA to GPIO4, VCC 3.3V, common GND; use appropriate pull-up.
   Change site coordinates and source/calibration metadata before field use.
   NTP via Wi-Fi provides UTC; measurements are withheld until clock is valid.
   Serial output is newline JSON for device_client.py --serial COMx.
   The laptop bridge persists/retries delivery. MCU has no persistent outbox. */
#include <WiFi.h>
#include <DHT.h>
#include <time.h>
#include <esp_system.h>
const char* WIFI_SSID="CHANGE_ME";
const char* WIFI_PASSWORD="CHANGE_ME";
const char* SITE_ID="FIELD-SITE-001";
const double LATITUDE=-3.1, LONGITUDE=-60.0;
DHT dht(4,DHT22);
unsigned long lastRead=0;
unsigned long sequenceNumber=0;
uint32_t bootId;
void setup(){
 Serial.begin(115200);dht.begin();bootId=esp_random();
 WiFi.begin(WIFI_SSID,WIFI_PASSWORD);configTime(0,0,"pool.ntp.org","time.google.com");
}
void emitValue(const char* metric,float value,const char* timestamp){
 if(isnan(value))return; // A failed read is absence, never an invented zero.
 String id=String("esp32-")+String(bootId,HEX)+"-"+String(sequenceNumber++);
 Serial.printf("{\"id\":\"%s\",\"site_id\":\"%s\",\"source_type\":\"sensor\",\"source_ref\":\"ESP32 DHT22; calibration pending\",\"mode\":\"FIELD\",\"timestamp\":\"%s\",\"latitude\":%.6f,\"longitude\":%.6f,\"metric\":\"%s\",\"value\":%.3f,\"quality\":\"valid\",\"metadata\":{\"calibration_status\":\"pending\",\"transport\":\"USB serial\"}}\n",id.c_str(),SITE_ID,timestamp,LATITUDE,LONGITUDE,metric,value);
}
void loop(){
 if(millis()-lastRead<10000)return;lastRead=millis();
 time_t t=time(nullptr);if(t<1700000000)return;
 struct tm utc;gmtime_r(&t,&utc);char timestamp[32];strftime(timestamp,sizeof(timestamp),"%Y-%m-%dT%H:%M:%SZ",&utc);
 emitValue("temperature_c",dht.readTemperature(),timestamp);emitValue("humidity_pct",dht.readHumidity(),timestamp);
}
