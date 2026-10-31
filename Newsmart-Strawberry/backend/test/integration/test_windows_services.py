import os
import threading
import uuid
from pathlib import Path

import httpx
import paho.mqtt.client as mqtt
import pytest
import redis
from dotenv import dotenv_values


pytestmark = pytest.mark.integration


@pytest.fixture
def local_settings(monkeypatch):
    if os.getenv("TEST_WINDOWS_LOCAL") != "1":
        pytest.skip("Set TEST_WINDOWS_LOCAL=1 for native Windows service tests")
    settings = dotenv_values(Path(__file__).resolve().parents[3] / ".runtime/local.env")
    for key, value in settings.items():
        monkeypatch.setenv(key, value)
    return settings


def test_redis_roundtrip(local_settings):
    client = redis.Redis.from_url(local_settings["REDIS_URL"])
    key = f"test:{uuid.uuid4().hex}"
    try:
        assert client.ping()
        client.set(key, "windows-local", ex=30)
        assert client.get(key) == b"windows-local"
    finally:
        client.delete(key)
        client.close()


def test_s3_public_upload_download_delete(local_settings):
    from yuxi.storage.minio.client import MinIOClient

    client = MinIOClient()
    key = f"local-test/{uuid.uuid4().hex}.txt"
    payload = b"native Windows S3 test"
    try:
        result = client.upload_file("public", key, payload, "text/plain")
        assert client.download_file("public", key) == payload
        response = httpx.get(result.url, timeout=15)
        assert response.status_code == 200
        assert response.content == payload
        assert httpx.get(client.get_presigned_url("public", key), timeout=15).content == payload
    finally:
        client.delete_file("public", key)


def test_mqtt_publish_subscribe_without_hardware_topics(local_settings):
    topic = f"local-test/{uuid.uuid4().hex}"
    received = threading.Event()
    payloads = []
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def subscribed(client, userdata, mid, reasons, properties):
        client.publish(topic, "local-test", qos=1)

    def message(client, userdata, msg):
        payloads.append(msg.payload)
        received.set()

    client.on_connect = lambda client, userdata, flags, reason, properties: client.subscribe(topic, qos=1)
    client.on_subscribe = subscribed
    client.on_message = message
    try:
        client.connect("127.0.0.1", int(local_settings["MQTT_BROKER_PORT"]))
        client.loop_start()
        assert received.wait(10), "MQTT message was not delivered"
        assert payloads == [b"local-test"]
    finally:
        client.disconnect()
        client.loop_stop()


def test_api_login_and_business_reads_with_temporary_user(local_settings):
    import secrets

    import psycopg
    from yuxi.utils.auth_utils import AuthUtils

    uid = "test_" + uuid.uuid4().hex[:12]
    password = secrets.token_urlsafe(24)
    conninfo = local_settings["POSTGRES_URL"].replace("+asyncpg", "")
    with psycopg.connect(conninfo, autocommit=True) as conn, httpx.Client(
        base_url="http://127.0.0.1:5050", timeout=20
    ) as client:
        department_id = conn.execute(
            "INSERT INTO departments (name, created_at) VALUES (%s, CURRENT_TIMESTAMP) RETURNING id", (uid,)
        ).fetchone()[0]
        user_id = conn.execute(
            "INSERT INTO users (username, uid, password_hash, role, created_at, "
            "login_failed_count, is_deleted, department_id) "
            "VALUES (%s, %s, %s, 'superadmin', CURRENT_TIMESTAMP, 0, 0, %s) RETURNING id",
            (uid, uid, AuthUtils.hash_password(password), department_id),
        ).fetchone()[0]
        try:
            bad = client.post("/api/auth/token", data={"username": uid, "password": "incorrect"})
            assert bad.status_code == 401
            login = client.post("/api/auth/token", data={"username": uid, "password": password})
            assert login.status_code == 200, login.text
            assert login.json()["uid"] == uid
            client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
            assert client.get("/api/auth/me").json()["uid"] == uid
            for path in ("/api/iot/dashboard", "/api/detect/stats", "/api/trace/plot/list"):
                response = client.get(path)
                assert response.status_code == 200, (path, response.text)
                assert isinstance(response.json(), (dict, list))
        finally:
            conn.execute("DELETE FROM operation_logs WHERE user_id = %s", (user_id,))
            conn.execute("DELETE FROM users WHERE id = %s AND uid = %s", (user_id, uid))
            conn.execute("DELETE FROM departments WHERE id = %s", (department_id,))
