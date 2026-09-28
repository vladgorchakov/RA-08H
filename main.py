"""Main Application entrypoint for ESP32 LoRaWAN Node (AI-Thinker RA-08H).

Implements a non-blocking event-driven loop with:
- State Machine architecture (Boot -> Join -> Telemetry Loop)
- Non-blocking button handling (Click = Cycle DataRate, Long Press = Force Uplink)
- Sensor reading with Cayenne LPP encoding
- Robust AT-command modem communication
- Energy-conscious OLED display management
- Hardware Watchdog integration
"""

import gc
import time
from machine import UART, Pin, I2C, SoftI2C

try:
    from machine import WDT
except ImportError:
    WDT = None

import config
from button import Button
from cayenne import LPPcodec
from display.manager import DisplayManager
from humidity import HumSensor
from ra08h import RA08H

if not hasattr(time, 'ticks_ms'):
    time.ticks_ms = lambda: int(time.time() * 1000)
    time.ticks_diff = lambda a, b: a - b
    time.sleep_ms = lambda ms: time.sleep(ms / 1000.0)


class LoRaWANNodeApp:
    """Orchestrates hardware peripherals, network lifecycle, and telemetry transmissions."""

    def __init__(self):
        print("\n==========================================")
        print("  ESP32 LoRaWAN Node - Starting Firmware  ")
        print("==========================================")
        gc.collect()

        # 1. Hardware Watchdog
        self.wdt = None
        if config.ENABLE_WDT and WDT is not None:
            try:
                self.wdt = WDT(timeout=config.WDT_TIMEOUT_MS)
                print("[SYS] Watchdog Timer initialized")
            except Exception as e:
                print(f"[SYS] WDT init warning: {e}")

        # 2. Status LED
        self.led = Pin(config.PIN_LED, Pin.OUT)
        self.led.off()

        # 3. I2C Bus & Display Manager
        self.display = self._init_display()
        self.display.show_splash("LoRaWAN Node", "AI-Thinker RA-08H")

        # 4. UART & LoRaWAN Modem
        self.uart = UART(
            config.UART_ID,
            baudrate=config.UART_BAUDRATE,
            tx=Pin(config.PIN_UART_TX),
            rx=Pin(config.PIN_UART_RX)
        )
        self.lora = RA08H(self.uart)

        # 5. Sensors & Codec
        self.sensor = HumSensor(config.PIN_DHT, is_dht22=config.IS_DHT22)
        self.codec = LPPcodec()

        # 6. State & Controls
        self.current_dr = config.DEFAULT_DATARATE
        self.packet_counter = 0
        self.last_tx_timestamp = -config.TX_INTERVAL_SEC * 1000
        self.force_tx_flag = False

        # Non-blocking button handler
        self.button = Button(
            pin_num=config.PIN_BUTTON,
            on_click=self._on_button_click,
            on_long_press=self._on_button_long_press,
            debounce_ms=config.BUTTON_DEBOUNCE_MS,
            long_press_ms=config.BUTTON_LONG_PRESS_MS
        )

        # Configure modem parameters
        self._configure_modem()

    def _init_display(self) -> DisplayManager:
        """Initializes hardware I2C with fallback to software bit-bang I2C."""
        i2c = None
        try:
            i2c = I2C(config.I2C_ID, scl=Pin(config.PIN_I2C_SCL), sda=Pin(config.PIN_I2C_SDA), freq=config.I2C_FREQ)
            print("[I2C] Hardware I2C initialized")
        except Exception:
            try:
                i2c = SoftI2C(scl=Pin(config.PIN_I2C_SCL), sda=Pin(config.PIN_I2C_SDA))
                print("[I2C] Falling back to SoftI2C")
            except Exception as err:
                print(f"[I2C] Error initializing bus: {err}")

        return DisplayManager(
            i2c,
            width=config.OLED_WIDTH,
            height=config.OLED_HEIGHT,
            timeout_sec=config.SCREEN_TIMEOUT_SEC
        )

    def _configure_modem(self):
        """Applies configured network credentials and radio settings."""
        if config.DEV_EUI or config.APP_EUI or config.APP_KEY:
            self.lora.set_keys(
                deveui=config.DEV_EUI or None,
                appeui=config.APP_EUI or None,
                appkey=config.APP_KEY or None
            )

        if config.ENABLE_ADR:
            self.lora.set_adr(True)
        else:
            self.lora.set_datarate(self.current_dr)

        if config.TX_POWER_DBM:
            self.lora.set_tx_power(config.TX_POWER_DBM)

    def _on_button_click(self):
        """Short click: wakes display, cycles DataRate."""
        self.display.wake()

        # Cycle Data Rate: 5 -> 4 -> 3 -> 2 -> 1 -> 0 -> 5
        if self.current_dr > 0:
            self.current_dr -= 1
        else:
            self.current_dr = 5

        print(f"[USER] Button clicked -> Changing DataRate to {self.current_dr}")
        self._blink_led(100)
        self.lora.set_datarate(self.current_dr)
        self.display.show_message("SETTINGS", f"DataRate: DR{self.current_dr}", "Applying...")
        time.sleep_ms(600)

    def _on_button_long_press(self):
        """Long press: wakes display and forces immediate transmission."""
        print("[USER] Button held -> Forcing immediate uplink")
        self.display.wake()
        self.display.show_message("MANUAL TRIGGER", "Measuring sensor...", "Sending...")
        self._blink_led(300)
        self.force_tx_flag = True

    def _blink_led(self, duration_ms: int = 100):
        self.led.on()
        time.sleep_ms(duration_ms)
        self.led.off()

    def feed_wdt(self):
        if self.wdt is not None:
            self.wdt.feed()

    def perform_network_join(self) -> bool:
        """Executes OTAA Join sequence with bounded retries."""
        for attempt in range(1, config.JOIN_MAX_ATTEMPTS + 1):
            self.feed_wdt()
            self.display.show_join(attempt, config.JOIN_MAX_ATTEMPTS, "JOINING", "Connecting...")
            self.led.on()

            success, info = self.lora.join(timeout_ms=config.JOIN_TIMEOUT_MS)
            self.led.off()

            self.display.show_join(attempt, config.JOIN_MAX_ATTEMPTS, info["STATUS"], info["MSG"])

            if success:
                print(f"[NET] Network Joined successfully on attempt {attempt}")
                self._blink_led(400)
                time.sleep(1)
                return True
            else:
                print(f"[NET] Join attempt {attempt} failed ({info['MSG']}).")
                if attempt < config.JOIN_MAX_ATTEMPTS:
                    time.sleep(config.JOIN_RETRY_DELAY_SEC)

        print("[NET] Could not join network. Will retry in background loop.")
        return False

    def transmit_telemetry(self):
        """Measures sensor, encodes in Cayenne LPP, and transmits over LoRaWAN."""
        # 1. Read environmental data
        hum = self.sensor.humidity
        temp = self.sensor.temp
        print(f"\n[MEASURE] Sensor reading: Temp={temp:.1f}°C, Hum={hum:.0f}%")

        # 2. Encode with Cayenne LPP
        payload_hex = self.codec.encode_humtemp((hum, temp), channel=config.LORA_PORT)
        print(f"[PAYLOAD] Cayenne LPP Hex: {payload_hex} ({self.codec.size} bytes)")

        # 3. Transmit via RA-08H
        self.led.on()
        success, log = self.lora.send_data(
            data_hex=payload_hex,
            confirmed=config.CONFIRMED_UPLINK,
            nbtrials=config.UPLINK_RETRIES,
            port=config.LORA_PORT
        )
        self.led.off()

        self.packet_counter += 1

        # 4. Update UI & Serial Diagnostics
        self.display.show_telemetry(self.packet_counter, success, log, hum, temp, self.current_dr)
        self._print_diagnostics(success, log, hum, temp)

        # 5. Clean up memory
        gc.collect()

    def _print_diagnostics(self, success: bool, log: dict, hum: float, temp: float):
        status = "SUCCESS" if success else "FAILED"
        rx = log.get("received_data", {})
        print(f"=== UPLINK #{self.packet_counter} [{status}] ===")
        print(f"  Payload: Temp={temp:.1f}°C, Hum={hum:.0f}%")
        print(f"  Radio:   DR={rx.get('daterate', self.current_dr)}, RSSI={rx.get('rssi')} dBm, SNR={rx.get('snr')} dB")
        if "RECV" in log and log["RECV"].get("DATA"):
            print(f"  Downlink Received: {log['RECV']['DATA']} on Port {log['RECV']['PORT']}")
        print("===================================\n")

    def run(self):
        """Main non-blocking execution loop."""
        # Step 1: Initial Network Join
        self.perform_network_join()

        # Step 2: Main Event Loop
        while True:
            self.feed_wdt()

            # Automatic screen power-save timeout check
            self.display.check_power_timeout()

            # Time to send telemetry or manual trigger?
            now = time.ticks_ms()
            elapsed_ms = time.ticks_diff(now, self.last_tx_timestamp)
            interval_ms = config.TX_INTERVAL_SEC * 1000

            if elapsed_ms >= interval_ms or self.force_tx_flag:
                self.force_tx_flag = False
                self.last_tx_timestamp = now

                # If connection was lost, attempt reconnection
                if not self.lora.is_join:
                    print("[NET] Not joined to network. Re-attempting join...")
                    self.perform_network_join()
                    if not self.lora.is_join:
                        time.sleep_ms(100)
                        continue

                self.transmit_telemetry()

            time.sleep_ms(50)


def main():
    app = LoRaWANNodeApp()
    app.run()


if __name__ == '__main__':
    main()
