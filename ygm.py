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
        self.config = {}
        logging.info("Starting up")

    def setup_gpio(self):
        logging.info("Setting up GPIO")
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.config["switch_pin"], GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def wait_for_switch_open(self):
        GPIO.wait_for_edge(self.config["switch_pin"], GPIO.RISING)
        logging.debug("Door opened")

    def wait_for_switch_close(self):
        GPIO.wait_for_edge(self.config["switch_pin"], GPIO.FALLING)
        logging.debug("Door closed")

    def take_photo(self) -> str:
        image_path = os.path.join(
            self.config["image_location"],
            f"image_{datetime.now().strftime('%b_%d_%Y_%H_%M_%S')}.jpg",
        )
        logging.info("Taking photo")
        with PiCamera() as camera:
            camera.brightness = self.config["brightness"]
            logging.debug("Saving photo to %s", image_path)
            camera.capture(image_path)
        return image_path

    def compose_email(self, attachment_path: str) -> str:
        msg = MIMEMultipart()
        msg["From"] = self.config["from_address"]
        msg["To"] = COMMASPACE.join(self.config["to_addresses"])
        msg["Date"] = formatdate(localtime=True)
        msg["Subject"] = self.config["subject"]
        msg.attach(MIMEText(self.config["message"]))

        with open(attachment_path, "rb") as image_file:
            img = MIMEImage(image_file.read(), "jpg")
        img.add_header("Content-ID", "<image>")
        img.add_header("Content-Disposition", "inline", filename="image.jpg")
        msg.attach(img)

        return msg.as_string()

    def send_email(self, msg: str):
        logging.info("Sending email")
        context = ssl.create_default_context()
        with smtplib.SMTP(self.config["server"], self.config["port"]) as server:
            server.starttls(context=context)
            server.login(self.config["account"], self.config["password"])
            server.sendmail(self.config["from_address"], self.config["to_addresses"], msg)

    def read_config(self, file_stream: StringIO):
        logging.info("Reading config")
        self.config = json.load(file_stream)


def main():
    ygm = YouveGotMail()
    with open(CONFIG_PATH, "r", encoding="utf8") as conf:
        ygm.read_config(conf)
    ygm.setup_gpio()

    while True:
        ygm.wait_for_switch_open()
        time.sleep(DOOR_SLEEP_SECONDS)
        image = ygm.take_photo()
        message = ygm.compose_email(image)

        retry_counter = 0
        mail_sent = False
        while not mail_sent:
            try:
                ygm.send_email(message)
            except (gaierror, smtplib.SMTPServerDisconnected, OSError) as error:
                logging.error(error)
                if retry_counter >= MAX_RETRIES:
                    logging.error("%s retries reached, abort sending mail", MAX_RETRIES)
                    break
                logging.warning("Mail failed to send, retrying in %s", MAIL_SEND_SLEEP_SECONDS)
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
    LOG_FILE_NAME = "ygm.log"

    logging.basicConfig(filename=LOG_FILE_NAME,
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.INFO)

    main()
