"""Validation and export shared by history queries and future backup jobs."""

import csv
import io
import os
from datetime import datetime, UTC
from zoneinfo import ZoneInfo

from yuxi.repositories.sensor_history_repository import sensor_history_repository

EXPORT_LIMIT = 50000
SENSOR_COLUMNS = (
    ("temp", "air_temperature_C"),
    ("humidity", "air_humidity_percent"),
    ("co2", "co2_ppm"),
    ("illumination", "illumination_lx"),
    ("soil_temperature", "soil_temperature_C"),
    ("soil_moisture", "soil_moisture_percent"),
    ("soil_conductivity", "conductivity_raw"),
    ("ph_value", "ph"),
    ("water_tank_level", "water_tank_level_cm"),
    ("nitrogen", "nitrogen_raw"),
    ("phosphorus", "phosphorus_raw"),
    ("potassium", "potassium_raw"),
)


def normalize_sample_time(value: datetime) -> datetime:
    # Legacy firmware timestamps are local wall time, not UTC.
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZoneInfo(os.getenv("SENSOR_TIMEZONE", "Asia/Shanghai")))
    return value.astimezone(UTC)


async def persist_sample(kind, data):
    device_id = os.getenv("MQTT_SENSOR_DEVICE_ID", "").strip()
    if not device_id:
        device_id = (
            "strawberry-local"
            if os.getenv("MQTT_PROTOCOL", "strawberry") == "strawberry"
            else os.getenv("MQTT_TOPIC_ROOT", "tomato_hnsw0001")
        )
    if not device_id or len(device_id) > 128:
        raise ValueError("MQTT_SENSOR_DEVICE_ID must contain 1-128 characters")
    await sensor_history_repository.append(
        device_id=device_id,
        kind=kind,
        sampled_at=normalize_sample_time(data.timestamp),
        values=data.model_dump(mode="json", exclude_unset=True, exclude={"timestamp"}),
    )


def validate_range(start, end):
    for value in (start, end):
        if value is not None and value.tzinfo is None:
            raise ValueError("查询时间必须包含时区")
    if start is not None and end is not None and start > end:
        raise ValueError("开始时间不能晚于结束时间")


def history_csv(items):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["id", "device_id", "kind", "sampled_at", "received_at", *[label for _, label in SENSOR_COLUMNS]])
    for item in items:
        # Device identifiers are configurable text; neutralize spreadsheet formulas.
        device_id = item["device_id"]
        if device_id.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
            device_id = "'" + device_id
        writer.writerow(
            [
                item["id"],
                device_id,
                item["kind"],
                item["sampled_at"],
                item["received_at"],
                *[item["values"].get(key, "") for key, _ in SENSOR_COLUMNS],
            ]
        )
    return output.getvalue().encode("utf-8-sig")
