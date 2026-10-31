"""MQTT 控制指令监听 — 验证前端按钮发出的指令是否正确到达 Broker"""
import json
import os
import time

import paho.mqtt.client as mqtt

BROKER_URL = os.environ.get("MQTT_BROKER_URL", "broker.emqx.io")
BROKER_PORT = int(os.environ.get("MQTT_BROKER_PORT", "1883"))
BROKER_USERNAME = os.environ.get("MQTT_BROKER_USERNAME", "admin")
BROKER_PASSWORD = os.environ.get("MQTT_BROKER_PASSWORD", "admin123")
TOPIC_ROOT = os.environ.get("MQTT_TOPIC_ROOT", "tomato_hnsw0001").strip().strip("/")

TOPICS = [
    (f"{TOPIC_ROOT}/set", 1),
    (f"{TOPIC_ROOT}/result", 1),
    (f"{TOPIC_ROOT}/state", 1),
    (f"{TOPIC_ROOT}/telemetry", 0),
    (f"{TOPIC_ROOT}/availability", 1),
]


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        client.subscribe(TOPICS)
        print(f"✅ 已连接 {BROKER_URL}:{BROKER_PORT}")
        print(f"   监听: {TOPIC_ROOT}/set | result | state | telemetry | availability")
        print("   等待平台和 ESP32 MQTT 消息...\n")
    else:
        print(f"❌ 连接失败: {reason_code}")


def on_message(client, userdata, msg: mqtt.MQTTMessage):
    ts = time.strftime("%H:%M:%S")
    try:
        payload = json.loads(msg.payload.decode("utf-8"))
        print(f"[{ts}] 📩 {msg.topic} → {json.dumps(payload, ensure_ascii=False)}")
    except json.JSONDecodeError:
        print(f"[{ts}] 📩 {msg.topic} → {msg.payload}")


def main():
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"yuxi-monitor-{int(time.time())}"
    )
    client.username_pw_set(BROKER_USERNAME, BROKER_PASSWORD)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER_URL, BROKER_PORT, 120)
    client.loop_forever()


if __name__ == "__main__":
    main()
