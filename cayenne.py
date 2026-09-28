"""Cayenne Low Power Payload (LPP) Encoder and Decoder for MicroPython.

Specification compliant (Semtech / myDevices Cayenne LPP):
- Temperature: 0.1 °C signed (16-bit two's complement)
- Relative Humidity: 0.5 % unsigned (8-bit)
- Analog Input / Battery: 0.01 signed (16-bit)
- Voltage: 0.01 V unsigned (16-bit)
- Barometer: 0.1 hPa unsigned (16-bit)
- GPS: Latitude / Longitude (0.0001 deg), Altitude (0.01 m)
"""

try:
    import ustruct as struct
except ImportError:
    import struct

try:
    import ubinascii as binascii
except ImportError:
    import binascii


class CayenneLPPType:
    DIGITAL_IN  = 0x00 # 1 byte
    DIGITAL_OUT = 0x01 # 1 byte
    ANALOG_IN   = 0x02 # 2 bytes, 0.01 signed
    ANALOG_OUT  = 0x03 # 2 bytes, 0.01 signed
    ILLUMINANCE = 0x65 # 2 bytes, 1 Lux unsigned
    PRESENCE    = 0x66 # 1 byte
    TEMPERATURE = 0x67 # 2 bytes, 0.1 °C signed
    HUMIDITY    = 0x68 # 1 byte, 0.5 % unsigned
    BAROMETER   = 0x73 # 2 bytes, 0.1 hPa unsigned
    VOLTAGE     = 0x74 # 2 bytes, 0.01 V unsigned
    ACCEL       = 0x71 # 6 bytes: X, Y, Z (0.001 G signed)
    GPS         = 0x88 # 9 bytes: Lat, Lon, Alt


class LPPcodec:
    """Encodes and decodes Cayenne LPP data frames efficiently."""

    def __init__(self):
        self._buffer = bytearray()

    def reset(self):
        """Clears the internal payload buffer."""
        self._buffer = bytearray()
        return self

    # --- Builder Methods ---

    def add_temperature(self, value: float, channel: int = 1):
        """Adds Temperature in °C (resolution 0.1 °C, signed 16-bit)."""
        raw = int(round(value * 10))
        self._buffer.extend(struct.pack('>BBh', channel, CayenneLPPType.TEMPERATURE, raw))
        return self

    def add_humidity(self, value: float, channel: int = 1):
        """Adds Relative Humidity in % (0..100%, resolution 0.5 %, unsigned 8-bit)."""
        clamped = max(0.0, min(100.0, float(value)))
        raw = int(round(clamped * 2))
        self._buffer.extend(struct.pack('>BBB', channel, CayenneLPPType.HUMIDITY, raw))
        return self

    def add_analog_input(self, value: float, channel: int = 1):
        """Adds Analog Input (e.g. Battery Voltage) with 0.01 resolution (signed 16-bit)."""
        raw = int(round(value * 100))
        self._buffer.extend(struct.pack('>BBh', channel, CayenneLPPType.ANALOG_IN, raw))
        return self

    def add_voltage(self, value: float, channel: int = 1):
        """Adds Voltage in V with 0.01 V resolution (unsigned 16-bit)."""
        raw = max(0, int(round(value * 100)))
        self._buffer.extend(struct.pack('>BBH', channel, CayenneLPPType.VOLTAGE, raw))
        return self

    def add_barometer(self, value_hpa: float, channel: int = 1):
        """Adds Barometric Pressure in hPa with 0.1 hPa resolution (unsigned 16-bit)."""
        raw = max(0, int(round(value_hpa * 10)))
        self._buffer.extend(struct.pack('>BBH', channel, CayenneLPPType.BAROMETER, raw))
        return self

    def add_gps(self, latitude: float, longitude: float, altitude_m: float, channel: int = 1):
        """Adds GPS Location (Lat/Lon resolution 0.0001 deg, Alt 0.01 m)."""
        lat_raw = int(round(latitude * 10000))
        lon_raw = int(round(longitude * 10000))
        alt_raw = int(round(altitude_m * 100))

        # Pack 24-bit signed integers for Lat/Lon
        lat_bytes = struct.pack('>i', lat_raw)[1:] # 3 bytes
        lon_bytes = struct.pack('>i', lon_raw)[1:] # 3 bytes
        alt_bytes = struct.pack('>i', alt_raw)[1:] # 3 bytes

        self._buffer.extend(struct.pack('>BB', channel, CayenneLPPType.GPS))
        self._buffer.extend(lat_bytes)
        self._buffer.extend(lon_bytes)
        self._buffer.extend(alt_bytes)
        return self

    # --- Serialization Outputs ---

    def to_bytes(self) -> bytes:
        """Returns the serialized payload as bytes."""
        return bytes(self._buffer)

    def to_hex(self) -> str:
        """Returns the serialized payload as an uppercase hexadecimal string."""
        return binascii.hexlify(self._buffer).decode('ascii').upper()

    @property
    def size(self) -> int:
        """Returns the current size of the payload in bytes."""
        return len(self._buffer)

    # --- Backward-Compatible Helpers ---

    def encode_temp(self, value: float, channel: int = 1) -> str:
        raw = int(round(value * 10))
        return binascii.hexlify(struct.pack('>BBh', channel, CayenneLPPType.TEMPERATURE, raw)).decode('ascii').upper()

    def encode_humidity(self, value: float, channel: int = 1) -> str:
        clamped = max(0.0, min(100.0, float(value)))
        raw = int(round(clamped * 2))
        return binascii.hexlify(struct.pack('>BBB', channel, CayenneLPPType.HUMIDITY, raw)).decode('ascii').upper()

    def encode_humtemp(self, values, channel: int = 1) -> str:
        """values: tuple/list of (humidity, temperature) -> returns Cayenne LPP hex string."""
        hum, temp = values[0], values[1]
        self.reset()
        self.add_humidity(hum, channel=channel)
        self.add_temperature(temp, channel=channel)
        return self.to_hex()

    # --- Decoder (for unit testing and verification) ---

    @staticmethod
    def decode(data) -> list:
        """Decodes raw bytes or hex string into a list of sensor reading dictionaries."""
        if isinstance(data, str):
            raw = binascii.unhexlify(data)
        else:
            raw = bytes(data)

        results = []
        idx = 0
        length = len(raw)

        while idx < length:
            if idx + 2 > length:
                break
            channel = raw[idx]
            data_type = raw[idx + 1]
            idx += 2

            if data_type == CayenneLPPType.TEMPERATURE:
                val = struct.unpack('>h', raw[idx:idx + 2])[0] / 10.0
                results.append({"channel": channel, "type": "temperature", "value": val})
                idx += 2
            elif data_type == CayenneLPPType.HUMIDITY:
                val = raw[idx] / 2.0
                results.append({"channel": channel, "type": "humidity", "value": val})
                idx += 1
            elif data_type == CayenneLPPType.ANALOG_IN:
                val = struct.unpack('>h', raw[idx:idx + 2])[0] / 100.0
                results.append({"channel": channel, "type": "analog_in", "value": val})
                idx += 2
            elif data_type == CayenneLPPType.VOLTAGE:
                val = struct.unpack('>H', raw[idx:idx + 2])[0] / 100.0
                results.append({"channel": channel, "type": "voltage", "value": val})
                idx += 2
            elif data_type == CayenneLPPType.BAROMETER:
                val = struct.unpack('>H', raw[idx:idx + 2])[0] / 10.0
                results.append({"channel": channel, "type": "barometer", "value": val})
                idx += 2
            else:
                # Unknown type, cannot reliably skip without length table
                break

        return results
