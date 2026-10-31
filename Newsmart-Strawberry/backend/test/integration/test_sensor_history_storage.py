"""Native Windows database check; deletes only this test's uniquely named samples."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import delete


def test_sensor_history_postgres_roundtrip():
    from yuxi.repositories.sensor_history_repository import SensorSample, sensor_history_repository as repository
    from yuxi.storage.postgres.manager import pg_manager

    async def run():
        pg_manager.initialize()
        device = "test-history-" + uuid4().hex
        now = datetime.now(UTC)
        try:
            await repository.initialize()
            await repository.append(device_id=device, kind="air", sampled_at=now, values={"temp": 23.5})
            await repository.append(
                device_id=device, kind="soil", sampled_at=now - timedelta(hours=2), values={"ph_value": 6.1}
            )
            result = await repository.query(device_id=device, start=now - timedelta(hours=1))
            assert result["total"] == 1
            assert result["items"][0]["values"] == {"temp": 23.5}
            assert (await repository.query(device_id=device, kind="soil"))["total"] == 1
            assert len((await repository.query(device_id=device, limit=1, offset=1))["items"]) == 1
            assert device in await repository.devices()
        finally:
            async with pg_manager.get_async_session_context() as session:
                await session.execute(delete(SensorSample).where(SensorSample.device_id == device))
            await pg_manager.close()

    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(run())
