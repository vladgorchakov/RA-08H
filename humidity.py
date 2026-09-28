"""Safe MicroPython driver for DHT11 and DHT22 temperature/humidity sensors.

Features:
- Bounded retries with configurable delay
- Built-in rate limiting (minimum 2 seconds between physical measurements)
- Safe error handling without deadlocks or unhandled exceptions
- In-memory circular log for recent history
"""

import time

try:
    import machine
except ImportError:
    machine = None

try:
    import dht
except ImportError:
    dht = None

try:
    import ujson as json
except ImportError:
    import json

if not hasattr(time, 'ticks_ms'):
    time.ticks_ms = lambda: int(time.time() * 1000)
    time.ticks_diff = lambda a, b: a - b
    time.sleep_ms = lambda ms: time.sleep(ms / 1000.0)


class HumSensor:
    """Resilient DHT11/DHT22 temperature and humidity sensor interface."""

    MIN_SAMPLE_INTERVAL_MS = 2000  # DHT sensors require at least 2 sec between reads

    def __init__(self, pin: int, name: str = 'climate', place: str = 'node', is_dht22: bool = False):
        self.name = name
        self.place = place
        self.pin_num = pin
        self.is_dht22 = is_dht22

        self._hum = 0.0
        self._temp = 0.0
        self._last_read_time = -self.MIN_SAMPLE_INTERVAL_MS
        self._last_read_success = False
        self._history = []

        self._sensor = None
        if machine is not None and dht is not None:
            pin_obj = machine.Pin(pin)
            self._sensor = dht.DHT22(pin_obj) if is_dht22 else dht.DHT11(pin_obj)

    def measure(self, max_retries: int = 3, retry_delay_ms: int = 250) -> bool:
        """Reads sensor values with bounded retries. Respects sensor sampling rate limits."""
        now = time.ticks_ms()

        # If read recently, return cached measurement to prevent sensor overheating / bus error
        if time.ticks_diff(now, self._last_read_time) < self.MIN_SAMPLE_INTERVAL_MS:
            return self._last_read_success

        if self._sensor is None:
            return False

        for attempt in range(max_retries):
            try:
                self._sensor.measure()
                self._hum = float(self._sensor.humidity())
                self._temp = float(self._sensor.temperature())
                self._last_read_time = now
                self._last_read_success = True
                self._append_history(self._hum, self._temp)
                return True
            except Exception as err:
                if attempt < max_retries - 1:
                    time.sleep_ms(retry_delay_ms)

        print(f"[SENSOR] Warning: DHT read failed on GPIO {self.pin_num} after {max_retries} retries")
        self._last_read_success = False
        return False

    def _append_history(self, hum: float, temp: float, max_len: int = 50):
        if len(self._history) >= max_len:
            self._history.pop(0)
        self._history.append((hum, temp, time.ticks_ms()))

    @property
    def humidity(self) -> float:
        self.measure()
        return self._hum

    @property
    def temp(self) -> float:
        self.measure()
        return self._temp

    @property
    def humtemp(self) -> tuple:
        """Returns (humidity, temperature) safely."""
        self.measure()
        return int(self._hum), int(self._temp)

    @property
    def is_valid(self) -> bool:
        return self._last_read_success

    def to_json(self) -> str:
        self.measure()
        payload = {
            "name": self.name,
            "place": self.place,
            "temp": self._temp,
            "humidity": self._hum,
            "valid": self._last_read_success
        }
        return json.dumps(payload)

    def humtemp_json(self) -> str:
        """Backward-compatible helper."""
        return self.to_json()

    @property
    def log(self) -> list:
        return self._history


# Alias for clean naming
DHTSensor = HumSensor
