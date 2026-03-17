from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import uuid4
import time


ActionType = Literal[
    "click", "hover", "type", "press",
    "scroll_up", "scroll_down",
    "goto", "go_back", "go_forward",
    "finish",
]


@dataclass
class Action:
    type: ActionType
    explanation: str
    screenshot_before: str  # base64
    timestamp: int

    # click / hover
    x: int | None = None
    y: int | None = None

    # type
    text: str | None = None

    # press
    key: str | None = None

    # goto
    url: str | None = None

    # finish
    answer: str | None = None


@dataclass
class StrippedAction:
    """Action without screenshot_before - used for JSON persistence."""
    type: ActionType
    explanation: str
    timestamp: int

    x: int | None = None
    y: int | None = None
    text: str | None = None
    key: str | None = None
    url: str | None = None
    answer: str | None = None


@dataclass
class Session:
    id: str
    url: str
    prompt: str
    actions: list[Action]
    current_screenshot: str  # base64
    status: Literal["active", "completed"]
    created_at: int
    viewport_width: int
    viewport_height: int

    @staticmethod
    def create(
        url: str,
        prompt: str,
        screenshot: str,
        viewport_width: int,
        viewport_height: int,
    ) -> Session:
        return Session(
            id=str(uuid4()),
            url=url,
            prompt=prompt,
            actions=[],
            current_screenshot=screenshot,
            status="active",
            created_at=int(time.time() * 1000),
            viewport_width=viewport_width,
            viewport_height=viewport_height,
        )


@dataclass
class SessionMeta:
    id: str
    url: str
    prompt: str
    status: Literal["active", "completed"]
    created_at: int
    updated_at: int
    viewport_width: int
    viewport_height: int
    action_count: int
    actions: list[StrippedAction]


@dataclass
class ExportData:
    session_id: str
    url: str
    prompt: str
    actions: list[dict]
    final_answer: str | None = None
    completed_at: int | None = None

    def to_dict(self) -> dict:
        d = {
            "sessionId": self.session_id,
            "url": self.url,
            "prompt": self.prompt,
            "actions": self.actions,
        }
        if self.final_answer is not None:
            d["finalAnswer"] = self.final_answer
        if self.completed_at is not None:
            d["completedAt"] = self.completed_at
        return d


def strip_action(action: Action) -> StrippedAction:
    return StrippedAction(
        type=action.type,
        explanation=action.explanation,
        timestamp=action.timestamp,
        x=action.x,
        y=action.y,
        text=action.text,
        key=action.key,
        url=action.url,
        answer=action.answer,
    )


def action_details(a: Action | StrippedAction) -> dict:
    if a.type in ("click", "hover"):
        return {"x": a.x, "y": a.y}
    if a.type == "type":
        return {"text": a.text}
    if a.type == "press":
        return {"key": a.key}
    if a.type == "goto":
        return {"url": a.url}
    if a.type == "finish":
        return {"answer": a.answer}
    return {}


def action_label(a: Action | StrippedAction) -> str:
    match a.type:
        case "click":
            return f"Click ({a.x}, {a.y})"
        case "hover":
            return f"Hover ({a.x}, {a.y})"
        case "type":
            return f'Type "{a.text}"'
        case "press":
            return f"Press {a.key}"
        case "scroll_up":
            return "Scroll Up"
        case "scroll_down":
            return "Scroll Down"
        case "goto":
            return f"Go to {a.url}"
        case "go_back":
            return "Go back"
        case "go_forward":
            return "Go forward"
        case "finish":
            return "Finish"
    return a.type


def action_badge_class(action_type: str) -> str:
    if action_type in ("click", "hover"):
        return "badge-primary"
    if action_type in ("type", "press"):
        return "badge-secondary"
    if action_type.startswith("scroll"):
        return "badge-accent"
    if action_type.startswith("go") or action_type == "goto":
        return "badge-info"
    if action_type == "finish":
        return "badge-success"
    return "badge-ghost"
