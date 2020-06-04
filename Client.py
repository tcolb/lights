import boto3, os, random, time, board, busio, math, sys
from multiprocessing import Process, Value
from adafruit_msa301 import MSA301, TapDuration
from adafruit_is31fl3731 import CharlieBonnet
from enum import Enum
import awsconfig
import BonnetPatterns

if 'him' == sys.argv[1]:
    receive_suffix = "him"
    send_suffix = "her"
if 'her' == sys.argv[1]:
    receive_suffix = "her"
    send_suffix = "him"

HEALTHCHECK_THRESHOLD = 60
HEALTHCHECK_SEND_PERIOD = 30
MAX_BRIGHTNESS = 50
EASE_STEP = 0.05
EASE_WAIT = 0.01


#######
#
#   AWS Helpers
#
#######


def setup_awscli_vars():
    os.environ["AWS_ACCESS_KEY_ID"] = awsconfig.id
    os.environ["AWS_SECRET_ACCESS_KEY"] = awsconfig.key
    os.environ["AWS_DEFAULT_REGION"] = awsconfig.region

def send_message(tapped, accel):
    response = sqs.send_message(
        QueueUrl=send_url,
        DelaySeconds=0,
        MessageAttributes={
            'Tapped': {
                'DataType': 'String',
                'StringValue': str(tapped),
            },
            'x': {
                'DataType': 'Number',
                'StringValue': str(accel[0])
            },
            'y': {
                'DataType': 'Number',
                'StringValue': str(accel[1])
            },
            'z': {
                'DataType': 'Number',
                'StringValue': str(accel[2])
            },
            'HealthCheck': {
                'DataType': 'String',
                'StringValue': 'True',
            }
        },
        MessageBody=(
            "Light information from " + send_suffix
        )
    )
    print("[SEND] Sent message as", send_suffix + ":", response['MessageId'])      

def send_healthcheck(respond=False):
    response = sqs.send_message(
        QueueUrl=send_url,
        DelaySeconds=0,
        MessageAttributes={
            'HealthCheck': {
                'DataType': 'String',
                'StringValue': str(True),
            },
            'ShouldRespond': {
                'DataType': 'String',
                'StringValue': str(respond),
            },
        },
        MessageBody=(
            "Light information from " + send_suffix
        )
    )
    return "sent healthcheck as" + send_suffix + ":" + response['MessageId']

#######
#
#  CharliePlex Bonnet Helpers
#
#######


# input is from 0 - 1 representing percentage of animation
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
#  Child Processes
#
#######


def sending(v_HEALTHY, v_LAST_SENT_HEALTHCHECK):
    print("[SEND] Hello!")
    print("[SEND] Initial-" + send_healthcheck(True))
    v_LAST_SENT_HEALTHCHECK.value = time.monotonic()
    while True:
        cur_time = time.monotonic()
        if v_HEALTHY.value and v_LAST_SENT_HEALTHCHECK.value + HEALTHCHECK_SEND_PERIOD < cur_time:
            print("[SEND] Schedule-" + send_healthcheck(True))
            v_LAST_SENT_HEALTHCHECK.value = cur_time

        tapped = msa.tapped
        accel = msa.acceleration
        if tapped:
            send_message(tapped, accel)
            eased_matrix_pattern_blink(BonnetPatterns.outline)

def recving(v_HEALTHY, v_LAST_RECV_HEALTHCHECK, v_LAST_SENT_HEALTHCHECK):
    print("[RECV] Hello!")

    while True:
        response = sqs.receive_message(
            QueueUrl=receive_url,
            AttributeNames=[
                'SentTimestamp'
            ],
            MaxNumberOfMessages=1,
            MessageAttributeNames=[
                'All'
            ],
            VisibilityTimeout=0,
            WaitTimeSeconds=0
        )

        cur_time = time.monotonic()

        if 'Messages' in response:
            print("[RECV] Got message, handling...")
            message = response['Messages'][0]
            receipt_handle = message['ReceiptHandle']
            if 'HealthCheck' in message['MessageAttributes'] and message['MessageAttributes']['HealthCheck']['StringValue'] == "True":
                print("[RECV] Got a HealthCheck")
                if not v_HEALTHY.value:
                    eased_matrix_pattern_blink(BonnetPatterns.happy)
                v_HEALTHY.value = True 
                v_LAST_RECV_HEALTHCHECK.value = cur_time
                if 'ShouldRespond' in message['MessageAttributes'] and message['MessageAttributes']['ShouldRespond']['StringValue'] == "True":
                    print("[RECV] Response-" + send_healthcheck())
                    v_LAST_SENT_HEALTHCHECK.value = cur_time
            if 'Tapped' in message['MessageAttributes'] and message['MessageAttributes']['Tapped']['StringValue'] == "True":
                print("[RECV] Got trigger from message")
                eased_matrix_pattern_blink(random.choice(BonnetPatterns.recv_patterns))
            print("[RECV] Deleting recv message from queue...")
            delete = sqs.delete_message(
                    QueueUrl=receive_url,
                    ReceiptHandle = receipt_handle
            )

        if v_LAST_RECV_HEALTHCHECK.value + HEALTHCHECK_THRESHOLD < cur_time:
            v_HEALTHY.value = False

        if not v_HEALTHY.value:
            eased_matrix_pattern_blink(BonnetPatterns.sad)


#######
#
#  Main logic
#
#######


if __name__ == "__main__":
    # setup environment vars for awscli
    setup_awscli_vars()
    # setup aws sqs
    sqs = boto3.client('sqs')
    base_sqs_url = awsconfig.baseurl
    send_url = base_sqs_url + send_suffix
    receive_url = base_sqs_url + receive_suffix
    # setup bus devices
    i2c = busio.I2C(board.SCL, board.SDA)
    display = CharlieBonnet(i2c)
    msa = MSA301(i2c)
    msa.enable_tap_detection()
    eased_matrix_blink()

    print("Send url: " + send_url)
    print("Recv url: " + receive_url)

    # setup multi processing
    HEALTH = Value('b', False)
    LAST_RECV_HEALTHCHECK = Value('d', 0)
    LAST_SENT_HEALTHCHECK = Value('d', 0)
    send_proc = Process(target=sending, args=(HEALTH, LAST_SENT_HEALTHCHECK))
    recv_proc = Process(target=recving, args=(HEALTH, LAST_RECV_HEALTHCHECK, LAST_SENT_HEALTHCHECK))
    send_proc.start()
    recv_proc.start()
    send_proc.join()
    recv_proc.join()
