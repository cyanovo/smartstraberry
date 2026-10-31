import os
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_checkpoint_pool_replaces_terminated_idle_connection():
    if os.getenv("TEST_WINDOWS_LOCAL") != "1":
        pytest.skip("Requires local Windows PostgreSQL")

    from dotenv import dotenv_values
    from psycopg import AsyncConnection
    from psycopg_pool import AsyncConnectionPool

    settings = dotenv_values(Path(__file__).resolve().parents[3] / ".runtime/local.env")
    url = settings["POSTGRES_URL"].replace("+asyncpg", "")
    async with AsyncConnectionPool(
        url, min_size=1, max_size=1,
        check=AsyncConnectionPool.check_connection,
        kwargs={"autocommit": True}, open=False,
    ) as pool:
        async with pool.connection() as connection:
            original_pid = connection.info.backend_pid
        # Terminate only this test's idle connection, never the database service.
        async with await AsyncConnection.connect(url, autocommit=True) as control:
            cursor = await control.execute("SELECT pg_terminate_backend(%s)", (original_pid,))
            assert (await cursor.fetchone())[0]
        async with pool.connection() as connection:
            assert connection.info.backend_pid != original_pid
            cursor = await connection.execute("SELECT 1")
            assert (await cursor.fetchone())[0] == 1
