import random
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import Any
from urllib.parse import quote_plus

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .outreach import generate_outreach_message, load_recent_leads
from .scraper import BUSINESS_CATEGORIES, INDIAN_STATES, collect_businesses

app = FastAPI(title="Local Business Lead Discovery API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://botbotbot-nine.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_runs: dict[str, dict[str, Any]] = {}
_runs_lock = threading.Lock()
_message_pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix="grok-message")


class StartRequest(BaseModel):
    total_businesses: int = Field(default=5, ge=1, le=5)


def _update_run(run_id: str, **changes: Any) -> None:
    with _runs_lock:
        if run_id in _runs:
            _runs[run_id].update(changes)


def _lead_for_dashboard(lead: dict[str, Any], state: str) -> dict[str, Any]:
    business_name = str(lead.get("name", "Unknown business"))
    category = str(lead.get("category", "business"))
    maps_query = quote_plus(f"{business_name} {state}")
    return {
        "id": str(uuid.uuid4()),
        "state": state,
        "name": business_name,
        "category": category,
        "phone": lead.get("phone"),
        "website": lead.get("website"),
        "has_website": bool(lead.get("website")),
        "maps_url": f"https://www.google.com/maps/search/?api=1&query={maps_query}",
        "message": "Preparing personalized message...",
        "message_status": "preparing",
        "delivery_status": "preview_only",
    }


def _finish_message(run_id: str, lead_id: str, lead: dict[str, Any], state: str) -> None:
    try:
        message = generate_outreach_message(
            {
                "name": lead.get("name", "Your business"),
                "category": lead.get("category", "local business"),
                "city": state,
                "website": lead.get("website"),
            }
        )
    except Exception:
        message = "Message preview could not be generated. Please retry this lead."

    with _runs_lock:
        run = _runs.get(run_id)
        if run is None:
            return
        for dashboard_lead in run["leads"]:
            if dashboard_lead["id"] == lead_id:
                dashboard_lead["message"] = message
                dashboard_lead["message_status"] = "ready"
                break


def _publish_business(run_id: str, lead: dict[str, Any], state: str, total_limit: int) -> None:
    dashboard_lead = _lead_for_dashboard(lead, state)
    with _runs_lock:
        run = _runs.get(run_id)
        if run is None or len(run["leads"]) >= total_limit:
            return
        run["leads"].append(dashboard_lead)

    _message_pool.submit(_finish_message, run_id, dashboard_lead["id"], lead, state)


def _run_discovery(run_id: str, total_businesses: int) -> None:
    selected_states = random.sample(INDIAN_STATES, k=len(BUSINESS_CATEGORIES))
    searches = list(zip(BUSINESS_CATEGORIES, selected_states))
    _update_run(
        run_id,
        status="running",
        searches=[{"category": category, "state": state} for category, state in searches],
    )

    errors: list[str] = []
    for index, (category, state) in enumerate(searches, start=1):
        query = f"{category} in {state}"
        _update_run(run_id, current_query=query, progress=index - 1)
        try:
            found = collect_businesses(
                category,
                city=state,
                max_results=2,
                on_business=lambda lead, selected_state=state: _publish_business(
                    run_id, lead, selected_state, total_businesses
                ),
            )
            if not found:
                errors.append(f"{query}: Google Maps loaded no detectable business cards for this search.")
        except Exception as exc:
            errors.append(f"{query}: {type(exc).__name__}: {exc}")
        _update_run(run_id, progress=index)

    source = "Google Maps"
    with _runs_lock:
        has_live_results = bool(_runs[run_id]["leads"])
    if not has_live_results:
        cached = load_recent_leads(limit=30)
        for lead in cached:
            state = str(lead.get("city") or "India")
            _publish_business(run_id, lead, state, total_businesses)
            with _runs_lock:
                if len(_runs[run_id]["leads"]) >= total_businesses:
                    break
        with _runs_lock:
            if _runs[run_id]["leads"]:
                source = "Saved lead report (Maps fallback)"

    _update_run(
        run_id,
        status="completed",
        current_query=None,
        progress=len(searches),
        source=source,
        errors=errors,
        completed_at=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "preview_only"}


@app.post("/api/runs")
def start_run(request: StartRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    run_id = str(uuid.uuid4())
    with _runs_lock:
        _runs[run_id] = {
            "id": run_id,
            "status": "queued",
            "progress": 0,
            "searches": [],
            "current_query": None,
            "leads": [],
            "errors": [],
            "source": None,
        }
    background_tasks.add_task(_run_discovery, run_id, request.total_businesses)
    return {"run_id": run_id}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    with _runs_lock:
        run = _runs.get(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return deepcopy(run)