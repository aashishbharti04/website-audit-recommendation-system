"""WebSocket endpoint that streams live crawl/analysis progress to the dashboard."""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..audit import get_audit
from ..audit.service import get_queue

router = APIRouter()


@router.websocket("/ws/audits/{audit_id}")
async def audit_progress(websocket: WebSocket, audit_id: str) -> None:
    await websocket.accept()
    audit = get_audit(audit_id)
    if not audit:
        await websocket.send_json({"status": "error", "message": "Audit not found", "pct": 100})
        await websocket.close()
        return

    queue = get_queue(audit_id)
    if queue is None:
        # Job already finished before the socket connected — send terminal state and close.
        await websocket.send_json({"status": audit.status.value, "message": "Audit complete.", "pct": 100})
        await websocket.close()
        return

    try:
        while True:
            event = await queue.get()
            if event is None:  # sentinel — stream finished
                break
            await websocket.send_json(event.model_dump(mode="json"))
        await websocket.close()
    except WebSocketDisconnect:
        pass
