import paho.mqtt.client as mqtt
import threading

import time, board, busio, math
from adafruit_msa301 import MSA301, TapDuration
from adafruit_is31fl3731 import Matrix

# accel is in m/s^2

DEBUG = True
HIMST = True

if DEBUG:
    SUB_GEN = "him"
    PUB_GEN = "him"
elif HIMST:
    SUB_GEN = "him"
    PUB_GEN = "her"
else:
    SUB_GEN = "her"
    PUB_GEN = "him"

MQTT_SERVER = "44.227.84.62" # amazon ec2 instance elastic ip
MQTT_SUB_PATH = "lovelight/from" + SUB_GEN
MQTT_PUB_PATH = "lovelight/from" + PUB_GEN

def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe(MQTT_SUB_PATH)

def on_message(client, userdata, msg):
    msg_str = msg.payload.decode('ascii')
    print("debug", msg_str)
    if msg_str.startswith("acc"):
        easedMatrixBlink()
    elif msg_str.startswith("tap"):
        easeMatrixBlink()
    else:
        print(msg.topic + " " + str(msg.payload))
    time.sleep(0.5)

def publishTestMessage(client):
    client.publish(MQTT_PUB_PATH, "hello from python!", qos=0, retain=False)

def publishAccel(client, accel):
    client.publish(MQTT_PUB_PATH, "acc %d %d %d" % (accel[0], accel[1], accel[2]), qos=0, retain=False)

def publishTap(client):
    client.publish(MQTT_PUB_PATH, "tap", qos=0, retain=False)

# input is from 0 - 1 representing percentage of animation
def easeInExpo(x):
    if x == 0:
        return 0
    else:
        return 2 ** (10 * x - 10)

maxBrightness = 100
easeStep = 0.05
def easeInMatrix(easeFunc):
    progress = 0.0
    while progress <= 1:
        display.fill(maxBrightness * easeFunc(progress))
        progress += easeStep

def easeOutMatrix(easeFunc):
    progress = 1.0
    while True:
        if progress <= 0:
            display.fill(0)
            return
        display.fill(maxBrightness * easeFunc(progress))
        progress -= easeStep

def easedMatrixBlink():
    easeInMatrix(easeInExpo)
    easeOutMatrix(easeInExpo)

# setup mqtt
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_SERVER, 1883, 60)
client.loop_start()

# init matrix and acceleromterer
i2c = busio.I2C(board.SCL, board.SDA)
display = Matrix(i2c)
msa = MSA301(i2c)
msa.enable_tap_detection()

# main loop
accel_threshold = 10
while(True):
    accel = msa.acceleration
    
    if accel > accel_threshold:
        publish_accel(client, vcur)
        time.sleep(1) # delay for placing back down, maybe better way to do this

    if msa.tapped:
        publish_tap(client)

    time.sleep(0.1)

client.loop_stop(force=False)
