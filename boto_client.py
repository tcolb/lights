import boto3, os
from multiprocessing import Process
import awsconfig

import time, board, busio, math
from adafruit_msa301 import MSA301, TapDuration
from adafruit_is31fl3731 import CharlieBonnet


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
            }
        },
        MessageBody=(
            "Light information from " + send_suffix
        )
    )
    print("[SEND] Sent message:", response['MessageId'])      

# input is from 0 - 1 representing percentage of animation
def ease_in_expo(x):
    if x == 0:
        return 0
    else:
        return 2 ** (10 * x - 10)

max_brightness = 100
ease_step = 0.05
ease_wait = 0.01
def ease_in_matrix(ease_func):
    progress = 0.0
    while progress <= 1:
        display.fill(int(max_brightness * ease_func(progress)))
        progress += ease_step
        time.sleep(ease_wait)

def ease_out_matrix(ease_func):
    progress = 1.0
    while True:
        if progress <= 0:
            display.fill(0)
            return
        display.fill(int(max_brightness * ease_func(progress)))
        progress -= ease_step
        time.sleep(ease_wait)

def eased_matrix_blink():
    ease_in_matrix(ease_in_expo)
    ease_out_matrix(ease_in_expo)

def sending():
    print("[SEND] Hello!")
    accel_threshold = 10
    while True:
        tapped = msa.tapped
        accel = msa.acceleration
        #if sum(accel) > accel_threshold or tapped:
        if tapped:
            send_message(tapped, accel)

def recving():
    print("[RECV] Hello!")
    global current_recvs
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

        if 'Messages' in response:
            print("[RECV] Got message, handling...")
            message = response['Messages'][0]
            receipt_handle = message['ReceiptHandle']
            if bool(message['MessageAttributes']['Tapped']['StringValue']):
                print("[RECV] Got trigger from message")
                eased_matrix_blink()
            else:
                print("[RECV] Did not receive trigger")
            print("[RECV] Deleting recv message from queue...")
            delete = sqs.delete_message(
                    QueueUrl=receive_url,
                    ReceiptHandle = receipt_handle
            )

def setup_awscli_vars():
    os.environ["AWS_ACCESS_KEY_ID"] = awsconfig.id
    os.environ["AWS_SECRET_ACCESS_KEY"] = awsconfig.key
    os.environ["AWS_DEFAULT_REGION"] = awsconfig.region


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
    # setup processes
    send_proc = Process(target=sending)
    recv_proc = Process(target=recving)
    send_proc.start()
    recv_proc.start()
    send_proc.join()
    recv_proc.join()
