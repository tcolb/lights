import boto3
import threading

import time, board, busio, math
from adafruit_msa301 import MSA301, TapDuration
from adafruit_is31fl3731 import Matrix


DEBUG = True
HIMST = True

if DEBUG:
    receive_suffix = "him"
    send_suffix = "him"
elif HIMST:
    receive_suffix = "him"
    send_suffix = "her"
else:
    receive_suffix = "her"
    send_suffix = "him"


def handle_message(msg):
    if msg.startswith("acc"):
        eased_matrix_blink()
    elif msg.startswith("tap"):
        easeMatrixBlink()

def recving():
    response = sqs.receieve_message(
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

    message = response['Messages'][0]
    receipt_handle = message['ReceiptHandle']

    handle_message(message)

    sqs.delete_message(
            QueueUrl=receieve_url,
            ReceiptHandle = receipt_handle
    )


def send_message(tapped, accel):
    response = sqs.send_message(
        QueueUrl=send_url,
        DelaySeconds=0,
        MessageAttributes={
            'Tapped': {
                'DataType': 'Binary',
                'BinaryValue': int(tapped == True),
            },
            'Acceleration': {
                'NumberListValues': [
                    accel.x,
                    accel.y,
                    accel.z,
                ]
            }
        },
        MessageBody=(
            "Light information from " + send_suffix
        )
    )
    print("Sent message:", response['MessageId'])      

# input is from 0 - 1 representing percentage of animation
def ease_in_expo(x):
    if x == 0:
        return 0
    else:
        return 2 ** (10 * x - 10)

maxBrightness = 100
easeStep = 0.05
def ease_in_matrix(easeFunc):
    progress = 0.0
    while progress <= 1:
        display.fill(maxBrightness * easeFunc(progress))
        progress += easeStep

def ease_out_matrix(easeFunc):
    progress = 1.0
    while True:
        if progress <= 0:
            display.fill(0)
            return
        display.fill(maxBrightness * easeFunc(progress))
        progress -= easeStep

def eased_matrix_blink():
    ease_in_matrix(ease_in_expo)
    ease_out_matrix(ease_in_expo)

def sending():
    accel_threshold = 10
    while True:
        tapped = msa.tapped
        accel = msa.acceleration
        if msa.acceleration > accel_threshold:
            send_message(tapped, accel)
            time.sleep(1) # delay for placing back down, maybe better way to do this

def __main__():
    # setup aws sqs
    sqs = boto3.client('sqs')
    base_sqs_url = "https://sqs.us-west-1.amazonaws.com/197553793325/light_"
    send_url = base_sqs_url + send_suffix
    receive_url = base_sqs_url + receive_suffix

    # setup bus devices
    i2c = busio.I2C(board.SCL, board.SDA)
    display = Matrix(i2c)
    #msa = MSA301(i2c)
    #msa.enable_tap_detection()

    # setup threads
    send_thread = threading.Thread(target=sending)
    recv_thread = threading.Thread(target=recving)

    send_thread.start()
    recv_thread.start()

    send_thread.join()
    recv_thread.join()
