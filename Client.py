import os, random, time, board, busio, math, sys
from adafruit_msa301 import MSA301, TapDuration
from adafruit_is31fl3731 import CharlieBonnet
import paho.mqtt.client as mqtt

import Config
import BonnetPatterns

if 'him' == sys.argv[1]:
    receive_suffix = "him"
    send_suffix = "her"
if 'her' == sys.argv[1]:
    receive_suffix = "her"
    send_suffix = "him"

MQTT_IP = Config.mqtt_ip
LIGHT_IDENTIFIER = Config.light_identifier
HEALTHCHECK_IDENTIFIER = Config.healthcheck_identifier
HEALTHCHECK_THRESHOLD = Config.healthcheck_threshold
HEALTHCHECK_SEND_PERIOD = Config.healthcheck_send_period
MAX_BRIGHTNESS = Config.max_brightness
UNHEALTHY_BLINK_COOLDOWN = Config.unhealthy_blink_cooldown
EASE_STEP = Config.ease_step
EASE_WAIT = Config.ease_wait


#######
#
#  CharliePlex Bonnet Helpers
#
#######


def ease_expo(x):
    if x == 0:
        return 0
    else:
        return 2 ** (10 * x - 10)

def generic_ease_in(ease_func, callback):
    progress = 0.0
    while progress <= 1:
        callback(int(MAX_BRIGHTNESS * ease_func(progress)))
        progress += EASE_STEP
        time.sleep(EASE_WAIT)

def generic_ease_out(ease_func, callback):
    progress = 1.0
    while True:
        if progress <= 0:
            callback(0)
            return
        callback(int(MAX_BRIGHTNESS * ease_func(progress)))
        progress -= EASE_STEP
        time.sleep(EASE_WAIT)

def ease_in_matrix():
    generic_ease_in(ease_expo, lambda x: display.fill(x))

def ease_out_matrix():
    generic_ease_out(ease_expo, lambda x: display.fill(x))

def eased_matrix_blink():
    ease_in_matrix()
    ease_out_matrix()

def matrix_pattern_callback(strength, pattern):
    width = 16
    height = 8
    for x in range(width):
        for y in range(height):
            if pattern[(y * width) + x] == 1:
                display.pixel(x, y, strength)

def eased_matrix_pattern_blink(pattern):
    generic_ease_in(ease_expo, lambda x: matrix_pattern_callback(x, pattern))
    generic_ease_out(ease_expo, lambda x: matrix_pattern_callback(x, pattern))


#######
#
#  MQTT Helpers
#
#######


def send_tapped():
    client.publish(send_path, LIGHT_IDENTIFIER, qos=0, retain=False)
    print("[SEND] Sent message as", send_suffix)      

def send_healthcheck(respond=False):
    client.publish(send_path, HEALTHCHECK_IDENTIFIER + " " + str(respond), qos=0, retain=False)
    return "sent healthcheck as" + send_suffix

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT server with result " + str(rc))
    client.subscribe(receive_path)
    print("Subscribed to MQTT path:", receive_path)

def on_message(client, userdata, msg):
    try:
        cur_time = time.monotonic()
        msg_str = msg.payload.decode('ascii')
        msg_args = msg_str.split()
        print("Got message with data:", msg_str)
        if msg_args[0] == HEALTHCHECK_IDENTIFIER:
            print("Got healthcheck")
            healthy = True
            last_got_healthcheck = cur_time
            if msg_args[1] == "True":
                print("Response-" + send_healthcheck())
                last_sent_healthcheck = cur_time
        if msg_args[0] == LIGHT_IDENTIFIER:
            print("Got light")
            eased_matrix_pattern_blink(random.choice(BonnetPatterns.recv_patterns))
        if last_got_healthcheck + HEALTHCHECK_THRESHOLD < cur_time:
            healthy = false
        if not healthy:
            eased_matrix_pattern_blink(BonnetPatterns.sad)
    except:
        print("Exception on getting message.")

def send_loop():
    cur_time = time.monotonic()
    print("Initial-" + send_healthcheck(True))
    last_sent_healthcheck = cur_time
    last_unhealthy_blink = cur_time
    while True:
        cur_time = time.monotonic()
        if not healthy and cur_time > last_unhealthy_blink + UNHEALTHY_BLINK_COOLDOWN:
            eased_matrix_pattern_blink(BonnetPatterns.sad)
            last_unhealthy_blink = time.monotonic()
        if healthy and last_sent_healthcheck + HEALTHCHECK_SEND_PERIOD < cur_time:
            print("Schedule-" + send_healthcheck(False))
            last_sent_healthcheck = cur_time
        if msa.tapped:
            try:
                send_tapped()
                eased_matrix_pattern_blink(BonnetPatterns.outline)
            except:
                print("Exception on sending message.")


#######
#
#  Main logic
#
#######


if __name__ == "__main__":
    # setup bus devices
    i2c = busio.I2C(board.SCL, board.SDA)
    display = CharlieBonnet(i2c)
    msa = MSA301(i2c)
    msa.enable_tap_detection()
    eased_matrix_blink()
    # setup state-vars
    healthy = False
    last_got_healthcheck = 0
    last_sent_healthcheck = 0
    last_unhealthy_blink = 0
    # setup mqtt paths
    send_path = Config.mqtt_base_path + send_suffix
    receive_path = Config.mqtt_base_path + receive_suffix
    client = mqtt.Client()
    client.on_connect = on_connect
    client.username_pw_set(Config.mqtt_username, Config.mqtt_password)
    client.connect(MQTT_IP, 1883, 60)
    # start loops
    client.loop_start()
    send_loop()
    client.loop_stop(force=True)
