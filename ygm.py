#! /usr/bin/env python3

from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from io import StringIO
from picamera import PiCamera

import json
import os
import smtplib
import ssl
import time
import RPi.GPIO as GPIO


class YouveGotMail():
    def __init__(self):
        self.account = None
        self.password = None
        self.port = None
        self.server = None
        self.to_addresses = []
        self.from_address = None
        self.subject = None
        self.message = None
        self.brightness = None
        self.switch_pin = None
        self.image_location = None

    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.switch_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def wait_for_switch_open(self):
        GPIO.wait_for_edge(self.switch_pin, GPIO.RISING)

    def take_photo(self) -> str:
        image_path = os.path.join(self.image_location,
                                  "image_{}.jpg".format(
                                    datetime.now().strftime(
                                        "%b_%d_%Y_%H_%M_%S")))
        with PiCamera() as camera:
            camera.brightness = self.brightness
            camera.capture(image_path)
        return image_path

    def compose_email(self, attachment_path: str) -> str:
        msg = MIMEMultipart()
        msg["From"] = self.from_address
        msg["To"] = COMMASPACE.join(self.to_addresses)
        msg["Date"] = formatdate(localtime=True)
        msg["Subject"] = self.subject
        msg.attach(MIMEText(self.message))

        with open(attachment_path, 'rb') as f:
            img = MIMEImage(f.read(), "jpg")
            img.add_header('Content-ID', '<image>')
            img.add_header('Content-Disposition', 'inline', filename='image.jpg')
            msg.attach(img)

        return msg.as_string()

    def send_email(self, msg: str) -> None:
        context = ssl.create_default_context()
        with smtplib.SMTP(self.server, self.port) as server:
            server.starttls(context=context)
            server.login(self.account, self.password)
            server.sendmail(self.from_address, self.to_addresses, msg)

    def read_config(self, file_stream: StringIO):
        config = json.load(file_stream)
        self.account = config["account"]
        self.password = config["password"]
        self.server = config["server"]
        self.port = config["port"]
        self.from_address = config["from"]
        self.to_addresses = config["to"]
        self.subject = config["subject"]
        self.message = config["message"]
        self.brightness = config["brightness"]
        self.switch_pin = config["switch_pin"]
        self.image_location = config["image_location"]


if __name__ == "__main__":

    CONFIG_PATH = "./config.json"
    ygm = YouveGotMail()
    with open(CONFIG_PATH) as f:
        ygm.read_config(f)
    ygm.setup_gpio()

    while True:
        ygm.wait_for_switch_open()
        print("Door open!")
        time.sleep(10)
        image_path = ygm.take_photo()
        print(image_path)
        msg = ygm.compose_email(image_path)
        ygm.send_email(msg)
