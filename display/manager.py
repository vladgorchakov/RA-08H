"""High-level OLED display manager for ESP32 LoRaWAN Node.

Handles:
- Screen page rendering (Joining, Telemetry, Notification)
- Energy saving: automatic screen timeout and sleep
- Graceful degradation if OLED is absent or disconnected
"""

import time
from .ssd1306 import SSD1306_I2C

if not hasattr(time, 'ticks_ms'):
    time.ticks_ms = lambda: int(time.time() * 1000)
    time.ticks_diff = lambda a, b: a - b


class DisplayManager:
    """Manages OLED presentation, layout, and automatic power saving."""

    def __init__(self, i2c, width: int = 128, height: int = 64, timeout_sec: int = 30):
        self.oled = None
        self.timeout_sec = timeout_sec
        self.last_activity = time.ticks_ms()
        self.is_powered_on = True

        if i2c is not None:
            try:
                self.oled = SSD1306_I2C(width, height, i2c)
                self.oled.fill(0)
                self.oled.show()
            except Exception as err:
                print(f"[DISPLAY] Init warning: {err}")
                self.oled = None

    def wake(self):
        """Wakes the OLED screen from power save."""
        self.last_activity = time.ticks_ms()
        if self.oled and not self.is_powered_on:
            try:
                self.oled.poweron()
                self.is_powered_on = True
            except Exception:
                pass

    def check_power_timeout(self):
        """Puts screen to sleep if inactive for longer than timeout_sec."""
        if self.timeout_sec > 0 and self.is_powered_on and self.oled:
            if time.ticks_diff(time.ticks_ms(), self.last_activity) > (self.timeout_sec * 1000):
                try:
                    self.oled.poweroff()
                    self.is_powered_on = False
                    print("[DISPLAY] Screen powered off (sleep mode)")
                except Exception:
                    pass

    def show_splash(self, title: str = "LoRaWAN Node", subtitle: str = "AI-Thinker RA08H"):
        """Displays boot splash screen."""
        if not self.oled:
            return
        self.wake()
        try:
            self.oled.fill(0)
            self.oled.text("=== EMBEDDED ===", 0, 10)
            self.oled.text(title, 0, 26)
            self.oled.text(subtitle, 0, 42)
            self.oled.show()
        except Exception:
            pass

    def show_join(self, attempt: int, max_attempts: int, status: str, msg: str):
        """Displays network join progress."""
        if not self.oled:
            return
        self.wake()
        try:
            self.oled.fill(0)
            self.oled.text("LoRaWAN JOIN", 0, 0)
            self.oled.text(f"Attempt: {attempt}/{max_attempts}", 0, 18)
            self.oled.text(f"ST:  {status}", 0, 34)
            self.oled.text(f"MSG: {msg[:14]}", 0, 48)
            self.oled.show()
        except Exception:
            pass

    def show_telemetry(self, packet_id: int, success: bool, log: dict, hum: float, temp: float, dr: int):
        """Displays transmission status, sensor readings, and RF link metrics."""
        if not self.oled or not self.is_powered_on:
            return
        try:
            self.oled.fill(0)
            status_text = "OK" if success else "FAIL"
            self.oled.text(f"#{packet_id} [{status_text}] DR:{dr}", 0, 0)
            self.oled.text(f"T: {temp:.1f}C  H: {hum:.0f}%", 0, 16)

            rx = log.get("received_data", {})
            rssi = rx.get("rssi", "N/A")
            snr = rx.get("snr", "N/A")
            self.oled.text(f"RSSI: {rssi} dBm", 0, 34)
            self.oled.text(f"SNR:  {snr} dB", 0, 48)
            self.oled.show()
        except Exception:
            pass

    def show_message(self, line1: str, line2: str = "", line3: str = ""):
        """Displays a momentary notification popup."""
        if not self.oled:
            return
        self.wake()
        try:
            self.oled.fill(0)
            if line1:
                self.oled.text(line1, 0, 10)
            if line2:
                self.oled.text(line2, 0, 28)
            if line3:
                self.oled.text(line3, 0, 46)
            self.oled.show()
        except Exception:
            pass
