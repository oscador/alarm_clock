#!/usr/bin/python
import RPi.GPIO as GPIO
import Adafruit_CharLCD as LCD
import ConfigParser, os, time, requests, sys, json, subprocess
from time import sleep, strftime
from datetime import datetime

# Raspberry Pi LCD pin setup
lcd_rs = 25
lcd_en = 24
lcd_d4 = 23
lcd_d5 = 17
lcd_d6 = 18
lcd_d7 = 22
lcd_backlight = 0

# Define LCD column and row size for 16x2 LCD.
lcd_columns = 16
lcd_rows = 2
lcd = LCD.Adafruit_CharLCD(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows, lcd_backlight)

# Raspberry Pi buzzer pin setup
BZRPin = 27
GPIO.setup(BZRPin, GPIO.OUT)   # Set pin mode as output
GPIO.output(BZRPin, GPIO.LOW)
p = GPIO.PWM(BZRPin, 50) # init frequency: 50HZ

# Frequency to download current conditions from Weather Underground
weather_update_freq=60

conf_file = 'alarm_clock.conf'
temp_file = "/tmp/alarm.cache.json"

def GetWeather():
    def WUDownload():
        r = requests.get(url)
        data = r.json()
        with open(temp_file, 'w') as f:
            json.dump(data, f)
        f.close()
        print "Data fetched successfully"

        try:
            f = open(temp_file, "r")
        except IOError:
            fetch_error()
        data = json.load(f)
        f.close()
            
    # Check if we have a config file
    if os.path.isfile(conf_file):
        print conf_file + " exists"
    else:
        print conf_file + " does not exist"
        exit(1)

    # Get Weather Underground values from config file
    conf = True
    config = ConfigParser.RawConfigParser(allow_no_value=True)
    config.read(conf_file)
     
    try:
        conf_key = config.get('WEATHER', 'apikey')
        conf_loc = config.get('WEATHER', 'location')
        conf_lang = config.get('WEATHER','language')
    except KeyError:
        conf = False
        print "Error: Config file variables not set"
        
    # Get the weather forecast for the location chosen
    url = ("http://api.wunderground.com/api/%s/forecast/q/%s.json" % (conf_key,conf_loc))

    if os.path.isfile(temp_file):
        # Get age of current weather data in cache
        age = time.time() - os.path.getmtime(temp_file)
        if age > weather_update_freq * 60:
            WUDownload()
    else:
        WUDownload()

def ReadCron(date_field):
    c=subprocess.Popen('crontab -l |tail -1',shell=True,stdout=subprocess.PIPE)   
    output = c.communicate()[0]
    if date_field == "hour":
       return int(output.split(" ")[1])
    elif date_field == "min":
       return int(output.split(" ")[0])

def buzzer(count):
    p.start(50)  # Duty cycle: 50%
    for i in range(count):
        for f in range(100, 2000, 100):
            p.ChangeFrequency(f)
	    time.sleep(0.2)
        for f in range(2000, 100, -100):
            p.ChangeFrequency(f)
	    time.sleep(0.2)
    p.stop()

# End of functions

lcd.clear()

while 1:
    curr_time = datetime.now().strftime('%a %d %b %H:%M\n')
    lcd.clear()

    if os.system('crontab -l>/dev/null') == 0:
      # Condition 1 - Alarm crontab entry exists. 
      # Display time and alarm time

      print "Alarm exists"
      
      # Get alarm time from cron
      min = ReadCron("min")
      hour = ReadCron ("hour")
      alarm_msg = ("Alarm - %02d:%02d" % (hour, min))

      # Display current time
      lcd.message(curr_time)
      lcd.message(alarm_msg)

      if os.path.isfile('ALARM_TRIGGERED'):
         # Condition 2 - Alarm crontab exists and alarm is currently triggered.
         # Display weather on LCD

         print "Alarm exists and is triggered"
         GetWeather()
         buzzer(2)
                  
         # Load cached weather from json file
         try:
             f = open(temp_file, "r")
         except IOError:
             fetch_error()
         data = json.load(f)
         f.close()

         for day in data['forecast']['simpleforecast']['forecastday']:
            if day['date']['weekday'] == time.strftime('%A'):
                weather = ("High:%sC Low:%sC" % (day['high']['celsius'], day['low']['celsius']))
                lcd.clear()
                lcd.message(curr_time)
                lcd.message(weather)
    else:
        lcd.clear()
        lcd.message(curr_time)

    sleep(10)
    lcd.clear()
