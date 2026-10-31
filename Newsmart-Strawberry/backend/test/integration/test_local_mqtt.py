"""Opt-in local broker smoke test. Never uses hardware command or sensor topics."""

import json
import os
import threading
import uuid
from pathlib import Path

import paho.mqtt.client as mqtt
import pytest


@pytest.mark.skipif(not os.getenv("MQTT_TEST_LAN_HOST"), reason="Requires running local MQTT and LAN IP")
def test_authenticated_lan_and_loopback_bridge():
    host = os.environ["MQTT_TEST_LAN_HOST"]
    credentials = json.loads(
        (Path(__file__).resolve().parents[3] / ".runtime/mqtt-device.json").read_text(encoding="utf-8")
    )
    topic = f"strawberry-test/{uuid.uuid4()}"
    clients = []

    def connect(address, port, username=None, password=None):
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        if username:
            client.username_pw_set(username, password)
        event = threading.Event()
        outcome = []

        def on_connect(client, userdata, flags, reason, properties):
            outcome.append(not reason.is_failure)
            event.set()

        def on_disconnect(client, userdata, flags, reason, properties):
            event.set()

        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        clients.append(client)
        client.connect(address, port, keepalive=10)
        client.loop_start()
        assert event.wait(5), "Broker did not respond"
        return client, bool(outcome and outcome[0])

    try:
        local, accepted = connect("127.0.0.1", 11883)
        assert accepted
        subscribed = threading.Event()
        received = threading.Event()
        local.on_subscribe = lambda *args: subscribed.set()
        local.on_message = lambda client, userdata, message: received.set() if message.payload == b"probe" else None
        local.subscribe(topic)
        assert subscribed.wait(5)
        hardware, accepted = connect(host, 1883, **credentials)
        assert accepted
        hardware.publish(topic, "probe", qos=0, retain=False).wait_for_publish(5)
        assert received.wait(5), "LAN and loopback must share a broker"
        _, accepted = connect(host, 1883)
        assert not accepted, "Anonymous LAN clients must be rejected"
        _, accepted = connect(host, 1883, credentials["username"], "incorrect-password")
        assert not accepted, "Invalid credentials must be rejected"
    finally:
        for client in clients:
            client.disconnect()
            client.loop_stop()
