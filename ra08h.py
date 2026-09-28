"""Driver for Ai-Thinker RA-08H LoRaWAN Module (ASR6601 based).

Provides clean abstraction over AT-commands with line-based parsing,
timeout enforcement, and comprehensive radio link telemetry extraction.
"""

import time

try:
    from machine import UART
except ImportError:
    UART = object

if not hasattr(time, 'ticks_ms'):
    time.ticks_ms = lambda: int(time.time() * 1000)
    time.ticks_diff = lambda a, b: a - b
    time.sleep_ms = lambda ms: time.sleep(ms / 1000.0)


class RA08HError(Exception):
    """Base exception for RA-08H operations."""
    pass


class RA08H:
    """High-level driver for Ai-Thinker RA-08H LoRaWAN modem."""

    SEND_ERRORS = {
        '00': 'Not Joined to Network',
        '01': 'Radio channel busy / send failure',
        '02': 'Payload length exceeds maximum allowed for current Data Rate',
    }

    def __init__(self, uart: UART, debug: bool = True):
        self.uart = uart
        self.debug = debug
        self._is_joined = False
        self._current_dr = 5
        self._flush_rx()

    def _log(self, *args):
        if self.debug:
            print("[RA08H]", *args)

    def _flush_rx(self):
        """Discards pending bytes from the UART receive buffer."""
        try:
            while self.uart.any():
                self.uart.read()
        except Exception:
            pass

    def send_at_command(self, cmd: str, timeout_ms: int = 3000, stop_tokens: tuple = None) -> list:
        """Sends an AT command string and collects lines until timeout or stop tokens match."""
        self._flush_rx()
        if not cmd.endswith('\r'):
            cmd += '\r'

        self._log("TX ->", cmd.strip())
        self.uart.write(cmd)

        lines = []
        start_time = time.ticks_ms()

        while time.ticks_diff(time.ticks_ms(), start_time) < timeout_ms:
            if self.uart.any():
                raw = self.uart.readline()
                if raw:
                    line = raw.decode('utf-8', 'ignore').strip()
                    if line:
                        lines.append(line)
                        # Check termination tokens
                        if stop_tokens:
                            for token in stop_tokens:
                                if token in line:
                                    # Wait briefly for any immediate trailing line
                                    time.sleep_ms(30)
                                    while self.uart.any():
                                        trailing = self.uart.readline()
                                        if trailing:
                                            tr_line = trailing.decode('utf-8', 'ignore').strip()
                                            if tr_line:
                                                lines.append(tr_line)
                                    return lines
            else:
                time.sleep_ms(15)

        return lines

    # --- Configuration Methods ---

    def set_keys(self, deveui: str = None, appeui: str = None, appkey: str = None) -> bool:
        """Configures OTAA credentials on the modem."""
        success = True
        if deveui:
            resp = self.send_at_command(f"AT+CDEVEUI={deveui}\r", stop_tokens=("OK", "ERROR"))
            success = success and any("OK" in l for l in resp)
        if appeui:
            resp = self.send_at_command(f"AT+CAPPEUI={appeui}\r", stop_tokens=("OK", "ERROR"))
            success = success and any("OK" in l for l in resp)
        if appkey:
            resp = self.send_at_command(f"AT+CAPPKEY={appkey}\r", stop_tokens=("OK", "ERROR"))
            success = success and any("OK" in l for l in resp)
        return success

    def set_datarate(self, dr: int = 5):
        """Sets Data Rate (0..7, regional dependent) and disables ADR for manual control."""
        self.send_at_command("AT+CADR=0\r", timeout_ms=1000, stop_tokens=("OK",))
        time.sleep_ms(100)
        self.send_at_command(f"AT+CDATARATE={dr}\r", timeout_ms=1000, stop_tokens=("OK",))
        self._current_dr = dr
        self._log(f"Data Rate set to {dr}")

    def set_date_rate(self, dr: int = 5):
        """Backward-compatible alias for set_datarate."""
        self.set_datarate(dr)

    def set_adr(self, enable: bool = True):
        """Enables or disables Adaptive Data Rate (ADR)."""
        val = 1 if enable else 0
        self.send_at_command(f"AT+CADR={val}\r", timeout_ms=1000, stop_tokens=("OK",))
        self._log(f"ADR set to {enable}")

    def set_tx_power(self, power_dbm: int):
        """Sets transmit power (e.g. 14 dBm)."""
        self.send_at_command(f"AT+CTXP={power_dbm}\r", timeout_ms=1000, stop_tokens=("OK",))

    def get_version(self) -> str:
        """Returns modem firmware version string."""
        lines = self.send_at_command("AT+CGMR\r", timeout_ms=1000, stop_tokens=("OK",))
        return " ".join(lines) if lines else "Unknown"

    # --- Network Operations ---

    def join(self, timeout_ms: int = 15000) -> tuple:
        """Executes OTAA Join procedure (AT+CJOIN=1,0,0,1).

        Returns: (bool success, dict status_info)
        """
        self._log("Initiating OTAA Network Join...")
        stop_tokens = ("+CJOIN:OK", "+CJOIN:FAIL", "ERR+CJOIN")
        response = self.send_at_command("AT+CJOIN=1,0,0,1\r", timeout_ms=timeout_ms, stop_tokens=stop_tokens)

        joined = False
        msg = "No response"

        for line in response:
            if "+CJOIN:OK" in line or "joined" in line.lower():
                joined = True
                msg = "Network Joined"
                break
            elif "+CJOIN:FAIL" in line:
                joined = False
                msg = "Join Rejected by Gateway/Server"
                break

        self._is_joined = joined
        return joined, {
            "STATUS": "CJOIN:OK" if joined else "CJOIN:FAIL",
            "MSG": msg,
            "raw": response
        }

    def send_data(
        self,
        data_hex: str,
        confirmed: bool = False,
        nbtrials: int = 2,
        port: int = 1,
        timeout_ms: int = 12000
    ) -> tuple:
        """Transmits hex-encoded payload via AT+DTRX.

        data_hex: Hexadecimal payload string (e.g. '016864016700FA')
        confirmed: True for Confirmed uplink, False for Unconfirmed
        nbtrials: Retransmission count
        Returns: (bool success, dict telemetry_log)
        """
        data_len = len(data_hex) // 2
        conf_flag = 1 if confirmed else 0
        cmd = f"AT+DTRX={conf_flag},{nbtrials},{data_len},{data_hex}\r"

        stop_tokens = ("OK+SENT", "ERR+SENT", "ERR+SEND", "+DTRX:FAIL")
        response = self.send_at_command(cmd, timeout_ms=timeout_ms, stop_tokens=stop_tokens)

        log = {
            "SEND": {},
            "SENT": {},
            "RECV": {},
            "freq": {},
            "received_data": {
                "rssi": "N/A",
                "snr": "N/A",
                "daterate": str(self._current_dr)
            },
            "raw": response
        }

        send_ok = False
        sent_ok = False

        for line in response:
            # OK+SEND:length / ERR+SEND:code
            if "OK+SEND:" in line:
                log["SEND"] = {"STATUS": "OK+SEND", "TX_LEN": line.split("OK+SEND:")[1]}
                send_ok = True
            elif "ERR+SEND:" in line:
                code = line.split("ERR+SEND:")[1].strip()
                log["SEND"] = {"STATUS": "ERR+SEND", "ERR_NUM": (code, self.SEND_ERRORS.get(code, "Unknown"))}

            # OK+SENT:count / ERR+SENT:count
            if "OK+SENT:" in line:
                log["SENT"] = {"STATUS": "OK+SENT", "TX_CNT": line.split("OK+SENT:")[1]}
                sent_ok = True
            elif "ERR+SENT:" in line:
                log["SENT"] = {"STATUS": "ERR+SENT", "TX_CNT": line.split("ERR+SENT:")[1]}

            # Downlink Frame: OK+RECV:type,port,len,payload
            if "OK+RECV:" in line:
                parts = line.split("OK+RECV:")[1].split(",")
                if len(parts) >= 3:
                    log["RECV"] = {
                        "STATUS": "OK+RECV",
                        "TYPE": parts[0],
                        "PORT": parts[1],
                        "LEN": parts[2],
                        "DATA": parts[3] if len(parts) > 3 else ""
                    }

            # Radio Frequencies
            if "tx_freq" in line.lower():
                try:
                    for token in line.split(","):
                        if "tx_freq" in token.lower():
                            log["freq"]["tx_freq"] = int(token.split(":")[1])
                        elif "rx_freq" in token.lower():
                            log["freq"]["rx_freq"] = int(token.split(":")[1])
                except Exception:
                    pass

            # Link Quality Metrics (RSSI, SNR, DR)
            if "rssi" in line.lower() and "snr" in line.lower():
                try:
                    for token in line.split(","):
                        kv = token.strip().split(":")
                        if len(kv) >= 2:
                            k = kv[0].strip().lower()
                            v = kv[1].strip()
                            if "rssi" in k:
                                log["received_data"]["rssi"] = v
                            elif "snr" in k:
                                log["received_data"]["snr"] = v
                            elif "daterate" in k or "dr" in k:
                                log["received_data"]["daterate"] = v
                except Exception:
                    pass

        # Transmission succeeded if confirmed packet got OK+SENT, or unconfirmed got OK+SEND/SENT
        success = sent_ok or (send_ok and not confirmed)
        return success, log

    # --- Property Accessors ---

    @property
    def is_join(self) -> bool:
        return self._is_joined

    @property
    def datarate(self) -> int:
        return self._current_dr
