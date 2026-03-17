from __future__ import annotations

import json
import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from .browser import (
    create_page, perform_click, perform_hover, perform_type, perform_press,
    perform_scroll, perform_goto, perform_go_back, perform_go_forward,
    shutdown as browser_shutdown, VIEWPORT,
)
from .store import (
    create_session, get_session, get_live_session_ids, add_action, update_screenshot,
    undo_last_action, complete_session, export_session, build_export_data,
    register_session, remove_session,
)
from .storage import (
    init_storage, save_step, list_sessions, load_session, load_session_meta,
    load_screenshot_raw, delete_session as delete_from_disk, get_screenshot_count,
)
from .models import Action, action_label, action_badge_class
from .templating import render


def normalize_url(url: str) -> str:
    if not url or url.startswith("http://") or url.startswith("https://"):
        return url
    return "https://" + url


def error_message(error: Exception, fallback: str) -> str:
    return str(error) if str(error) else fallback


def _actions_display(actions: list) -> list[dict]:
    """Build display data for action history template."""
    return [
        {
            "label": action_label(a),
            "badge_class": action_badge_class(a.type),
            "explanation": a.explanation,
        }
        for a in actions
    ]


def _format_date(timestamp_ms: int) -> str:
    """Format a millisecond timestamp to a readable date string."""
    from datetime import datetime, timezone
    dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    return dt.strftime("%b %d, %Y, %I:%M %p")


# --- Lifespan ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_storage()
    print(f"\n  Web Browser Annotation Tool")
    print(f"  http://localhost:3456\n")
    yield
    await browser_shutdown()


app = FastAPI(lifespan=lifespan)

# Static assets
app.mount("/assets", StaticFiles(directory="static"), name="static")


# --- Routes ---

@app.get("/logo.png")
async def serve_logo():
    from fastapi.responses import FileResponse
    return FileResponse("static/logo.png")


@app.get("/", response_class=HTMLResponse)
async def home():
    return render("home.html", title="Web Browser Annotation Tool", hide_navbar=False)


@app.get("/sessions", response_class=HTMLResponse)
async def sessions_list():
    sessions = await list_sessions()
    live_ids = get_live_session_ids()

    # Prepare display data
    sessions_display = []
    for meta in sessions:
        prompt_truncated = (
            meta.prompt[:60] + "..." if len(meta.prompt) > 60 else meta.prompt
        )
        sessions_display.append({
            "id": meta.id,
            "url": meta.url,
            "prompt_truncated": prompt_truncated,
            "status": meta.status,
            "action_count": meta.action_count,
            "date_str": _format_date(meta.created_at),
        })

    return render(
        "sessions.html",
        title="Annotation Sessions",
        hide_navbar=False,
        sessions=sessions_display,
        live_ids=live_ids,
    )


@app.post("/sessions")
async def create_session_route(request: Request):
    form = await request.form()
    url = (form.get("url", "") or "").strip()
    prompt = (form.get("prompt", "") or "").strip()

    if not url or not prompt:
        return HTMLResponse(
            '<div class="alert alert-error">URL and prompt are required</div>',
            status_code=400,
        )

    url = normalize_url(url)

    try:
        page, context, screenshot = await create_page(url)
        session = create_session(
            url, prompt, page, context, screenshot,
            VIEWPORT["width"], VIEWPORT["height"],
        )

        await save_step(session)

        return HTMLResponse(
            content="",
            status_code=200,
            headers={"HX-Redirect": f"/sessions/{session.id}"},
        )
    except Exception as e:
        html = render(
            "partials/error.html",
            message=f"Failed to load: {error_message(e, 'Failed to load webpage')}",
            page=True,
            inline=False,
            back_url="/",
            back_text="Try again",
        )
        return HTMLResponse(html, status_code=500)


@app.get("/sessions/{session_id}", response_class=HTMLResponse)
async def annotation_page(session_id: str):
    live = get_session(session_id)
    if not live:
        return RedirectResponse("/", status_code=302)

    s = live.session
    return render(
        "annotation.html",
        title=f"Annotate - {s.url}",
        hide_navbar=True,
        session=s,
        actions_display=_actions_display(s.actions),
    )


@app.post("/sessions/{session_id}/actions", response_class=HTMLResponse)
async def execute_action(session_id: str, request: Request):
    live = get_session(session_id)
    if not live:
        return HTMLResponse(
            '<div class="alert alert-error">Session not found</div>',
            status_code=404,
        )

    s = live.session
    if s.status == "completed":
        return HTMLResponse(render(
            "partials/controls.html",
            session=s,
            actions_display=_actions_display(s.actions),
        ))

    form = await request.form()
    action_type = form.get("type", "")
    explanation = form.get("explanation", "") or ""
    screenshot_before = s.current_screenshot
    timestamp = int(time.time() * 1000)

    base = {
        "explanation": explanation,
        "screenshot_before": screenshot_before,
        "timestamp": timestamp,
    }

    try:
        if action_type == "click":
            x = int(form.get("x", 0) or 0)
            y = int(form.get("y", 0) or 0)
            action = Action(type="click", x=x, y=y, **base)
            new_screenshot = await perform_click(live.page, x, y)

        elif action_type == "hover":
            x = int(form.get("x", 0) or 0)
            y = int(form.get("y", 0) or 0)
            action = Action(type="hover", x=x, y=y, **base)
            new_screenshot = await perform_hover(live.page, x, y)

        elif action_type == "type":
            text = form.get("text", "") or ""
            action = Action(type="type", text=text, **base)
            new_screenshot = await perform_type(live.page, text)

        elif action_type == "press":
            key = form.get("key", "Enter") or "Enter"
            action = Action(type="press", key=key, **base)
            new_screenshot = await perform_press(live.page, key)

        elif action_type == "scroll_up":
            action = Action(type="scroll_up", **base)
            new_screenshot = await perform_scroll(live.page, "up")

        elif action_type == "scroll_down":
            action = Action(type="scroll_down", **base)
            new_screenshot = await perform_scroll(live.page, "down")

        elif action_type == "goto":
            goto_url = normalize_url(form.get("goto_url", "") or "")
            action = Action(type="goto", url=goto_url, **base)
            new_screenshot = await perform_goto(live.page, goto_url)

        elif action_type == "go_back":
            action = Action(type="go_back", **base)
            new_screenshot = await perform_go_back(live.page)

        elif action_type == "go_forward":
            action = Action(type="go_forward", **base)
            new_screenshot = await perform_go_forward(live.page)

        elif action_type == "finish":
            answer = form.get("answer", "") or ""
            finish_action = Action(type="finish", answer=answer, **base)
            add_action(session_id, finish_action)
            complete_session(session_id)
            await save_step(s)
            html = render(
                "partials/session_update.html",
                session=s,
                actions_display=_actions_display(s.actions),
            )
            await remove_session(session_id)
            return HTMLResponse(html)

        else:
            return HTMLResponse(
                '<div class="alert alert-error">Unknown action type</div>',
                status_code=400,
            )

        add_action(session_id, action)
        update_screenshot(session_id, new_screenshot)

        # Save in background
        asyncio.create_task(_save_step_safe(s))

        return HTMLResponse(render(
            "partials/session_update.html",
            session=s,
            actions_display=_actions_display(s.actions),
        ))

    except Exception as e:
        screenshot_html = render("partials/screenshot.html", session=s)
        error_html = (
            f'<div class="alert alert-warning alert-inline">'
            f'<span>{error_message(e, "Action failed")}</span></div>'
        )
        return HTMLResponse(error_html + screenshot_html)


async def _save_step_safe(session):
    try:
        await save_step(session)
    except Exception as e:
        print(f"Failed to save step: {e}")


@app.post("/sessions/{session_id}/undo", response_class=HTMLResponse)
async def undo_action(session_id: str):
    live = get_session(session_id)
    if not live:
        return HTMLResponse(
            '<div class="alert alert-error">Session not found</div>',
            status_code=404,
        )

    s = live.session
    removed = undo_last_action(session_id)
    if not removed:
        return HTMLResponse(render("partials/screenshot.html", session=s))

    asyncio.create_task(_save_step_safe(s))

    return HTMLResponse(render(
        "partials/session_update.html",
        session=s,
        actions_display=_actions_display(s.actions),
    ))


@app.get("/sessions/{session_id}/restore")
async def restore_session(session_id: str):
    existing = get_session(session_id)
    if existing:
        return RedirectResponse(f"/sessions/{session_id}", status_code=302)

    session = await load_session(session_id)
    if not session:
        html = render(
            "partials/error.html",
            message="Session not found or corrupted",
            page=True,
            inline=False,
            back_url="/sessions",
            back_text="Back to sessions",
        )
        return HTMLResponse(html, status_code=404)

    try:
        page, context, screenshot = await create_page(session.url)
        session.current_screenshot = screenshot
        register_session(session, page, context)
        await save_step(session)
        return RedirectResponse(f"/sessions/{session_id}", status_code=302)
    except Exception as e:
        html = render(
            "partials/error.html",
            message=f"Restore failed: {error_message(e, 'Failed to restore session')}",
            page=True,
            inline=False,
            back_url="/sessions",
            back_text="Back to sessions",
        )
        return HTMLResponse(html, status_code=500)


@app.get("/sessions/{session_id}/replay", response_class=HTMLResponse)
async def replay_page(session_id: str):
    meta = await load_session_meta(session_id)
    if not meta:
        return RedirectResponse("/sessions", status_code=302)

    count = await get_screenshot_count(session_id)
    if count == 0:
        return RedirectResponse("/sessions", status_code=302)

    prompt_truncated = (
        meta.prompt[:100] + "..." if len(meta.prompt) > 100 else meta.prompt
    )

    # Build session data for JS (matching the original structure)
    session_data_obj = {
        "id": session_id,
        "url": meta.url,
        "prompt": meta.prompt,
        "screenshotCount": count,
        "actions": [
            {
                "type": a.type,
                "explanation": a.explanation,
                "x": a.x,
                "y": a.y,
                "text": a.text,
                "key": a.key,
                "url": a.url,
                "answer": a.answer,
            }
            for a in meta.actions
        ],
    }

    # JSON-encode and HTML-escape for safe embedding in data attribute
    session_data_json = json.dumps(session_data_obj)
    # Escape for HTML attribute (replace & < > " ')
    session_data_escaped = (
        session_data_json
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )

    return render(
        "replay.html",
        title=f"Replay - {meta.url}",
        hide_navbar=False,
        session_data=session_data_escaped,
        meta=meta,
        prompt_truncated=prompt_truncated,
        screenshot_count=count,
    )


@app.get("/sessions/{session_id}/screenshots/{step}")
async def serve_screenshot(session_id: str, step: int):
    if step < 0:
        return JSONResponse({"error": "Invalid step"}, status_code=400)

    buffer = await load_screenshot_raw(session_id, step)
    if not buffer:
        return Response(status_code=404)

    return Response(
        content=buffer,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@app.delete("/sessions/{session_id}", response_class=HTMLResponse)
async def delete_session_route(session_id: str):
    await remove_session(session_id)
    await delete_from_disk(session_id)
    return HTMLResponse("")


@app.get("/sessions/{session_id}/history", response_class=HTMLResponse)
async def get_history(session_id: str):
    live = get_session(session_id)
    if not live:
        return HTMLResponse("", status_code=404)
    s = live.session
    return HTMLResponse(render(
        "partials/history.html",
        session=s,
        actions_display=_actions_display(s.actions),
    ))


@app.get("/sessions/{session_id}/export")
async def export_session_route(session_id: str):
    # Try in-memory first
    data = export_session(session_id)
    if data:
        return JSONResponse(data.to_dict())

    # Fall back to disk
    meta = await load_session_meta(session_id)
    if not meta:
        return JSONResponse({"error": "Session not found"}, status_code=404)

    export = build_export_data(
        session_id=meta.id,
        url=meta.url,
        prompt=meta.prompt,
        status=meta.status,
        actions=meta.actions,
        updated_at=meta.updated_at,
    )
    return JSONResponse(export.to_dict())
