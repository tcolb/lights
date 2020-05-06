import paho.mqtt.client as mqtt
import threading

import time, board, busio, math
from adafruit_msa301 import MSA301, TapDuration
from adafruit_is31fl3731 import Matrix


# accel is in m/s^2
#VEC_MAG_MIN = 3.224212470756315
VEC_MAG_MIN = 11

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
        display.fill(5)
        time.sleep(0.2)
        display.fill(0)
    elif msg_str.startswith("tap"):
        display.fill(5)
        time.sleep(0.2)
        display.fill(0)
    else:
        print(msg.topic + " " + str(msg.payload))

def publish_test_message(client):
    client.publish(MQTT_PUB_PATH, "hello from python!", qos=0, retain=False)

def publish_accel(client, accel):
    client.publish(MQTT_PUB_PATH, "acc %d %d %d" % (accel[0], accel[1], accel[2]), qos=0, retain=False)

def publish_tap(client):
    client.publish(MQTT_PUB_PATH, "tap", qos=0, retain=False)

def calc_euc2_dist(u, v):
    return ((u[0] - v[0])**2 + (u[1] - v[1])**2 + (u[2] - v[2])**2)

def calc_vec_mag(v):
    return math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect(MQTT_SERVER, 1883, 60)

client.loop_start()


i2c = busio.I2C(board.SCL, board.SDA)
display = Matrix(i2c)
msa = MSA301(i2c)
msa.enable_tap_detection()


vcur = (0,0,0)
vprev = (0,0,0)
while(True):
    vcur = msa.acceleration
    print(calc_vec_mag(vcur))
    enough_accel = calc_vec_mag(vcur) > VEC_MAG_MIN

    if enough_accel:
        publish_accel(client, vcur)
        time.sleep(1) # delay for placing back down, maybe better way to do this

    if msa.tapped:
        publish_tap(client)

    vprev = vcur
    time.sleep(0.1)


client.loop_stop(force=False)
