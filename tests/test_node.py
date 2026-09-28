"""Automated Unit Tests for ESP32 LoRaWAN Node codebase.

Can be run on any PC with standard Python 3:
    python3 tests/test_node.py
"""

import sys
import unittest

# Ensure root project directory is on sys.path
sys.path.insert(0, ".")

import config
from cayenne import LPPcodec, CayenneLPPType
from button import Button
from humidity import HumSensor
from ra08h import RA08H


class TestCayenneLPP(unittest.TestCase):
    def setUp(self):
        self.codec = LPPcodec()

    def test_temperature_positive(self):
        # 25.5 degC -> raw 255 -> 0x00FF
        hex_data = self.codec.encode_temp(25.5, channel=1)
        self.assertEqual(hex_data, "016700FF")

    def test_temperature_negative(self):
        # -5.2 degC -> raw -52 -> 0xFFCC (two's complement 16-bit)
        hex_data = self.codec.encode_temp(-5.2, channel=1)
        self.assertEqual(hex_data, "0167FFCC")

    def test_humidity(self):
        # 50.0 % -> raw 100 -> 0x64
        hex_data = self.codec.encode_humidity(50.0, channel=1)
        self.assertEqual(hex_data, "016864")

    def test_humtemp_combined(self):
        # Humidity 80% (160 = 0xA0), Temp -10.5C (-105 = 0xFF97)
        hex_data = self.codec.encode_humtemp((80, -10.5), channel=1)
        self.assertEqual(hex_data, "0168A00167FF97")

    def test_decoder_roundtrip(self):
        self.codec.reset()
        self.codec.add_humidity(62.5, channel=1)
        self.codec.add_temperature(21.3, channel=1)
        self.codec.add_voltage(3.65, channel=1)
        self.codec.add_barometer(1013.2, channel=1)

        raw_hex = self.codec.to_hex()
        decoded = LPPcodec.decode(raw_hex)

        self.assertEqual(len(decoded), 4)
        self.assertAlmostEqual(decoded[0]["value"], 62.5, places=1)
        self.assertAlmostEqual(decoded[1]["value"], 21.3, places=1)
        self.assertAlmostEqual(decoded[2]["value"], 3.65, places=2)
        self.assertAlmostEqual(decoded[3]["value"], 1013.2, places=1)


class TestRA08HParser(unittest.TestCase):
    class MockUART:
        def __init__(self, script):
            self.script = script
            self.rx_buf = []

        def any(self):
            return len(self.rx_buf)

        def readline(self):
            if self.rx_buf:
                return self.rx_buf.pop(0).encode('utf-8')
            return b''

        def read(self):
            self.rx_buf.clear()
            return b''

        def write(self, data):
            cmd = data.decode('utf-8') if isinstance(data, bytes) else str(data)
            for pattern, responses in self.script.items():
                if pattern in cmd:
                    self.rx_buf.extend(responses)
                    break

    def test_join_success(self):
        script = {
            "AT+CJOIN": [
                "OK\r\n",
                "+JOIN:NetID 000001,DevAddr 01234567\r\n",
                "+CJOIN:OK\r\n"
            ]
        }
        lora = RA08H(self.MockUART(script), debug=False)
        success, info = lora.join(timeout_ms=500)
        self.assertTrue(success)
        self.assertEqual(info["STATUS"], "CJOIN:OK")
        self.assertTrue(lora.is_join)

    def test_send_telemetry_confirmed(self):
        script = {
            "AT+DTRX": [
                "OK+SEND:7\r\n",
                "tx_freq:868100000,rx_freq:868100000\r\n",
                "rssi:-72,snr:8,daterate:5\r\n",
                "OK+SENT:1\r\n"
            ]
        }
        lora = RA08H(self.MockUART(script), debug=False)
        success, log = lora.send_data("016864016700FF", confirmed=True, timeout_ms=500)
        self.assertTrue(success)
        self.assertEqual(log["received_data"]["rssi"], "-72")
        self.assertEqual(log["received_data"]["snr"], "8")
        self.assertEqual(log["received_data"]["daterate"], "5")


class TestSensorResilience(unittest.TestCase):
    def test_sensor_init_without_crash(self):
        sensor = HumSensor(18, name="climate_test")
        self.assertEqual(sensor.name, "climate_test")
        hum, temp = sensor.humtemp
        self.assertIsInstance(hum, int)
        self.assertIsInstance(temp, int)


if __name__ == "__main__":
    unittest.main()
