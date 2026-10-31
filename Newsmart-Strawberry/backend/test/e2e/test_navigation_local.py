import os
import secrets
import subprocess
import uuid
from pathlib import Path

import httpx
import psycopg
import pytest
from dotenv import dotenv_values


@pytest.mark.e2e
def test_local_menu_navigation(monkeypatch):
    if os.getenv("TEST_WINDOWS_LOCAL") != "1":
        pytest.skip("Requires local Windows services")
    root = Path(__file__).resolve().parents[3]
    settings = dotenv_values(root / ".runtime/local.env")
    for key, value in settings.items():
        monkeypatch.setenv(key, value)
    from yuxi.utils.auth_utils import AuthUtils

    uid = "nav_" + uuid.uuid4().hex[:12]
    password = secrets.token_urlsafe(24)
    with psycopg.connect(settings["POSTGRES_URL"].replace("+asyncpg", ""), autocommit=True) as conn:
        dept = conn.execute(
            "INSERT INTO departments (name, created_at) VALUES (%s, CURRENT_TIMESTAMP) RETURNING id", (uid,)
        ).fetchone()[0]
        user = conn.execute(
            "INSERT INTO users (username, uid, password_hash, role, created_at, "
            "login_failed_count, is_deleted, department_id) "
            "VALUES (%s, %s, %s, 'superadmin', CURRENT_TIMESTAMP, 0, 0, %s) RETURNING id",
            (uid, uid, AuthUtils.hash_password(password), dept),
        ).fetchone()[0]
        try:
            response = httpx.post("http://127.0.0.1:5050/api/auth/token", data={"username": uid, "password": password})
            response.raise_for_status()
            result = subprocess.run(
                ["node", str(Path(__file__).with_name("navigation_smoke.mjs"))],
                env={**os.environ, "TEST_TOKEN": response.json()["access_token"]},
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=180,
            )
            assert result.returncode == 0, result.stdout + result.stderr
            print(result.stdout)
        finally:
            conn.execute("DELETE FROM operation_logs WHERE user_id = %s", (user,))
            conn.execute("DELETE FROM users WHERE id = %s", (user,))
            conn.execute("DELETE FROM departments WHERE id = %s", (dept,))
