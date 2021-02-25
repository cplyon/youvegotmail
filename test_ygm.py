#!/usr/bin/env python3

import sys
import unittest

from io import BytesIO, StringIO
from json import JSONDecodeError
from unittest.mock import MagicMock

sys.modules["picamera"] = MagicMock()
sys.modules["RPi"] = MagicMock()
sys.modules["RPi.GPIO"] = MagicMock()
from ygm import YouveGotMail


class YGMTest(unittest.TestCase):

    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    def test_read_config_positive(self) -> None:
        ACCOUNT = "chris@example.com"
        PASSWORD = "p@ssw0rd!"
        PORT = "1919"
        SERVER = "smpt.example.com"
        TO = "['matt@example.com']"
        FROM = "chris@example.com"
        SUBJECT = "Hi there!"
        MESSAGE = "Call me tomorrow."
        SWITCH_PIN = "1"
        IMAGE_LOCATION = "/home/chris/"

        with StringIO() as config:
            config.write('{\n')
            config.write('"account": "{}",\n'.format(ACCOUNT))
            config.write('"password": "{}",\n'.format(PASSWORD))
            config.write('"port": "{}",\n'.format(PORT))
            config.write('"server": "{}",\n'.format(SERVER))
            config.write('"to": "{}",\n'.format(TO))
            config.write('"from": "{}",\n'.format(FROM))
            config.write('"subject": "{}",\n'.format(SUBJECT))
            config.write('"message": "{}",\n'.format(MESSAGE))
            config.write('"switch_pin": "{}",\n'.format(SWITCH_PIN))
            config.write('"image_location": "{}"\n'.format(IMAGE_LOCATION))
            config.write('}\n')
            config.seek(0)

            ygm = YouveGotMail()
            ygm.read_config(config)
        self.assertEqual(ygm.account, ACCOUNT)
        self.assertEqual(ygm.password, PASSWORD)
        self.assertEqual(ygm.port, PORT)
        self.assertEqual(ygm.server, SERVER)
        self.assertEqual(ygm.to_addresses, TO)
        self.assertEqual(ygm.from_address, FROM)
        self.assertEqual(ygm.subject, SUBJECT)
        self.assertEqual(ygm.message, MESSAGE)
        self.assertEqual(ygm.switch_pin, SWITCH_PIN)
        self.assertEqual(ygm.image_location, IMAGE_LOCATION)

    def test_read_config_negative(self) -> None:
        config = StringIO()
        config.write('{\n')
        config.write('}\n')
        ygm = YouveGotMail()
        with self.assertRaises(JSONDecodeError):
            ygm.read_config(config)

