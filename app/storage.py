from __future__ import annotations

import base64
import json
import os
import shutil
import time
from pathlib import Path

from .models import Session, Action, StrippedAction, SessionMeta, strip_action

SESSIONS_DIR = Path(os.getcwd()) / "sessions"


async def init_storage() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def _session_dir(session_id: str) -> Path:
    return SESSIONS_DIR / session_id


def _session_json_path(session_id: str) -> Path:
    return _session_dir(session_id) / "session.json"


def _screenshot_path(session_id: str, step_index: int) -> Path:
    filename = f"screenshot-{step_index:03d}.png"
    return _session_dir(session_id) / filename


def _stripped_action_to_dict(a: StrippedAction) -> dict:
    d: dict = {"type": a.type, "explanation": a.explanation, "timestamp": a.timestamp}
    if a.x is not None:
        d["x"] = a.x
    if a.y is not None:
        d["y"] = a.y
    if a.text is not None:
        d["text"] = a.text
    if a.key is not None:
        d["key"] = a.key
    if a.url is not None:
        d["url"] = a.url
    if a.answer is not None:
        d["answer"] = a.answer
    return d


def _dict_to_stripped_action(d: dict) -> StrippedAction:
    return StrippedAction(
        type=d["type"],
        explanation=d.get("explanation", ""),
        timestamp=d.get("timestamp", 0),
        x=d.get("x"),
        y=d.get("y"),
        text=d.get("text"),
        key=d.get("key"),
        url=d.get("url"),
        answer=d.get("answer"),
    )


def _session_to_json(session: Session) -> dict:
    return {
        "id": session.id,
        "url": session.url,
        "prompt": session.prompt,
        "status": session.status,
        "createdAt": session.created_at,
        "updatedAt": int(time.time() * 1000),
        "viewportWidth": session.viewport_width,
        "viewportHeight": session.viewport_height,
        "actions": [_stripped_action_to_dict(strip_action(a)) for a in session.actions],
    }


def _base64_to_bytes(b64: str) -> bytes:
    # Remove data URL prefix if present
    if b64.startswith("data:"):
        b64 = b64.split(",", 1)[1]
    return base64.b64decode(b64)


async def save_step(session: Session) -> None:
    session_dir = _session_dir(session.id)
    session_dir.mkdir(parents=True, exist_ok=True)

    # Write session.json
    json_path = _session_json_path(session.id)
    json_path.write_text(json.dumps(_session_to_json(session), indent=2))

    # Save current screenshot as latest step
    if session.current_screenshot:
        step_index = len(session.actions)
        screenshot_bytes = _base64_to_bytes(session.current_screenshot)
        _screenshot_path(session.id, step_index).write_bytes(screenshot_bytes)


async def load_session_meta(session_id: str) -> SessionMeta | None:
    json_path = _session_json_path(session_id)
    if not json_path.exists():
        return None

    try:
        data = json.loads(json_path.read_text())
        actions = [_dict_to_stripped_action(a) for a in data.get("actions", [])]
        return SessionMeta(
            id=data["id"],
            url=data["url"],
            prompt=data["prompt"],
            status=data["status"],
            created_at=data["createdAt"],
            updated_at=data["updatedAt"],
            viewport_width=data["viewportWidth"],
            viewport_height=data["viewportHeight"],
            action_count=len(actions),
            actions=actions,
        )
    except Exception as e:
        print(f"Error loading session metadata for {session_id}: {e}")
        return None


async def load_screenshot(session_id: str, step_index: int) -> str | None:
    path = _screenshot_path(session_id, step_index)
    if not path.exists():
        return None

    try:
        raw = path.read_bytes()
        return base64.b64encode(raw).decode()
    except Exception as e:
        print(f"Error loading screenshot {step_index} for session {session_id}: {e}")
        return None


async def load_screenshot_raw(session_id: str, step_index: int) -> bytes | None:
    path = _screenshot_path(session_id, step_index)
    if not path.exists():
        return None

    try:
        return path.read_bytes()
    except Exception as e:
        print(f"Error loading raw screenshot {step_index} for session {session_id}: {e}")
        return None


async def load_session(session_id: str) -> Session | None:
    meta = await load_session_meta(session_id)
    if not meta:
        return None

    try:
        # Load latest screenshot
        latest_step = meta.action_count
        current_screenshot = await load_screenshot(session_id, latest_step)
        if not current_screenshot:
            print(f"No current screenshot found for session {session_id}")
            return None

        # Reconstruct actions with screenshots
        actions: list[Action] = []
        for i, action_meta in enumerate(meta.actions):
            screenshot_before = await load_screenshot(session_id, i)
            if not screenshot_before:
                print(f"Missing screenshot for action {i} in session {session_id}")
                return None

            actions.append(Action(
                type=action_meta.type,
                explanation=action_meta.explanation,
                timestamp=action_meta.timestamp,
                screenshot_before=screenshot_before,
                x=action_meta.x,
                y=action_meta.y,
                text=action_meta.text,
                key=action_meta.key,
                url=action_meta.url,
                answer=action_meta.answer,
            ))

        return Session(
            id=meta.id,
            url=meta.url,
            prompt=meta.prompt,
            status=meta.status,
            created_at=meta.created_at,
            actions=actions,
            current_screenshot=current_screenshot,
            viewport_width=meta.viewport_width,
            viewport_height=meta.viewport_height,
        )
    except Exception as e:
        print(f"Error loading full session {session_id}: {e}")
        return None


async def list_sessions() -> list[SessionMeta]:
    try:
        if not SESSIONS_DIR.exists():
            return []

        sessions: list[SessionMeta] = []
        for entry in SESSIONS_DIR.iterdir():
            if entry.is_dir():
                meta = await load_session_meta(entry.name)
                if meta:
                    sessions.append(meta)

        sessions.sort(key=lambda s: s.created_at, reverse=True)
        return sessions
    except Exception as e:
        print(f"Error listing sessions: {e}")
        return []


async def delete_session(session_id: str) -> bool:
    session_dir = _session_dir(session_id)
    try:
        shutil.rmtree(session_dir, ignore_errors=True)
        return True
    except Exception as e:
        print(f"Error deleting session {session_id}: {e}")
        return False


async def get_screenshot_count(session_id: str) -> int:
    session_dir = _session_dir(session_id)
    try:
        if not session_dir.exists():
            return 0
        return sum(
            1 for f in session_dir.iterdir()
            if f.name.startswith("screenshot-") and f.name.endswith(".png")
        )
    except Exception as e:
        print(f"Error counting screenshots for session {session_id}: {e}")
        return 0
