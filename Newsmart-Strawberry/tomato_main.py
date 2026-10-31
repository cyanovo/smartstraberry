import utime

from umqtt.simple import MQTTClient
import _thread
import gc
import machine
import network
import ubinascii
import ujson
import usocket as socket
import uasyncio as asyncio


# WiFi needs a relatively large contiguous block when its driver starts.
# Initialize it before UART buffers and the other application objects.
gc.collect()
station = network.WLAN(network.STA_IF)


# ========== Basic configuration ==========

CONFIG_FILE = "config.json"
APP_BUILD = "2026-08-24-esp32s3-five-light-profiles-r18"

AP_SSID = "A-tomato"
AP_PWD = "12345678"
AP_IP = "192.168.4.1"

MQTT_PORT = 1883
MQTT_KEEPALIVE = 120
MQTT_TELEMETRY_INTERVAL_MS = 10000

MQTT_TOPIC_ROOT = b"tomato_hnsw0001"
TOPIC_SET = MQTT_TOPIC_ROOT + b"/set"
TOPIC_RESULT = MQTT_TOPIC_ROOT + b"/result"
TOPIC_STATE = MQTT_TOPIC_ROOT + b"/state"
TOPIC_TELEMETRY = MQTT_TOPIC_ROOT + b"/telemetry"
TOPIC_AVAILABILITY = MQTT_TOPIC_ROOT + b"/availability"

RECONNECT_INTERVAL_MS = 10000


def log(message):
    print(message)


def load_config():
    try:
        with open(CONFIG_FILE, "r") as config_file:
            return ujson.load(config_file)
    except Exception:
        return {}


def save_config(config):
    try:
        with open(CONFIG_FILE, "w") as config_file:
            ujson.dump(config, config_file)
        return True
    except Exception as exc:
        print("Save config error:", exc)
        return False


_config = load_config()
wifi_ssid = _config.get("wifi_ssid", "JXDZ")
wifi_password = _config.get("wifi_pwd", "18539922132")
mqtt_server = _config.get("mqtt_server", "broker.emqx.io")
mqtt_user = _config.get("mqtt_user", "admin")
mqtt_password = _config.get("mqtt_password", "admin123")


# ========== RS485 protocol ============

SENSOR_WATER_ADDRESS = 0x01
SENSOR_AIR_ADDRESS = 0x04
SENSOR_PH_ADDRESS = 0x06
CONTROLLER_ADDRESS = 0x08

MODBUS_READ_HOLDING = 0x03

LIGHT_CHANNEL_RED = 0x01
LIGHT_CHANNEL_BLUE = 0x02


def crc16_modbus(data):
    crc = 0xFFFF
    for value in data:
        crc ^= value
        bit = 0
        while bit < 8:
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
            bit += 1
    return crc & 0xFFFF


def append_crc(payload):
    crc = crc16_modbus(payload)
    return bytes(payload) + bytes((crc & 0xFF, (crc >> 8) & 0xFF))


def frame_crc_valid(frame):
    if frame is None or len(frame) < 4:
        return False
    expected = crc16_modbus(frame[:-2])
    actual = frame[-2] | (frame[-1] << 8)
    return expected == actual


def build_light_brightness_frame(channel, brightness):
    if channel not in (LIGHT_CHANNEL_RED, LIGHT_CHANNEL_BLUE):
        raise ValueError("invalid light channel")
    if type(brightness) is not int or brightness < 0 or brightness > 100:
        raise ValueError("brightness must be an integer from 0 to 100")

    payload = bytearray(
        (
            CONTROLLER_ADDRESS,
            0x77,
            0x13,
            channel,
            0x10,
            0x00,
            0x0E,
            0xCE,
            0x0F,
            0x32,
            0x10,
            0x04,
            0x0B,
            0xB8,
        )
    )
    if brightness == 0:
        payload.extend((0, 0, 0, 0, 0, 0, 0, 0))
    else:
        payload.append(brightness)
        payload.extend((100, 100, 100, 100, 100, 100, 100))
    return append_crc(payload)


def build_pump_frame(state):
    if state not in (0, 1):
        raise ValueError("pump state must be 0 or 1")
    return append_crc(bytes((CONTROLLER_ADDRESS, 0x79, 0x01, state)))


def _rs485_u16(data, offset):
    return (data[offset] << 8) | data[offset + 1]


def _rs485_s16(data, offset):
    value = _rs485_u16(data, offset)
    if value & 0x8000:
        value -= 0x10000
    return value


def _modbus_data(frame, expected_address):
    if not frame_crc_valid(frame):
        raise ValueError("invalid CRC")
    if frame[0] != expected_address:
        raise ValueError("unexpected device address")
    if frame[1] == (MODBUS_READ_HOLDING | 0x80):
        raise ValueError("device exception code {}".format(frame[2]))
    if frame[1] != MODBUS_READ_HOLDING:
        raise ValueError("unexpected function code")

    byte_count = frame[2]
    if len(frame) != byte_count + 5:
        raise ValueError("invalid response length")
    return frame[3:3 + byte_count]


def parse_sensor_frame(frame):
    if not frame:
        raise ValueError("empty sensor frame")

    address = frame[0]
    data = _modbus_data(frame, address)

    if address == SENSOR_WATER_ADDRESS:
        if len(data) < 6:
            raise ValueError("water sensor response is too short")
        return {
            "hydroponic_temperature": _rs485_s16(data, 0) / 10.0,
            "nutrient_ec": _rs485_u16(data, 2) / 20.15,
            "water_tank_level": _rs485_u16(data, 4) / 10.0,
        }

    if address == SENSOR_AIR_ADDRESS:
        if len(data) < 6:
            raise ValueError("air sensor response is too short")
        return {
            "light_intensity": _rs485_u16(data, 0),
            "air_temperature": _rs485_s16(data, 2) / 10.0,
            "air_humidity": _rs485_u16(data, 4) / 10.0,
        }

    if address == SENSOR_PH_ADDRESS:
        if len(data) < 2:
            raise ValueError("pH sensor response is too short")
        return {"ph_value": _rs485_u16(data, 0) / 100.0}

    raise ValueError("unsupported sensor address {}".format(address))


# ========== UART configuration ==========

# ESP32-S3 UART1: TJC display. Wiring: display TX -> GPIO8, display RX -> GPIO9.
tjc_uart = machine.UART(
    1,
    baudrate=9600,
    tx=9,
    rx=8,
    bits=8,
    parity=None,
    stop=1,
    rxbuf=256,
    timeout=0,
    timeout_char=2,
)

# ESP32-S3 UART2: RS485 bus. Wiring: RS485 DI <- GPIO4, RO -> GPIO5.
# The transceiver handles TX/RX direction automatically, so no
# direction-control GPIO is used.
rs485_serial = machine.UART(
    2,
    baudrate=9600,
    tx=4,
    rx=5,
    bits=8,
    parity=None,
    stop=1,
    rxbuf=512,
    timeout=0,
    timeout_char=2,
)

RS485_BUS_IDLE_MS = 15
RS485_CONTROL_SETTLE_MS = 10
RS485_CONTROL_SEND_COUNT = 3
RS485_CONTROL_REPEAT_GAP_MS = 300
# Every RS485 control frame, including red/blue frames produced by the master
# light switch, is separated by this minimum time.
RS485_CONTROL_INTER_FRAME_GAP_MS = 300
RS485_CONTROL_TX_LOG = True
RS485_MAX_COMMAND_QUEUE = 16
RS485_RX_RING_CAPACITY = 512
RS485_SENSOR_MAX_FRAME_LENGTH = 32
RS485_MONITOR_SAMPLE_LIMIT = 96
RS485_DEBUG = False
RS485_MONITOR = True
RS485_MONITOR_INTERVAL_MS = 5000

RS485_SENSOR_RESPONSE_HEADERS = (
    b"\x01\x03\x06",  # water temperature, EC and water level
    b"\x04\x03\x0c",  # light, air temperature and humidity
    b"\x06\x03\x04",  # pH and reserved register
)

rs485_command_queue = []
rs485_rx_byte_count = 0
rs485_valid_sensor_frame_count = 0
rs485_last_rx_sample = b""
rs485_crc_error_count = 0
rs485_length_error_count = 0
rs485_parse_error_count = 0


class _Rs485RingBuffer:
    """Fixed-size ring buffer: no bulk copy when data is consumed."""

    def __init__(self, capacity):
        self.capacity = capacity
        self.data = bytearray(capacity)
        self.read_index = 0
        self.write_index = 0
        self.count = 0
        self.overflow_count = 0

    def append(self, source):
        for value in source:
            if self.count == self.capacity:
                self.read_index += 1
                if self.read_index == self.capacity:
                    self.read_index = 0
                self.count -= 1
                self.overflow_count += 1

            self.data[self.write_index] = value
            self.write_index += 1
            if self.write_index == self.capacity:
                self.write_index = 0
            self.count += 1

    def peek(self, offset):
        index = self.read_index + offset
        if index >= self.capacity:
            index %= self.capacity
        return self.data[index]

    def discard(self, length):
        if length >= self.count:
            self.read_index = self.write_index
            self.count = 0
            return

        self.read_index += length
        self.read_index %= self.capacity
        self.count -= length

    def frame(self, length):
        # Sensor frames are at most 32 bytes.  Only a complete candidate frame
        # is copied for CRC checking and protocol parsing.
        output = bytearray(length)
        index = self.read_index
        for offset in range(length):
            output[offset] = self.data[index]
            index += 1
            if index == self.capacity:
                index = 0
        return bytes(output)


rs485_rx_ring = _Rs485RingBuffer(RS485_RX_RING_CAPACITY)


def _rs485_debug_frame(prefix, data):
    if RS485_DEBUG and data:
        print(prefix, ubinascii.hexlify(data).decode())


def _queue_rs485_frame(key, frame):
    queued = (key, frame, RS485_CONTROL_SEND_COUNT, utime.ticks_ms())
    index = 0
    while index < len(rs485_command_queue):
        if rs485_command_queue[index][0] == key:
            rs485_command_queue[index] = queued
            return
        index += 1

    if len(rs485_command_queue) >= RS485_MAX_COMMAND_QUEUE:
        rs485_command_queue.pop(0)
    rs485_command_queue.append(queued)


def queue_rs485_control_for_command(cmd):
    try:
        if cmd == "01":
            _queue_rs485_frame(
                "red_light",
                build_light_brightness_frame(
                    LIGHT_CHANNEL_RED,
                    red_light_brightness,
                ),
            )
            return

        if cmd == "02":
            _queue_rs485_frame(
                "blue_light",
                build_light_brightness_frame(
                    LIGHT_CHANNEL_BLUE,
                    blue_light_brightness,
                ),
            )
            return

        if cmd == "03":
            _queue_rs485_frame(
                "water_pump",
                build_pump_frame(pump_state),
            )
            return

        if cmd in ("04", "05"):
            # The master light switch and each tomato stage profile both send
            # the current red/blue outputs as two independent RS485 frames.
            _queue_rs485_frame(
                "red_light",
                build_light_brightness_frame(
                    LIGHT_CHANNEL_RED,
                    red_light_brightness,
                ),
            )
            _queue_rs485_frame(
                "blue_light",
                build_light_brightness_frame(
                    LIGHT_CHANNEL_BLUE,
                    blue_light_brightness,
                ),
            )
    except Exception as exc:
        print("RS485 control frame error:", cmd, exc)


def _apply_rs485_sensor_values(values):
    global air_temperature, air_humidity, light_intensity
    global hydroponic_temperature, water_tank_level, ph_value, nutrient_ec

    if "air_temperature" in values:
        air_temperature = round(values["air_temperature"], 1)
    if "air_humidity" in values:
        air_humidity = round(values["air_humidity"], 1)
    if "light_intensity" in values:
        light_intensity = int(values["light_intensity"])
    if "hydroponic_temperature" in values:
        hydroponic_temperature = round(values["hydroponic_temperature"], 1)
    if "water_tank_level" in values:
        water_tank_level = round(values["water_tank_level"], 1)
    if "ph_value" in values:
        ph_value = round(values["ph_value"], 2)
    if "nutrient_ec" in values:
        nutrient_ec = round(values["nutrient_ec"], 2)


def _rs485_sensor_header_at_ring_start(ring):
    if ring.count < 3:
        return False

    first = ring.peek(0)
    second = ring.peek(1)
    third = ring.peek(2)
    for header in RS485_SENSOR_RESPONSE_HEADERS:
        if (
            first == header[0]
            and second == header[1]
            and third == header[2]
        ):
            return True
    return False


def _rs485_parse_passive_ring(ring):
    global rs485_valid_sensor_frame_count, rs485_crc_error_count
    global rs485_length_error_count, rs485_parse_error_count

    # A nonmatching byte is discarded by advancing only the read pointer.
    # This preserves a two-byte partial header at the end of the ring without
    # allocating or copying a new receive buffer.
    while ring.count >= 3:
        if not _rs485_sensor_header_at_ring_start(ring):
            ring.discard(1)
            continue

        frame_length = int(ring.peek(2)) + 5
        if frame_length > RS485_SENSOR_MAX_FRAME_LENGTH:
            rs485_length_error_count += 1
            ring.discard(1)
            continue
        if ring.count < frame_length:
            return

        frame = ring.frame(frame_length)
        if frame_crc_valid(frame):
            try:
                values = parse_sensor_frame(frame)
                _apply_rs485_sensor_values(values)
                rs485_valid_sensor_frame_count += 1
                if RS485_MONITOR:
                    print(
                        "RS485 sensor RX 0x{:02X}:".format(frame[0]),
                        values,
                    )
                ring.discard(frame_length)
                continue
            except Exception as exc:
                rs485_parse_error_count += 1
                if RS485_DEBUG:
                    print("RS485 sensor parse error:", exc)
        else:
            rs485_crc_error_count += 1
            _rs485_debug_frame("RS485 CRC invalid:", frame)

        # CRC/parse error: shift by one byte and search for the next header.
        ring.discard(1)


async def _send_one_rs485_control(key, frame, attempt):
    try:
        if RS485_CONTROL_TX_LOG:
            print(
                "RS485 TX {} {}/{}:".format(
                    key,
                    attempt,
                    RS485_CONTROL_SEND_COUNT,
                ),
                ubinascii.hexlify(frame).decode(),
            )
        written = rs485_serial.write(frame)
        if written is not None and written != len(frame):
            print(
                "RS485 TX short write {}: {}/{}".format(
                    key,
                    written,
                    len(frame),
                )
            )
        await asyncio.sleep_ms(RS485_CONTROL_SETTLE_MS)
    except Exception as exc:
        print("RS485 control send error:", exc)


async def rs485_loop():
    global rs485_rx_byte_count, rs485_last_rx_sample

    last_bus_activity = utime.ticks_ms()
    last_monitor_report = last_bus_activity
    last_control_tx = utime.ticks_add(
        last_bus_activity,
        -RS485_CONTROL_INTER_FRAME_GAP_MS,
    )

    while True:
        count = rs485_serial.any()
        if count:
            chunk = rs485_serial.read(count)
            if chunk:
                last_bus_activity = utime.ticks_ms()
                rs485_rx_byte_count += len(chunk)
                rs485_last_rx_sample = bytes(
                    (rs485_last_rx_sample + chunk)[
                        -RS485_MONITOR_SAMPLE_LIMIT:
                    ]
                )
                _rs485_debug_frame("RS485 RX:", chunk)
                rs485_rx_ring.append(chunk)
                _rs485_parse_passive_ring(rs485_rx_ring)

        now = utime.ticks_ms()
        if RS485_MONITOR and utime.ticks_diff(
            now,
            last_monitor_report,
        ) >= RS485_MONITOR_INTERVAL_MS:
            sample_text = "none"
            if rs485_last_rx_sample:
                sample_text = ubinascii.hexlify(
                    rs485_last_rx_sample
                ).decode()
            print(
                "RS485 monitor: rx_bytes={} valid_frames={} "
                "ring={}/{} overflow={} crc_err={} len_err={} "
                "parse_err={} uart=hardware-uart2 last_rx={}".format(
                    rs485_rx_byte_count,
                    rs485_valid_sensor_frame_count,
                    rs485_rx_ring.count,
                    RS485_RX_RING_CAPACITY,
                    rs485_rx_ring.overflow_count,
                    rs485_crc_error_count,
                    rs485_length_error_count,
                    rs485_parse_error_count,
                    sample_text,
                )
            )
            last_monitor_report = now
            rs485_last_rx_sample = b""

        if rs485_command_queue:
            key, frame, remaining, not_before = rs485_command_queue[0]
            if (
                utime.ticks_diff(now, not_before) >= 0
                and utime.ticks_diff(now, last_bus_activity)
                >= RS485_BUS_IDLE_MS
                and utime.ticks_diff(now, last_control_tx)
                >= RS485_CONTROL_INTER_FRAME_GAP_MS
            ):
                rs485_command_queue.pop(0)
                attempt = RS485_CONTROL_SEND_COUNT - remaining + 1
                await _send_one_rs485_control(key, frame, attempt)
                last_bus_activity = utime.ticks_ms()
                last_control_tx = last_bus_activity

                if remaining > 1:
                    newer_command_waiting = False
                    for queued in rs485_command_queue:
                        if queued[0] == key:
                            newer_command_waiting = True
                            break
                    if not newer_command_waiting:
                        rs485_command_queue.append(
                            (
                                key,
                                frame,
                                remaining - 1,
                                utime.ticks_add(
                                    last_bus_activity,
                                    RS485_CONTROL_REPEAT_GAP_MS,
                                ),
                            )
                        )

        await asyncio.sleep_ms(2)


# ========== Connection state ==========

wifi_connected = False
wifi_connecting = False
mqtt_connected = False
mqtt_connecting = False
mqtt_client = None
mqtt_state_dirty = True
config_ap_active = False
config_ap_ready = False
network_startup_ready = False

previous_wifi_state = None
previous_mqtt_state = None
last_reconnect_attempt = 0


# ========== TJC display ==========

TJC_COMMAND_END = b"\xff\xff\xff"
TJC_FRAME_HEADER = b"\x55\xaa"
TJC_BASE_FRAME_LENGTH = 8
TJC_REST_TIME_FRAME_LENGTH = 10
TJC_MAIN_PAGE = "page0"

TJC_CMD_RED_BRIGHTNESS = 0x01
TJC_CMD_BLUE_BRIGHTNESS = 0x02
TJC_CMD_PUMP_STATE = 0x03
TJC_CMD_LIGHT_MASTER_STATE = 0x04
TJC_CMD_FILL_LIGHT_MODE = 0x05
TJC_CMD_PUMP_INTERVAL = 0x06
TJC_CMD_PUMP_DURATION = 0x07
TJC_CMD_CONTROL_MODE = 0x08
TJC_CMD_REST_SCHEDULE = 0x09

# MQTT-to-TJC synchronization components. These names intentionally have no
# page prefix: page0.bt0/page0.bt1 remain reserved for WiFi/MQTT status.
TJC_CONTROL_MODE_BUTTONS = ("bt10", "bt11")
TJC_FILL_LIGHT_MODE_BUTTONS = ("bt0", "bt1", "bt2", "bt3", "bt4")
TJC_RED_BRIGHTNESS_COMPONENT = "h0"
TJC_BLUE_BRIGHTNESS_COMPONENT = "h1"
TJC_LIGHT_MASTER_COMPONENT = "sw0"
TJC_PUMP_SWITCH_COMPONENT = "sw2"
TJC_REST_START_HOUR_COMPONENT = "n0"
TJC_REST_START_MINUTE_COMPONENT = "n1"
TJC_REST_END_HOUR_COMPONENT = "n2"
TJC_REST_END_MINUTE_COMPONENT = "n3"
TJC_PUMP_INTERVAL_COMPONENT = "n4"
TJC_PUMP_DURATION_COMPONENT = "n5"

CONTROL_MODE_MANUAL = 0
CONTROL_MODE_AI = 1

# The receive buffer allows one UART read to contain a partial frame or
# multiple consecutive frames.
tjc_receive_buffer = bytearray()

# TJC text component values. The data source can update these globals later.
air_temperature = 0.0          # t0: air temperature
air_humidity = 0.0             # t1: air humidity
light_intensity = 0            # t2: light intensity
hydroponic_temperature = 0.0   # t3: hydroponic temperature
water_tank_level = 0.0         # t4: water tank level
ph_value = 0.0                 # t5: pH
nutrient_ec = 0.0              # t6: nutrient solution EC

FILL_LIGHT_MODE_EMERGENCE = 1
FILL_LIGHT_MODE_STRONG_SEEDLING = 2
FILL_LIGHT_MODE_VEGETATIVE_GROWTH = 3
FILL_LIGHT_MODE_FLOWERING_FRUIT_SET = 4
FILL_LIGHT_MODE_FRUIT_EXPANSION = 5

# Initial red/blue output profiles for tomato growth stages.  These are LED
# channel percentages, rather than calibrated PPFD values, and are intended
# to be adjusted after on-site plant/light testing.
FILL_LIGHT_MODE_PROFILES = {
    FILL_LIGHT_MODE_EMERGENCE: (50, 50),
    FILL_LIGHT_MODE_STRONG_SEEDLING: (70, 70),
    FILL_LIGHT_MODE_VEGETATIVE_GROWTH: (80, 60),
    FILL_LIGHT_MODE_FLOWERING_FRUIT_SET: (90, 45),
    FILL_LIGHT_MODE_FRUIT_EXPANSION: (100, 35),
}

# The fill-light state remains registered.  Its buttons may reuse bt0..bt4
# on a different TJC page; page0.bt0/page0.bt1 remain WiFi/MQTT indicators.
fill_light_mode = FILL_LIGHT_MODE_EMERGENCE

# TJC/MQTT logical control values. Direct light and pump changes are serialized
# through the RS485 command queue after validation.
red_light_brightness = 0
blue_light_brightness = 0
pump_state = 0
light_master_state = 0
pump_interval_min = 0
pump_duration_sec = 0
control_mode = CONTROL_MODE_MANUAL

# CMD 09h rest schedule. If the end time is earlier than the start time, the
# interval crosses midnight, for example 20:12 to 07:22.
rest_start_hour = 0
rest_start_minute = 0
rest_end_hour = 0
rest_end_minute = 0


def apply_fill_light_mode_profile(mode):
    """Apply a stage profile to the logical red/blue light state."""
    global red_light_brightness, blue_light_brightness, light_master_state

    profile = FILL_LIGHT_MODE_PROFILES.get(mode)
    if profile is None:
        raise ValueError("unsupported fill light mode")

    red_light_brightness = profile[0]
    blue_light_brightness = profile[1]
    light_master_state = 1 if (
        red_light_brightness > 0 or blue_light_brightness > 0
    ) else 0
    return profile


def tjc_command_send(command):
    if isinstance(command, str):
        command = command.encode("utf-8")
    packet = command + TJC_COMMAND_END
    tjc_uart.write(packet)


def tjc_text_send(component, value):
    command = '{}.txt="{}"'.format(component, value)
    tjc_command_send(command)


def tjc_value_send(component, value):
    command = "{}.val={}".format(component, int(value))
    tjc_command_send(command)


def sync_mqtt_command_to_tjc(cmd):
    if cmd == "01":
        tjc_value_send(TJC_RED_BRIGHTNESS_COMPONENT, red_light_brightness)
        tjc_value_send(TJC_LIGHT_MASTER_COMPONENT, light_master_state)
        return

    if cmd == "02":
        tjc_value_send(TJC_BLUE_BRIGHTNESS_COMPONENT, blue_light_brightness)
        tjc_value_send(TJC_LIGHT_MASTER_COMPONENT, light_master_state)
        return

    if cmd == "03":
        tjc_value_send(TJC_PUMP_SWITCH_COMPONENT, pump_state)
        return

    if cmd == "04":
        tjc_value_send(TJC_LIGHT_MASTER_COMPONENT, light_master_state)
        tjc_value_send(TJC_RED_BRIGHTNESS_COMPONENT, red_light_brightness)
        tjc_value_send(TJC_BLUE_BRIGHTNESS_COMPONENT, blue_light_brightness)
        return

    if cmd == "08":
        # AI: bt10=0 and bt11=0; manual: bt10=1 and bt11=1.
        button_value = 0 if control_mode == CONTROL_MODE_AI else 1
        for component in TJC_CONTROL_MODE_BUTTONS:
            tjc_value_send(component, button_value)
        return

    if cmd == "05":
        # Modes 1..5 map to bt0..bt4.
        selected_index = fill_light_mode - 1
        for index, component in enumerate(TJC_FILL_LIGHT_MODE_BUTTONS):
            tjc_value_send(component, 1 if index == selected_index else 0)
        tjc_value_send(TJC_RED_BRIGHTNESS_COMPONENT, red_light_brightness)
        tjc_value_send(TJC_BLUE_BRIGHTNESS_COMPONENT, blue_light_brightness)
        tjc_value_send(TJC_LIGHT_MASTER_COMPONENT, light_master_state)
        return

    if cmd == "06":
        tjc_value_send(TJC_PUMP_INTERVAL_COMPONENT, pump_interval_min)
        return

    if cmd == "07":
        tjc_value_send(TJC_PUMP_DURATION_COMPONENT, pump_duration_sec)
        return

    if cmd == "09":
        tjc_value_send(TJC_REST_START_HOUR_COMPONENT, rest_start_hour)
        tjc_value_send(TJC_REST_START_MINUTE_COMPONENT, rest_start_minute)
        tjc_value_send(TJC_REST_END_HOUR_COMPONENT, rest_end_hour)
        tjc_value_send(TJC_REST_END_MINUTE_COMPONENT, rest_end_minute)


def _tjc_bytes_to_hex(data):
    return " ".join("{:02X}".format(value) for value in data)


def _tjc_frame_length(command):
    if command == TJC_CMD_REST_SCHEDULE:
        return TJC_REST_TIME_FRAME_LENGTH
    return TJC_BASE_FRAME_LENGTH


def _tjc_decode_u16(frame):
    return frame[3] | (frame[4] << 8)


def _tjc_value_in_range(name, value, minimum, maximum):
    if minimum <= value <= maximum:
        return True
    print(
        "TJC invalid {}: {} (expected {}..{})".format(
            name, value, minimum, maximum
        )
    )
    return False


def tjc_parse_frame(frame):
    global red_light_brightness, blue_light_brightness
    global pump_state, light_master_state, fill_light_mode
    global pump_interval_min, pump_duration_sec, control_mode
    global rest_start_hour, rest_start_minute
    global rest_end_hour, rest_end_minute

    if len(frame) < TJC_BASE_FRAME_LENGTH:
        print("TJC frame too short:", _tjc_bytes_to_hex(frame))
        return False
    if frame[0:2] != TJC_FRAME_HEADER or frame[-3:] != TJC_COMMAND_END:
        print("TJC invalid frame:", _tjc_bytes_to_hex(frame))
        return False

    command = frame[2]

    if command == TJC_CMD_REST_SCHEDULE:
        if len(frame) != TJC_REST_TIME_FRAME_LENGTH:
            print("TJC CMD 09 invalid length:", len(frame))
            return False

        start_hour = frame[3]
        start_minute = frame[4]
        end_hour = frame[5]
        end_minute = frame[6]

        if not _tjc_value_in_range("rest_start_hour", start_hour, 0, 23):
            return False
        if not _tjc_value_in_range("rest_start_minute", start_minute, 0, 59):
            return False
        if not _tjc_value_in_range("rest_end_hour", end_hour, 0, 23):
            return False
        if not _tjc_value_in_range("rest_end_minute", end_minute, 0, 59):
            return False

        rest_start_hour = start_hour
        rest_start_minute = start_minute
        rest_end_hour = end_hour
        rest_end_minute = end_minute

        crosses_midnight = (
            end_hour * 60 + end_minute
            < start_hour * 60 + start_minute
        )
        print(
            "TJC CMD 09 rest schedule: {:02d}:{:02d} -> {:02d}:{:02d}, "
            "crosses_midnight={}".format(
                rest_start_hour,
                rest_start_minute,
                rest_end_hour,
                rest_end_minute,
                crosses_midnight,
            )
        )
        return True

    if len(frame) != TJC_BASE_FRAME_LENGTH:
        print("TJC command invalid length:", command, len(frame))
        return False

    value = _tjc_decode_u16(frame)

    if (
        control_mode == CONTROL_MODE_AI
        and command in (
            TJC_CMD_RED_BRIGHTNESS,
            TJC_CMD_BLUE_BRIGHTNESS,
            TJC_CMD_PUMP_STATE,
            TJC_CMD_LIGHT_MASTER_STATE,
        )
    ):
        print(
            "TJC direct control rejected in AI mode: 0x{:02X}".format(
                command
            )
        )
        return False

    if command == TJC_CMD_RED_BRIGHTNESS:
        if not _tjc_value_in_range("red_light_brightness", value, 0, 100):
            return False
        red_light_brightness = value
        light_master_state = 1 if (
            red_light_brightness > 0 or blue_light_brightness > 0
        ) else 0
        queue_rs485_control_for_command("01")
        print("TJC CMD 01 red brightness:", value)
        return True

    if command == TJC_CMD_BLUE_BRIGHTNESS:
        if not _tjc_value_in_range("blue_light_brightness", value, 0, 100):
            return False
        blue_light_brightness = value
        light_master_state = 1 if (
            red_light_brightness > 0 or blue_light_brightness > 0
        ) else 0
        queue_rs485_control_for_command("02")
        print("TJC CMD 02 blue brightness:", value)
        return True

    if command == TJC_CMD_PUMP_STATE:
        if not _tjc_value_in_range("pump_state", value, 0, 1):
            return False
        pump_state = value
        queue_rs485_control_for_command("03")
        print("TJC CMD 03 pump state:", value)
        return True

    if command == TJC_CMD_LIGHT_MASTER_STATE:
        if not _tjc_value_in_range("light_master_state", value, 0, 1):
            return False
        light_master_state = value
        red_light_brightness = 100 if value else 0
        blue_light_brightness = 100 if value else 0
        queue_rs485_control_for_command("04")
        print("TJC CMD 04 light master state:", value)
        return True

    if command == TJC_CMD_FILL_LIGHT_MODE:
        if not _tjc_value_in_range("fill_light_mode", value, 1, 5):
            return False
        fill_light_mode = value
        red_value, blue_value = apply_fill_light_mode_profile(value)
        sync_mqtt_command_to_tjc("05")
        queue_rs485_control_for_command("05")
        print(
            "TJC CMD 05 fill light mode: {} red={} blue={}".format(
                value,
                red_value,
                blue_value,
            )
        )
        return True

    if command == TJC_CMD_PUMP_INTERVAL:
        pump_interval_min = value
        print("TJC CMD 06 pump interval minutes:", value)
        return True

    if command == TJC_CMD_PUMP_DURATION:
        pump_duration_sec = value
        print("TJC CMD 07 pump duration seconds:", value)
        return True

    if command == TJC_CMD_CONTROL_MODE:
        if not _tjc_value_in_range("control_mode", value, 0, 1):
            return False
        control_mode = value
        print("TJC CMD 08 control mode:", "AI" if value else "manual")
        return True

    print("TJC unknown command: 0x{:02X}".format(command))
    return False


def tjc_receive_data(data):
    global tjc_receive_buffer

    if not data:
        return

    tjc_receive_buffer.extend(data)

    while True:
        if len(tjc_receive_buffer) < 2:
            if tjc_receive_buffer and tjc_receive_buffer[0] != 0x55:
                tjc_receive_buffer = bytearray()
            return

        if (
            tjc_receive_buffer[0] != 0x55
            or tjc_receive_buffer[1] != 0xAA
        ):
            tjc_receive_buffer = tjc_receive_buffer[1:]
            continue

        if len(tjc_receive_buffer) < 3:
            return

        command = tjc_receive_buffer[2]
        frame_length = _tjc_frame_length(command)
        if len(tjc_receive_buffer) < frame_length:
            return

        if (
            tjc_receive_buffer[frame_length - 3:frame_length]
            != TJC_COMMAND_END
        ):
            print(
                "TJC RX invalid frame start:",
                _tjc_bytes_to_hex(tjc_receive_buffer[:frame_length]),
            )
            tjc_receive_buffer = tjc_receive_buffer[1:]
            continue

        frame = bytes(tjc_receive_buffer[:frame_length])
        tjc_receive_buffer = tjc_receive_buffer[frame_length:]
        print("TJC FRAME:", _tjc_bytes_to_hex(frame))
        if tjc_parse_frame(frame):
            mark_mqtt_state_dirty()


def send_connection_state_to_tjc(force=False):
    global previous_wifi_state, previous_mqtt_state

    if force or wifi_connected != previous_wifi_state:
        tjc_value_send(TJC_MAIN_PAGE + ".bt0", 1 if wifi_connected else 0)
        previous_wifi_state = wifi_connected

    if force or mqtt_connected != previous_mqtt_state:
        tjc_value_send(TJC_MAIN_PAGE + ".bt1", 1 if mqtt_connected else 0)
        previous_mqtt_state = mqtt_connected


def _tjc_sensor_values_for_display():
    return (
        air_temperature,
        air_humidity,
        light_intensity,
        hydroponic_temperature,
        water_tank_level,
        ph_value,
        nutrient_ec,
    )


def send_growing_data_to_tjc():
    values = _tjc_sensor_values_for_display()
    tjc_text_send(TJC_MAIN_PAGE + ".t0", "{:.1f}".format(values[0]))
    tjc_text_send(TJC_MAIN_PAGE + ".t1", "{:.1f}".format(values[1]))
    tjc_text_send(TJC_MAIN_PAGE + ".t2", str(int(values[2])))
    tjc_text_send(TJC_MAIN_PAGE + ".t3", "{:.1f}".format(values[3]))
    tjc_text_send(TJC_MAIN_PAGE + ".t4", "{:.1f}".format(values[4]))
    tjc_text_send(TJC_MAIN_PAGE + ".t5", "{:.2f}".format(values[5]))
    tjc_text_send(TJC_MAIN_PAGE + ".t6", "{:.2f}".format(values[6]))


async def tjc_loop():
    while tjc_uart.any():
        tjc_uart.read()

    await asyncio.sleep_ms(500)

    # TJC startup page command: b"page page0\xff\xff\xff"
    tjc_command_send("page page0")
    await asyncio.sleep_ms(100)
    send_connection_state_to_tjc(force=True)
    send_growing_data_to_tjc()

    last_data_send = utime.ticks_ms()

    while True:
        count = tjc_uart.any()
        if count:
            data = tjc_uart.read(count)
            if data:
                print("TJC RX:", data)
                tjc_receive_data(data)

        send_connection_state_to_tjc()

        now = utime.ticks_ms()
        if utime.ticks_diff(now, last_data_send) >= 1000:
            send_growing_data_to_tjc()
            last_data_send = now

        await asyncio.sleep_ms(20)


# ========== WiFi ==========

async def connect_wifi():
    global wifi_connected, wifi_connecting

    if wifi_connecting:
        while wifi_connecting:
            await asyncio.sleep_ms(200)
        return check_wifi()

    wifi_connecting = True
    try:
        if not station.isconnected():
            try:
                station.disconnect()
            except Exception:
                pass
            station.active(False)
            await asyncio.sleep_ms(300)
        station.active(True)
        await asyncio.sleep_ms(300)
        if station.isconnected():
            wifi_connected = True
            return True

        log("WiFi connecting to " + wifi_ssid)
        station.connect(wifi_ssid, wifi_password)

        attempt = 0
        while attempt < 15:
            if station.isconnected():
                break
            attempt += 1
            await asyncio.sleep(1)

        wifi_connected = station.isconnected()
        if wifi_connected:
            print("WiFi OK:", station.ifconfig())
        else:
            log("WiFi FAIL")
        return wifi_connected
    except Exception as exc:
        wifi_connected = False
        print("WiFi error:", exc)
        return False
    finally:
        wifi_connecting = False


def check_wifi():
    global wifi_connected
    try:
        wifi_connected = station.isconnected()
    except Exception:
        wifi_connected = False
    return wifi_connected


# ========== MQTT ==========

_MQTT_SUPPORTED_COMMANDS = (
    "01",
    "02",
    "03",
    "04",
    "05",
    "06",
    "07",
    "08",
    "09",
)

_MQTT_DIRECT_CONTROL_COMMANDS = ("01", "02", "03", "04")


def _rest_schedule_crosses_midnight():
    start_minutes = rest_start_hour * 60 + rest_start_minute
    end_minutes = rest_end_hour * 60 + rest_end_minute
    return end_minutes < start_minutes


def _mqtt_state_payload():
    return {
        "control_mode": control_mode,
        "red_brightness": red_light_brightness,
        "blue_brightness": blue_light_brightness,
        "pump_state": pump_state,
        "light_master_state": light_master_state,
        "fill_light_mode": fill_light_mode,
        "pump_interval_min": pump_interval_min,
        "pump_duration_sec": pump_duration_sec,
        "rest_schedule": {
            "start_hour": rest_start_hour,
            "start_minute": rest_start_minute,
            "end_hour": rest_end_hour,
            "end_minute": rest_end_minute,
            "crosses_midnight": _rest_schedule_crosses_midnight(),
        },
    }


def _mqtt_telemetry_payload():
    return {
        "air_temperature": air_temperature,
        "air_humidity": air_humidity,
        "light_intensity": light_intensity,
        "hydroponic_temperature": hydroponic_temperature,
        "water_tank_level": water_tank_level,
        "ph": ph_value,
        "ec": nutrient_ec,
    }


def _mqtt_publish_with_client(client, topic, payload, retain=False, qos=0):
    encoded = ujson.dumps(payload).encode("utf-8")
    client.publish(topic, encoded, retain=retain, qos=qos)


def _mqtt_publish_json(topic, payload, retain=False, qos=0):
    global mqtt_connected

    if not mqtt_connected or mqtt_client is None:
        return False

    try:
        _mqtt_publish_with_client(
            mqtt_client,
            topic,
            payload,
            retain=retain,
            qos=qos,
        )
        return True
    except Exception as exc:
        mqtt_connected = False
        print("MQTT publish error:", topic, exc)
        return False


def mark_mqtt_state_dirty():
    global mqtt_state_dirty
    mqtt_state_dirty = True


def mqtt_publish_state(force=False):
    global mqtt_state_dirty

    if not force and not mqtt_state_dirty:
        return True

    if _mqtt_publish_json(
        TOPIC_STATE,
        _mqtt_state_payload(),
        retain=True,
        qos=1,
    ):
        mqtt_state_dirty = False
        return True
    return False


def mqtt_publish_telemetry():
    return _mqtt_publish_json(
        TOPIC_TELEMETRY,
        _mqtt_telemetry_payload(),
        retain=False,
        qos=0,
    )


def _mqtt_publish_error(request_id, cmd, error, message, extra=None):
    payload = {
        "request_id": request_id,
        "cmd": cmd,
        "success": False,
        "applied": False,
        "error": error,
        "message": message,
    }
    if extra:
        payload.update(extra)
    return _mqtt_publish_json(TOPIC_RESULT, payload, retain=False, qos=1)


def _mqtt_publish_success(request_id, cmd, data, message):
    return _mqtt_publish_json(
        TOPIC_RESULT,
        {
            "request_id": request_id,
            "cmd": cmd,
            "success": True,
            "applied": True,
            "data": data,
            "message": message,
        },
        retain=False,
        qos=1,
    )


def _mqtt_integer_value(data, field, minimum, maximum, range_error):
    if field not in data:
        return None, "MISSING_FIELD", "missing field: " + field

    value = data[field]
    if type(value) is not int:
        return None, range_error, field + " must be an integer"
    if value < minimum or value > maximum:
        return (
            None,
            range_error,
            "{} must be between {} and {}".format(
                field, minimum, maximum
            ),
        )
    return value, None, None


def _mqtt_apply_command(cmd, data):
    global red_light_brightness, blue_light_brightness
    global pump_state, light_master_state, fill_light_mode
    global pump_interval_min, pump_duration_sec, control_mode
    global rest_start_hour, rest_start_minute
    global rest_end_hour, rest_end_minute

    if cmd in _MQTT_DIRECT_CONTROL_COMMANDS and control_mode == CONTROL_MODE_AI:
        return (
            False,
            None,
            None,
            "MANUAL_MODE_REQUIRED",
            "direct control is only allowed in manual mode",
        )

    if cmd == "09":
        values = {}
        for field in (
            "start_hour",
            "start_minute",
            "end_hour",
            "end_minute",
        ):
            maximum = 23 if field.endswith("hour") else 59
            value, error, message = _mqtt_integer_value(
                data,
                field,
                0,
                maximum,
                "INVALID_TIME",
            )
            if error:
                return False, None, None, error, message
            values[field] = value

        rest_start_hour = values["start_hour"]
        rest_start_minute = values["start_minute"]
        rest_end_hour = values["end_hour"]
        rest_end_minute = values["end_minute"]

        result = {
            "start_hour": rest_start_hour,
            "start_minute": rest_start_minute,
            "end_hour": rest_end_hour,
            "end_minute": rest_end_minute,
            "crosses_midnight": _rest_schedule_crosses_midnight(),
        }
        return True, result, "rest schedule updated", None, None

    limits = {
        "01": (0, 100),
        "02": (0, 100),
        "03": (0, 1),
        "04": (0, 1),
        "05": (1, 5),
        "06": (0, 65535),
        "07": (0, 65535),
        "08": (0, 1),
    }
    minimum, maximum = limits[cmd]
    value, error, error_message = _mqtt_integer_value(
        data,
        "value",
        minimum,
        maximum,
        "VALUE_OUT_OF_RANGE",
    )
    if error:
        return False, None, None, error, error_message

    if cmd == "01":
        red_light_brightness = value
        light_master_state = 1 if (
            red_light_brightness > 0 or blue_light_brightness > 0
        ) else 0
        message = "red brightness updated"
    elif cmd == "02":
        blue_light_brightness = value
        light_master_state = 1 if (
            red_light_brightness > 0 or blue_light_brightness > 0
        ) else 0
        message = "blue brightness updated"
    elif cmd == "03":
        pump_state = value
        message = "pump state updated"
    elif cmd == "04":
        light_master_state = value
        red_light_brightness = 100 if value else 0
        blue_light_brightness = 100 if value else 0
        message = "light master state updated"
    elif cmd == "05":
        fill_light_mode = value
        apply_fill_light_mode_profile(value)
        message = "fill light mode updated"
    elif cmd == "06":
        pump_interval_min = value
        message = "pump interval updated"
    elif cmd == "07":
        pump_duration_sec = value
        message = "pump duration updated"
    else:
        control_mode = value
        message = "control mode updated"

    result = {"value": value}
    if cmd == "05":
        result["red_brightness"] = red_light_brightness
        result["blue_brightness"] = blue_light_brightness
        result["light_master_state"] = light_master_state
    return True, result, message, None, None


def mqtt_message_callback(topic, message):
    if topic != TOPIC_SET:
        return

    print("MQTT RX:", topic, message)
    request_id = ""
    cmd = ""
    try:
        try:
            text = (
                message.decode("utf-8")
                if isinstance(message, bytes)
                else message
            )
            parsed = ujson.loads(text)
        except Exception:
            _mqtt_publish_error(
                request_id,
                cmd,
                "INVALID_JSON",
                "MQTT payload is not valid JSON",
            )
            return

        if not isinstance(parsed, dict):
            _mqtt_publish_error(
                request_id,
                cmd,
                "INVALID_JSON",
                "MQTT payload must be a JSON object",
            )
            return

        raw_request_id = parsed.get("request_id")
        raw_cmd = parsed.get("cmd")
        data = parsed.get("data")

        if isinstance(raw_request_id, str):
            request_id = raw_request_id
        if isinstance(raw_cmd, str):
            cmd = raw_cmd

        if not request_id:
            _mqtt_publish_error(
                request_id,
                cmd,
                "MISSING_FIELD",
                "request_id must be a non-empty string",
            )
            return
        if not cmd:
            _mqtt_publish_error(
                request_id,
                cmd,
                "MISSING_FIELD",
                "cmd must be a non-empty string",
            )
            return
        if not isinstance(data, dict):
            _mqtt_publish_error(
                request_id,
                cmd,
                "MISSING_FIELD",
                "data must be a JSON object",
            )
            return
        if cmd not in _MQTT_SUPPORTED_COMMANDS:
            _mqtt_publish_error(
                request_id,
                cmd,
                "UNKNOWN_COMMAND",
                "CMD is not defined or supported",
            )
            return

        success, result_data, success_message, error, error_message = (
            _mqtt_apply_command(cmd, data)
        )
        if not success:
            extra = None
            if error == "MANUAL_MODE_REQUIRED":
                extra = {"current_mode": control_mode}
            _mqtt_publish_error(
                request_id,
                cmd,
                error,
                error_message,
                extra=extra,
            )
            return

        print("MQTT command applied:", cmd, result_data)
        sync_mqtt_command_to_tjc(cmd)
        queue_rs485_control_for_command(cmd)
        mark_mqtt_state_dirty()
        _mqtt_publish_success(
            request_id,
            cmd,
            result_data,
            success_message,
        )
        mqtt_publish_state(force=True)
    except Exception as exc:
        print("MQTT callback error:", exc)
        _mqtt_publish_error(
            request_id,
            cmd,
            "INTERNAL_ERROR",
            "ESP32 internal processing error",
        )


def _mqtt_connect_thread():
    global mqtt_client, mqtt_connected, mqtt_connecting, mqtt_state_dirty

    new_client = None
    broker_connected = False
    try:
        client_suffix = ubinascii.hexlify(machine.unique_id()).decode()
        client_id = ("tomato-esp32s3-" + client_suffix).encode("utf-8")
        user_bytes = mqtt_user.encode("utf-8") if mqtt_user else None
        password_bytes = (
            mqtt_password.encode("utf-8") if mqtt_password else None
        )
        new_client = MQTTClient(
            client_id=client_id,
            server=mqtt_server,
            port=MQTT_PORT,
            user=user_bytes,
            password=password_bytes,
            keepalive=MQTT_KEEPALIVE,
        )
        new_client.set_callback(mqtt_message_callback)
        new_client.set_last_will(
            TOPIC_AVAILABILITY,
            ujson.dumps({"status": "offline"}).encode("utf-8"),
            retain=True,
            qos=1,
        )
        new_client.connect()
        broker_connected = True
        new_client.subscribe(TOPIC_SET, qos=1)

        _mqtt_publish_with_client(
            new_client,
            TOPIC_AVAILABILITY,
            {"status": "online"},
            retain=True,
            qos=1,
        )
        _mqtt_publish_with_client(
            new_client,
            TOPIC_STATE,
            _mqtt_state_payload(),
            retain=True,
            qos=1,
        )

        mqtt_client = new_client
        mqtt_state_dirty = False
        mqtt_connected = True
        log("MQTT OK: " + mqtt_server)
        print("MQTT subscribed:", TOPIC_SET)
    except Exception as exc:
        mqtt_connected = False
        if new_client is not None:
            if broker_connected:
                try:
                    _mqtt_publish_with_client(
                        new_client,
                        TOPIC_AVAILABILITY,
                        {"status": "offline"},
                        retain=True,
                        qos=1,
                    )
                except Exception:
                    pass
            try:
                new_client.disconnect()
            except Exception:
                pass
        print("MQTT FAIL:", mqtt_server, exc)
    finally:
        mqtt_connecting = False


def start_mqtt_connect():
    global mqtt_connecting

    if mqtt_connecting or not wifi_connected:
        return

    mqtt_connecting = True
    log("MQTT connecting to " + mqtt_server)
    try:
        try:
            _thread.stack_size(6144)
        except Exception:
            pass
        _thread.start_new_thread(_mqtt_connect_thread, ())
    except Exception as exc:
        mqtt_connecting = False
        print("MQTT thread error:", exc)


def check_mqtt():
    global mqtt_connected

    if mqtt_client is None:
        mqtt_connected = False
        return False

    try:
        mqtt_client.ping()
        mqtt_connected = True
        return True
    except Exception:
        mqtt_connected = False
        mark_mqtt_state_dirty()
        return False


def mqtt_disconnect():
    global mqtt_client, mqtt_connected, mqtt_connecting

    client = mqtt_client
    if client is not None:
        if mqtt_connected:
            try:
                _mqtt_publish_with_client(
                    client,
                    TOPIC_AVAILABILITY,
                    {"status": "offline"},
                    retain=True,
                    qos=1,
                )
            except Exception as exc:
                print("MQTT offline publish error:", exc)
        try:
            client.disconnect()
        except Exception:
            pass

    mqtt_client = None
    mqtt_connected = False
    mqtt_connecting = False
    mark_mqtt_state_dirty()


async def check_and_reconnect():
    global last_reconnect_attempt, mqtt_connected

    if not network_startup_ready:
        return False

    now = utime.ticks_ms()
    if utime.ticks_diff(now, last_reconnect_attempt) <= RECONNECT_INTERVAL_MS:
        return wifi_connected and mqtt_connected

    last_reconnect_attempt = now

    if not check_wifi():
        mqtt_connected = False
        if await connect_wifi():
            start_mqtt_connect()
        return False

    if not check_mqtt():
        log("MQTT lost, reconnecting...")
        start_mqtt_connect()
        return False

    return True


async def mqtt_message_loop():
    global mqtt_connected

    last_telemetry_publish = utime.ticks_ms()
    while True:
        try:
            if mqtt_connected and mqtt_client is not None:
                mqtt_client.check_msg()
                mqtt_publish_state()

                now = utime.ticks_ms()
                if (
                    utime.ticks_diff(now, last_telemetry_publish)
                    >= MQTT_TELEMETRY_INTERVAL_MS
                ):
                    if mqtt_publish_telemetry():
                        last_telemetry_publish = now
            await asyncio.sleep_ms(200)
        except Exception as exc:
            print("MQTT check error:", exc)
            mqtt_connected = False
            mark_mqtt_state_dirty()
            await asyncio.sleep(2)


# ========== AP configuration web server ==========

def _html_escape(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(
        ">", "&gt;"
    ).replace('"', "&quot;")


def _config_html():
    return ("HTTP/1.1 200 OK\r\nContent-Type:text/html;"
            "charset=utf-8\r\nConnection:close\r\n\r\n"
            "<!doctype html><meta charset=utf-8><meta name=viewport "
            "content='width=device-width,initial-scale=1'><title>Tomato "
            "Config</title><style>body{{font:15px Arial;padding:20px;"
            "background:#f4f9f4}}main{{max-width:480px;margin:auto;"
            "background:white;padding:20px;border-radius:12px}}label{{"
            "display:block;margin-top:12px}}input,button{{width:100%;"
            "padding:10px;box-sizing:border-box}}button{{margin-top:16px;"
            "background:#40916c;color:white;border:0}}</style><main><h2>"
            "Tomato Config</h2><form method=post action=/save><label>WiFi "
            "SSID</label><input name=ssid value='{ssid}'><label>WiFi "
            "Password</label><input type=password name=pwd value='{wifi_pwd}'>"
            "<label>MQTT Server</label><input name=mqtt value='{mqtt}'>"
            "<label>MQTT User</label><input name=mqtt_user value='{mqtt_user}'>"
            "<label>MQTT Password</label><input type=password name=mqtt_pwd "
            "value='{mqtt_pwd}'><button>Save &amp; Reboot</button></form></main>"
            ).format(
        ssid=_html_escape(_config.get("wifi_ssid", wifi_ssid)),
        wifi_pwd=_html_escape(_config.get("wifi_pwd", wifi_password)),
        mqtt=_html_escape(_config.get("mqtt_server", mqtt_server)),
        mqtt_user=_html_escape(_config.get("mqtt_user", mqtt_user)),
        mqtt_pwd=_html_escape(_config.get("mqtt_password", mqtt_password)),
    )


def _saved_html():
    return ("HTTP/1.1 200 OK\r\nContent-Type:text/html;charset=utf-8\r\n"
            "Connection:close\r\n\r\n<meta charset=utf-8><body style='font:"
            "16px Arial;text-align:center;padding:40px'><h2>Saved</h2>"
            "Rebooting...</body>")


def _url_decode(value):
    value = value.replace("+", " ")
    output = bytearray()
    index = 0

    while index < len(value):
        if value[index] == "%" and index + 2 < len(value):
            try:
                output.append(int(value[index + 1:index + 3], 16))
                index += 3
                continue
            except Exception:
                pass
        output.extend(value[index].encode("utf-8"))
        index += 1

    return bytes(output).decode("utf-8", "ignore")


def _parse_form(body):
    parameters = {}
    try:
        for pair in body.split("&"):
            if "=" not in pair:
                continue
            key, value = pair.split("=", 1)
            parameters[_url_decode(key)] = _url_decode(value)
    except Exception as exc:
        print("Form parse error:", exc)
    return parameters


async def _send_all(connection, data):
    sent = 0
    while sent < len(data):
        try:
            count = connection.send(data[sent:])
            if not count:
                return False
            sent += count
        except OSError:
            await asyncio.sleep_ms(20)
    return True


async def _handle_http(connection):
    try:
        try:
            connection.setblocking(False)
        except Exception:
            pass

        request = b""
        attempts = 0
        while b"\r\n\r\n" not in request and attempts < 100:
            try:
                chunk = connection.recv(256)
                if chunk:
                    request += chunk
                elif chunk == b"":
                    break
            except OSError:
                pass
            attempts += 1
            await asyncio.sleep_ms(20)

        if b"\r\n\r\n" not in request:
            return

        header_bytes, body_bytes = request.split(b"\r\n\r\n", 1)
        header = header_bytes.decode("utf-8", "ignore")
        first_line = header.split("\r\n", 1)[0]
        parts = first_line.split(" ")
        method = parts[0] if parts else "GET"
        path = parts[1] if len(parts) > 1 else "/"

        content_length = 0
        for line in header.split("\r\n"):
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                except Exception:
                    content_length = 0
                break

        attempts = 0
        while len(body_bytes) < content_length and attempts < 100:
            try:
                chunk = connection.recv(256)
                if chunk:
                    body_bytes += chunk
                elif chunk == b"":
                    break
            except OSError:
                pass
            attempts += 1
            await asyncio.sleep_ms(20)

        if method == "GET" and path in ("/", "/index.html"):
            await _send_all(connection, _config_html().encode("utf-8"))
            return

        if method == "POST" and path == "/save":
            parameters = _parse_form(
                body_bytes[:content_length].decode("utf-8", "ignore")
            )
            if parameters:
                _config["wifi_ssid"] = parameters.get(
                    "ssid", _config.get("wifi_ssid", "")
                )
                _config["wifi_pwd"] = parameters.get(
                    "pwd", _config.get("wifi_pwd", "")
                )
                _config["mqtt_server"] = parameters.get(
                    "mqtt", _config.get("mqtt_server", "")
                )
                _config["mqtt_user"] = parameters.get(
                    "mqtt_user", _config.get("mqtt_user", "")
                )
                _config["mqtt_password"] = parameters.get(
                    "mqtt_pwd", _config.get("mqtt_password", "")
                )

                if not save_config(_config):
                    await _send_all(
                        connection,
                        b"HTTP/1.1 500 Internal Server Error\r\nConnection: close\r\n\r\nSave failed",
                    )
                    return

            await _send_all(connection, _saved_html().encode("utf-8"))
            await asyncio.sleep(2)
            machine.reset()

        await _send_all(
            connection,
            b"HTTP/1.1 302 Found\r\nLocation: /\r\nConnection: close\r\n\r\n",
        )
    except Exception as exc:
        print("HTTP error:", exc)
    finally:
        try:
            connection.close()
        except Exception:
            pass


async def config_web_server(enable_access_point):
    global config_ap_active, config_ap_ready

    access_point = None
    page_ip = AP_IP

    if enable_access_point:
        # ESP32-S3 runs this configuration AP together with STA mode, so the
        # phone can always change WiFi or MQTT settings at 192.168.4.1.
        config_ap_active = True
        access_point = network.WLAN(network.AP_IF)
        ap_stage = "activate"
        try:
            access_point.active(True)
            await asyncio.sleep_ms(500)
            # This firmware rejects AP config writes while AP_IF is inactive
            # with "Wifi Invalid Mode", so configure it only after activation.
            ap_stage = "configure"
            access_point.config(essid=AP_SSID, password=AP_PWD)
            ap_stage = "set IP"
            access_point.ifconfig(
                (AP_IP, "255.255.255.0", AP_IP, AP_IP)
            )
        except Exception as exc:
            config_ap_active = False
            config_ap_ready = True
            print("AP start error at " + ap_stage + ":", exc)
            return

        print("AP:", AP_SSID, access_point.ifconfig())
    else:
        config_ap_active = False
        try:
            page_ip = station.ifconfig()[0]
        except Exception:
            page_ip = "0.0.0.0"

    config_ap_ready = True
    print("Config page: http://" + page_ip)

    while True:
        server = None
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                server.setsockopt(
                    socket.SOL_SOCKET,
                    socket.SO_REUSEADDR,
                    1,
                )
            except Exception:
                pass

            server.bind(("0.0.0.0", 80))
            server.listen(3)
            server.setblocking(False)
            log("Web server started")

            while True:
                try:
                    connection, _address = server.accept()
                    asyncio.create_task(_handle_http(connection))
                except OSError:
                    pass
                await asyncio.sleep_ms(100)
        except OSError as exc:
            print("Web server socket retry:", exc)
        except Exception as exc:
            print("Web server error:", exc)
        finally:
            if server is not None:
                try:
                    server.close()
                except Exception:
                    pass

        await asyncio.sleep(2)


# ========== Main tasks ==========

async def initial_network_connect():
    global wifi_connected, network_startup_ready

    # The ESP32-S3 supports AP+STA mode.  Let the configuration task create
    # A-tomato first, then connect to the user's router without disabling AP.
    while not config_ap_ready:
        await asyncio.sleep_ms(50)

    print("WiFi mode: AP+STA")
    wifi_connected = await connect_wifi()
    network_startup_ready = True

    if wifi_connected:
        start_mqtt_connect()
    else:
        print("WiFi unavailable; A-tomato AP remains available for configuration")


async def main_loop():
    # Keep the configuration hotspot available even after STA/MQTT succeeds.
    asyncio.create_task(config_web_server(True))
    asyncio.create_task(initial_network_connect())
    asyncio.create_task(mqtt_message_loop())
    asyncio.create_task(tjc_loop())
    asyncio.create_task(rs485_loop())

    while True:
        try:
            await check_and_reconnect()
            await asyncio.sleep(1)
        except Exception as exc:
            print("Main loop error:", exc)
            await asyncio.sleep(2)


def main():
    print("=" * 40)
    print("Tomato controller: ESP32-S3 MicroPython")
    print("Build:", APP_BUILD)
    print("WiFi SSID:", wifi_ssid)
    print("MQTT server:", mqtt_server)
    print("MQTT topic root:", MQTT_TOPIC_ROOT)
    print("AP SSID:", AP_SSID)
    print("TJC: hardware UART1, TX=GPIO9 RX=GPIO8, 9600 8N1")
    print("RS485: hardware UART2, TX=GPIO4 RX=GPIO5, 9600 8N1")
    print("UART0: reserved for Thonny/USB serial debug")
    print("=" * 40)

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        log("Stopped by user")
    except Exception as exc:
        print("Fatal error:", exc)
        utime.sleep(2)
        machine.reset()
    finally:
        mqtt_disconnect()
        try:
            asyncio.new_event_loop()
        except Exception:
            pass


if __name__ == "__main__":
    main()
