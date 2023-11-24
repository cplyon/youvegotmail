#! /usr/bin/env python3

import json
import logging
import os
import smtplib
import ssl
import time

from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText
from email.utils import COMMASPACE, formatdate
from io import StringIO
from socket import gaierror
from picamera import PiCamera
from RPi import GPIO


class YouveGotMail:
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
        logging.warning("Door opened")

    def wait_for_switch_close(self):
        GPIO.wait_for_edge(self.switch_pin, GPIO.FALLING)
        logging.warning("Door closed")

    def take_photo(self) -> str:
        image_path = os.path.join(
            self.image_location,
            f"image_{datetime.now().strftime('%b_%d_%Y_%H_%M_%S')}.jpg",
        )
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

        with open(attachment_path, "rb") as image_file:
            img = MIMEImage(image_file.read(), "jpg")
            img.add_header("Content-ID", "<image>")
            img.add_header("Content-Disposition", "inline", filename="image.jpg")
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


def main():
    ygm = YouveGotMail()
    with open(CONFIG_PATH, "r", encoding="utf8") as conf:
        ygm.read_config(conf)
    ygm.setup_gpio()

    while True:
        ygm.wait_for_switch_open()
        time.sleep(DOOR_SLEEP_SECONDS)
        image = ygm.take_photo()
        logging.debug(image)
        message = ygm.compose_email(image)

        retry_counter = 0
        mail_sent = False
        while not mail_sent:
            try:
                ygm.send_email(message)
            except (gaierror, smtplib.SMTPServerDisconnected, OSError) as error:
                logging.debug(error)
                if retry_counter >= MAX_RETRIES:
                    logging.debug("%s retries reached, abort sending mail", MAX_RETRIES)
                    break
                logging.debug("Mail failed to send, retrying in %s", MAIL_SEND_SLEEP_SECONDS)
                time.sleep(MAIL_SEND_SLEEP_SECONDS)
                retry_counter += 1
            else:
                mail_sent = True

        ygm.wait_for_switch_close()


if __name__ == "__main__":
    CONFIG_PATH = "./config.json"
    MAIL_SEND_SLEEP_SECONDS = 60
    DOOR_SLEEP_SECONDS = 10
    MAX_RETRIES = 2
    LOG_NAME = "ygm.log"

    logging.basicConfig(filename=LOG_NAME,
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)

    main()
