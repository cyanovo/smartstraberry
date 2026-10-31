"""Authenticated disease-care conversation workflow."""

import asyncio
import json
from contextlib import suppress

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from server.utils.auth_middleware import get_required_user
from yuxi.repositories.field_work_repository import field_repository as repo
from yuxi.services.control_proposal_service import require_thread
from yuxi.services.disease_care_service import analyze_disease, confirm_disease

disease_care = APIRouter(prefix="/disease-care", tags=["disease-care"])


class AnalysisInput(BaseModel):
    thread_id: str = Field(min_length=1, max_length=128)
    record_ids: list[str] = Field(min_length=1, max_length=20)
    kb_id: str | None = None
    question: str = Field(default="分析所选病虫害记录", max_length=100000)


class ConfirmationInput(BaseModel):
    thread_id: str = Field(min_length=1, max_length=128)
    accept: bool


@disease_care.get("")
async def suggestions(user=Depends(get_required_user)):
    return await repo.list("disease_care", user.department_id, owner_uid=user.uid, limit=20)


@disease_care.get("/{thread_id}")
async def history(thread_id: str, user=Depends(get_required_user)):
    await require_thread(thread_id, user)
    rows = await repo.list("disease_care", user.department_id, parent_id=thread_id)
    return [row for row in rows if row["owner_uid"] == str(user.uid)]


@disease_care.post("")
async def analyze(body: AnalysisInput, user=Depends(get_required_user)):
    return await analyze_disease(body.thread_id, body.record_ids, body.kb_id, user, question=body.question)


@disease_care.post("/stream")
async def stream_analysis(body: AnalysisInput, user=Depends(get_required_user)):
    await require_thread(body.thread_id, user)

    async def events():
        queue = asyncio.Queue()

        async def run():
            try:
                row = await analyze_disease(
                    body.thread_id, body.record_ids, body.kb_id, user, queue.put, question=body.question
                )
                answer = row["data"]["answer"]
                for offset in range(0, len(answer), 8):
                    await queue.put({"type": "delta", "text": answer[offset:offset + 8]})
                    # Pace presentation of the fixed guidance, not simulated model reasoning.
                    await asyncio.sleep(0.08)
                await queue.put({"type": "done", "row": row})
            except HTTPException as exc:
                await queue.put({"type": "error", "text": str(exc.detail)})
            except Exception:
                await queue.put({"type": "error", "text": "病害分析失败，请检查后端日志后重试"})

        task = asyncio.create_task(run())
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=10)
                except TimeoutError:
                    yield ": keep-alive\n\n"
                    continue
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                if event["type"] in {"done", "error"}:
                    break
        finally:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    return StreamingResponse(
        events(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@disease_care.post("/{record_id}/confirm")
async def confirm(record_id: str, body: ConfirmationInput, user=Depends(get_required_user)):
    return await confirm_disease(record_id, body.thread_id, body.accept, user)
