"""Configuration settings for ESP32 LoRaWAN Node (AI-Thinker RA-08H).

Organized by functional subsystem: Pinout, LoRaWAN, Sensors, Display, System.
"""

# ==============================================================================
# 1. HARDWARE PINOUT & BUS CONFIGURATION
# ==============================================================================

# --- UART Interface for Ai-Thinker RA-08H (ASR6601 LoRaWAN module) ---
UART_ID = 2
UART_BAUDRATE = 9600
PIN_UART_TX = 17   # Connect to RA-08H RX
PIN_UART_RX = 16   # Connect to RA-08H TX

# --- I2C Interface for SSD1306 OLED Display ---
I2C_ID = 0
I2C_FREQ = 400000  # 400 kHz Fast-mode
PIN_I2C_SCL = 26
PIN_I2C_SDA = 25

# --- User I/O (Button & LED) ---
PIN_BUTTON = 22    # Active HIGH (PULL_DOWN internally or externally)
PIN_LED = 14       # Active HIGH status LED

# --- Sensors ---
PIN_DHT = 18       # DHT11 / DHT22 single-wire data pin
IS_DHT22 = False   # Set True if using DHT22/AM2302, False for DHT11


# ==============================================================================
# 2. LORAWAN NETWORK CONFIGURATION
# ==============================================================================

# Join Mode: 1 = OTAA (Over-The-Air Activation), 2 = ABP
JOIN_MODE = 1

# OTAA Credentials (leave empty string to use credentials saved in RA-08H flash)
DEV_EUI = ""       # e.g., "70B3D57ED0050000" (16 hex chars)
APP_EUI = ""       # e.g., "0000000000000000" (16 hex chars)
APP_KEY = ""       # e.g., "2B7E151628AED2A6ABF7158809CF4F3C" (32 hex chars)

# Radio link parameters
DEFAULT_DATARATE = 5    # DR5 = SF7/125kHz (higher throughput, shorter range)
ENABLE_ADR = False      # Adaptive Data Rate (AT+CADR=1)
TX_POWER_DBM = 14       # Transmit power (typically 14-20 dBm)

# Uplink transmission settings
CONFIRMED_UPLINK = False # False = Unconfirmed (saves network capacity & battery)
UPLINK_RETRIES = 2       # Retries for confirmed frames
LORA_PORT = 1            # FPort (1..223)


# ==============================================================================
# 3. TIMING & ENERGY MANAGEMENT
# ==============================================================================

# Telemetry interval in seconds (respect regional 1% duty-cycle regulations)
TX_INTERVAL_SEC = 60

# OTAA Join timing
JOIN_TIMEOUT_MS = 15000
JOIN_MAX_ATTEMPTS = 5
JOIN_RETRY_DELAY_SEC = 5

# OLED Display auto-off (0 to keep display always active)
SCREEN_TIMEOUT_SEC = 30

# Button debounce
BUTTON_DEBOUNCE_MS = 250
BUTTON_LONG_PRESS_MS = 2000

# Sensor read retry policy
SENSOR_MAX_RETRIES = 3
SENSOR_RETRY_DELAY_MS = 250


# ==============================================================================
# 4. SYSTEM HEALTH & WATCHDOG
# ==============================================================================

ENABLE_WDT = False       # Set True in production to auto-reset on deadlocks
WDT_TIMEOUT_MS = 30000   # 30 seconds watchdog period
