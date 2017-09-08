# Author: Michael Akayan

import os, random
import redis
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from time import time, sleep
from boto3 import client, resource 

r = redis.Redis(host='127.0.0.1', port='6379',charset="utf-8", decode_responses=True) 

# Initialize the Flask application
app = Flask(__name__)

# Setup AWS variables
# Ensure C:\Users\<username>\.aws\credientials and C:\Users\<username>\.aws\config are created and defined

rk = client('rekognition')
conn = client('s3')
s3 = resource('s3')

# Get a handle on the photo and read it
bucket = "akayan-images"
photo_list = []

def Rekognise(photo_list):
    print "Running photo regognition"
    # Choose a random photo
    photo = random.choice(photo_list)
    
    # Read photo from AWS    
    image = s3.Object(bucket, photo)
    img_data = image.get()['Body'].read()

    ### Send it to Rekognition and detect characteristics in photo  
    results = rk.detect_labels(
    Image={'Bytes': img_data},
    MaxLabels=3,
    MinConfidence=80)
    
    return photo, results["Labels"]

def GetPhotos():
    print "Grabbing list of images for bucket: " + bucket
    for key in conn.list_objects(Bucket=bucket)['Contents']:
        image_key = key['Key']
        photo_list.append(image_key)
    return ()

@app.route('/')
def main():
    image_data = Rekognise(photo_list)
    
    return (render_template('main.html', filename=image_data[0], \
                            conf_0=str(int(image_data[1][0]['Confidence'])), label_0=image_data[1][0]['Name'],
                            conf_1=str(int(image_data[1][1]['Confidence'])), label_1=image_data[1][1]['Name']))

@app.route('/potd/<filename>')
def send_potd(filename):
    url = "https://akayan-images.s3-us-west-2.amazonaws.com/" + filename
    return redirect(url)
    
@app.route('/save.html', methods=['GET', 'POST'])
def save():
    start_page = """<html>
        <head>
        <meta id="meta" name="viewport"
        content="width=device-width; initial-scale=1.0" />
        <title>Alarm Clock</title>
        <style>
        h1 {text-align:center;}
        p {text-align:center;}
        </style>
        <meta name="HandheldFriendly" content="true">
        </head><body>"""

    if request.form['submit'] == 'Set Alarm':
        alarm_time=request.form['alarm_time']
        store = 'check' in request.form
       
        if not alarm_time:
            return redirect('/')
        else:
            hour=alarm_time.split(":")[0]
            minute=alarm_time.split(":")[1]

            ## Add Cron entry
            updatecron(hour,minute)
            
            ## Store alarm record in redis
            if store:
                print "Storing favourite alarm in redis"
                StoreRecord(hour,minute)
            
            mid_page = "<h1>Alarm time of """ + alarm_time + " selected</h1>"
            end_page = """<form action="/">
                        <p><input type="submit" value="Back to Main" /></p>
                        </form></body></html>"""
            full_page = start_page + mid_page + end_page

            return full_page
    elif request.form['submit'] == 'Cancel Alarm':
        print "Removing crontab entries"
        os.system("crontab -r")

        print "Removing ALARM"
        if os.path.isfile("ALARM_TRIGGERED"):
            os.system("rm ALARM_TRIGGERED")
        else:
            print "Alarm is not triggered"

        mid_page= "<h1>Alarm cancelled</h1>"
        end_page = """<form action="/">
                      <p><input type="submit" value="Back to Main" /></p>
                      </form></body></html>"""
        full_page = start_page + mid_page + end_page

        return full_page

        
## Store alarm record in Redis (future functionality)
def StoreRecord(hour,minute):
    Counter = r.incr('counter_alarm')
    newalarm = 'alarm' + str(Counter).zfill(3)
    
    r.hmset(newalarm,{'hour':hour, 'minute':minute})

    print "Dumping favourite alarm records from Redis"
    for alarm in sorted(r.keys('alarm*')):
        print "Alarm Hour", r.hget(alarm,'hour')
        print "Alarm Minute", r.hget(alarm,'minute')
     
    return ""

## Update cronttab for pi user
def updatecron(hour,minute):
    crontab=minute + " " + hour + " * * * touch ~/projects/clock/ALARM_TRIGGERED"
    CMD = "echo \"" + crontab + "\"|crontab -"
    os.system(CMD) 

### End of functions

# Grab list of images at AWS and store in a list
GetPhotos()

if __name__ == "__main__":
	app.run(debug=False, host='0.0.0.0', \
                port=int(os.getenv('PORT', '5000')), threaded=True)
