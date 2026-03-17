from __future__ import annotations

import time
from dataclasses import dataclass
from playwright.async_api import Page, BrowserContext

from .models import (
    Session, Action, StrippedAction, ExportData,
    action_details, strip_action,
)


@dataclass
class LiveSession:
    session: Session
    page: Page
    context: BrowserContext


_sessions: dict[str, LiveSession] = {}


def create_session(
    url: str,
    prompt: str,
    page: Page,
    context: BrowserContext,
    screenshot: str,
    viewport_width: int,
    viewport_height: int,
) -> Session:
    session = Session.create(url, prompt, screenshot, viewport_width, viewport_height)
    _sessions[session.id] = LiveSession(session=session, page=page, context=context)
    return session


def get_session(session_id: str) -> LiveSession | None:
    return _sessions.get(session_id)


def get_live_session_ids() -> set[str]:
    return set(_sessions.keys())


def add_action(session_id: str, action: Action) -> None:
    live = _sessions.get(session_id)
    if live:
        live.session.actions.append(action)


def update_screenshot(session_id: str, screenshot: str) -> None:
    live = _sessions.get(session_id)
    if live:
        live.session.current_screenshot = screenshot


def undo_last_action(session_id: str) -> Action | None:
    live = _sessions.get(session_id)
    if not live or not live.session.actions:
        return None

    removed = live.session.actions.pop()
    live.session.current_screenshot = removed.screenshot_before
    return removed


def complete_session(session_id: str) -> None:
    live = _sessions.get(session_id)
    if live:
        live.session.status = "completed"


async def remove_session(session_id: str) -> None:
    live = _sessions.pop(session_id, None)
    if not live:
        return
    try:
        await live.context.close()
    except Exception:
        pass


def build_export_data(
    session_id: str,
    url: str,
    prompt: str,
    status: str,
    actions: list[Action | StrippedAction],
    updated_at: int | None = None,
) -> ExportData:
    finish_action = next((a for a in actions if a.type == "finish"), None)
    return ExportData(
        session_id=session_id,
        url=url,
        prompt=prompt,
        actions=[
            {
                "step": i + 1,
                "type": a.type,
                "details": action_details(a),
                "explanation": a.explanation,
                "timestamp": a.timestamp,
            }
            for i, a in enumerate(actions)
        ],
        final_answer=finish_action.answer if finish_action and finish_action.type == "finish" else None,
        completed_at=(updated_at or int(time.time() * 1000)) if status == "completed" else None,
    )


def export_session(session_id: str) -> ExportData | None:
    live = _sessions.get(session_id)
    if not live:
        return None
    s = live.session
    return build_export_data(
        session_id=s.id,
        url=s.url,
        prompt=s.prompt,
        status=s.status,
        actions=s.actions,
    )


def register_session(session: Session, page: Page, context: BrowserContext) -> None:
    _sessions[session.id] = LiveSession(session=session, page=page, context=context)
