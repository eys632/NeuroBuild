from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.ifc_mvp import generate_simple_box_building
from backend.llm_qwen import interpret_delta_prompt, interpret_prompt, get_llm_status
from backend.edit_ops import apply_ops
from backend.prompt_parser import BuildingParams, parse_prompt, parse_prompt_delta
from backend.agent_runner import build_corrective_prompt, verify_supported_intents


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = PROJECT_ROOT / "web"
OUTPUT_DIR = PROJECT_ROOT / "output"
MODELS_DIR = PROJECT_ROOT / "models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)


app = FastAPI(title="IFC MVP")

# Static files (front-end)
app.mount("/static", StaticFiles(directory=str(WEB_DIR), html=True), name="static")


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=5000)
    use_llm: bool = True
    base_file_id: str | None = None


class GenerateResponse(BaseModel):
    file_id: str
    file_url: str
    download_url: str
    parsed: dict
    llm: dict | None = None
    llm_raw_json: str | None = None


class InterpretResponse(BaseModel):
    model_id: str
    data: dict
    raw_json: str


class InterpretRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=5000)


class AgentGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=5000)
    use_llm: bool = True
    base_file_id: str | None = None
    max_iters: int = Field(default=2, ge=0, le=5)


class AgentGenerateResponse(BaseModel):
    status: str
    final: GenerateResponse
    iterations: list[dict[str, Any]]


class _DesignState(BaseModel):
    params: dict[str, Any]
    layout_spec: dict | None = None
    last_prompt: str | None = None
    history: list[dict[str, Any]] = Field(default_factory=list)


_DESIGN_STORE: dict[str, _DesignState] = {}


def _merge_layout_spec(*, base: dict | None, delta: dict | None, delta_prompt: str) -> dict | None:
    """Merge LLM specs for multi-turn edits.

    We keep the base program (spaces) unless the new prompt likely changes it.
    """

    if base is None:
        return delta
    if delta is None:
        return base

    def _strip_nulls(d: dict) -> dict:
        out: dict = {}
        for k, v in (d or {}).items():
            if v is None:
                continue
            if isinstance(v, str) and v.strip() == "":
                continue
            out[k] = v
        return out

    merged: dict[str, Any] = {**base}

    # Merge dictionaries
    for key in ("constraints", "windows"):
        b = merged.get(key) or {}
        d = delta.get(key) or {}
        if isinstance(b, dict) and isinstance(d, dict) and d:
            d2 = _strip_nulls(d)
            if d2:
                merged[key] = {**b, **d2}

    # Replace only if delta provides non-empty
    for key in ("adjacency", "priorities", "assumptions"):
        if delta.get(key):
            merged[key] = delta.get(key)

    # Spaces: overwrite only if prompt likely changes program
    program_keywords = ("침실", "거실", "주방", "욕실", "화장실", "발코니", "방", "수납", "현관")
    if any(k in (delta_prompt or "") for k in program_keywords):
        if delta.get("spaces"):
            merged["spaces"] = delta.get("spaces")

    # Dimensions: merge if provided
    if isinstance(delta.get("proposed_dimensions_m"), dict):
        merged["proposed_dimensions_m"] = {
            **(merged.get("proposed_dimensions_m") or {}),
            **_strip_nulls(delta.get("proposed_dimensions_m") or {}),
        }

    return merged


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=500, detail="index.html not found")
    return HTMLResponse(index_path.read_text(encoding="utf-8"))


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest) -> GenerateResponse:
    # Ensure HF cache stays local to the project unless user overrides.
    os.environ.setdefault("HF_HOME", str(MODELS_DIR))

    base_state: _DesignState | None = _DESIGN_STORE.get(req.base_file_id) if req.base_file_id else None
    if req.base_file_id and base_state is None:
        raise HTTPException(
            status_code=400,
            detail="Unknown base_file_id. The server may have restarted; generate a new base design first.",
        )

    if base_state is not None:
        params = BuildingParams(**base_state.params)
    else:
        params = parse_prompt(req.prompt)

    llm_data: dict | None = None
    llm_raw_json: str | None = None
    llm_error: str | None = None
    applied_ops: list[dict[str, Any]] = []
    skipped_ops: list[dict[str, Any]] = []
    layout_spec: dict | None = base_state.layout_spec if base_state is not None else None
    if req.use_llm:
        try:
            # If modifying an existing design, interpret as a delta to avoid overwriting the program.
            if base_state is not None:
                # Provide current design state so the model can choose incremental ops (e.g., add_bathroom)
                # instead of repeatedly setting the same absolute value.
                def _infer_bathroom_count(spec: dict | None) -> int:
                    if not spec or not isinstance(spec, dict):
                        return 0
                    constraints = spec.get("constraints") if isinstance(spec.get("constraints"), dict) else {}
                    spaces = spec.get("spaces") if isinstance(spec.get("spaces"), list) else []
                    val = None
                    if isinstance(constraints, dict):
                        val = constraints.get("bathroom_count")
                    if val is not None:
                        try:
                            return max(0, int(val))
                        except Exception:
                            return 0
                    total = 0
                    for s in spaces:
                        if not isinstance(s, dict):
                            continue
                        if (s.get("type") or "") == "bathroom":
                            try:
                                total += int(s.get("count") or 0)
                            except Exception:
                                total += 0
                    return max(0, total)

                current_state = {
                    "params": {
                        "width_m": params.width_m,
                        "depth_m": params.depth_m,
                        "height_m": params.height_m,
                        "windows_per_wall": int(getattr(params, "windows_per_wall", 0)),
                        "windows_size_preset": str(getattr(params, "windows_size_preset", "medium")),
                        "avoid_bathroom_zone": bool(getattr(params, "avoid_bathroom_zone", False)),
                        "exterior_door": bool(getattr(params, "exterior_door", False)),
                    },
                    "layout": {
                        "bathroom_count": _infer_bathroom_count(layout_spec),
                    },
                }

                llm_out = interpret_delta_prompt(req.prompt, current_state=current_state)
            else:
                llm_out = interpret_prompt(req.prompt)
            llm_data = llm_out.data
            llm_raw_json = llm_out.raw_text
            # Base edits use Ops-first, but keep backward-compat with older fields.
            if base_state is not None and isinstance(llm_data, dict) and isinstance(llm_data.get("edits"), list):
                params, layout_spec, op_res = apply_ops(params=params, layout_spec=layout_spec, ops=llm_data.get("edits") or [])
                applied_ops = op_res.applied
                skipped_ops = op_res.skipped

            proposed = (llm_data or {}).get("proposed_dimensions_m") or {}
            llm_windows = (llm_data or {}).get("windows") or {}
            llm_windows_per_wall = llm_windows.get("perimeter_windows_per_wall")
            llm_windows_size = llm_windows.get("size_preset")
            llm_avoid_bathroom = llm_windows.get("avoid_bathroom_zone")

            llm_constraints = (llm_data or {}).get("constraints") or {}
            llm_exterior_door = llm_constraints.get("exterior_door")
            if not isinstance(llm_exterior_door, bool):
                llm_exterior_door = None

            if isinstance(llm_windows_size, str):
                llm_windows_size = llm_windows_size.strip().lower()
                if llm_windows_size not in ("small", "medium", "large"):
                    llm_windows_size = None
            else:
                llm_windows_size = None

            if not isinstance(llm_avoid_bathroom, bool):
                llm_avoid_bathroom = None

            # Only apply proposed dimensions if user explicitly mentioned dimensions in this turn.
            delta = parse_prompt_delta(req.prompt)
            has_explicit_dims = any(x is not None for x in (delta.width_m, delta.depth_m, delta.height_m))

            # For initial designs (no base), we still use the structured fields.
            if base_state is None:
                params = type(params)(
                    width_m=float(proposed.get("width_m", params.width_m)) if has_explicit_dims else params.width_m,
                    depth_m=float(proposed.get("depth_m", params.depth_m)) if has_explicit_dims else params.depth_m,
                    height_m=float(proposed.get("height_m", params.height_m)) if has_explicit_dims else params.height_m,
                    wall_thickness_m=params.wall_thickness_m,
                    slab_thickness_m=params.slab_thickness_m,
                    windows_per_wall=(
                        int(llm_windows_per_wall)
                        if llm_windows_per_wall is not None
                        else int(getattr(params, "windows_per_wall", 0))
                    ),
                    windows_size_preset=(
                        llm_windows_size
                        if llm_windows_size is not None
                        else str(getattr(params, "windows_size_preset", "medium"))
                    ),
                    avoid_bathroom_zone=(
                        llm_avoid_bathroom
                        if llm_avoid_bathroom is not None
                        else bool(getattr(params, "avoid_bathroom_zone", False))
                    ),
                    exterior_door=(
                        llm_exterior_door if llm_exterior_door is not None else bool(getattr(params, "exterior_door", False))
                    ),
                )

            layout_spec = _merge_layout_spec(base=layout_spec, delta=llm_data, delta_prompt=req.prompt)
        except Exception as e:
            # MVP: if LLM fails, fall back to rule-based parsing without breaking generation.
            llm_data = None
            llm_raw_json = None
            llm_error = f"{type(e).__name__}: {e}"

    # Apply rule-based delta edits when modifying an existing design.
    if base_state is not None:
        delta = parse_prompt_delta(req.prompt)
        params = type(params)(
            width_m=delta.width_m if delta.width_m is not None else params.width_m,
            depth_m=delta.depth_m if delta.depth_m is not None else params.depth_m,
            height_m=delta.height_m if delta.height_m is not None else params.height_m,
            wall_thickness_m=delta.wall_thickness_m if delta.wall_thickness_m is not None else params.wall_thickness_m,
            slab_thickness_m=delta.slab_thickness_m if delta.slab_thickness_m is not None else params.slab_thickness_m,
            windows_per_wall=delta.windows_per_wall if delta.windows_per_wall is not None else params.windows_per_wall,
            windows_size_preset=(
                delta.windows_size_preset if delta.windows_size_preset is not None else getattr(params, "windows_size_preset", "medium")
            ),
            avoid_bathroom_zone=(
                delta.avoid_bathroom_zone if delta.avoid_bathroom_zone is not None else getattr(params, "avoid_bathroom_zone", False)
            ),
            exterior_door=(
                delta.exterior_door if delta.exterior_door is not None else getattr(params, "exterior_door", False)
            ),
        )

    model = generate_simple_box_building(
        width_m=params.width_m,
        depth_m=params.depth_m,
        height_m=params.height_m,
        wall_thickness_m=params.wall_thickness_m,
        slab_thickness_m=params.slab_thickness_m,
        windows_per_wall=int(getattr(params, "windows_per_wall", 0)),
        windows_size_preset=str(getattr(params, "windows_size_preset", "medium")),
        avoid_bathroom_zone=bool(getattr(params, "avoid_bathroom_zone", False)),
        exterior_door=bool(getattr(params, "exterior_door", False)),
        layout_spec=layout_spec,
        name="MVP Generated",
    )

    file_id = str(uuid.uuid4())
    out_path = OUTPUT_DIR / f"{file_id}.ifc"
    model.write(str(out_path))

    file_url = f"/api/files/{file_id}.ifc"

    history: list[dict[str, Any]] = []
    if base_state is not None:
        history = list(base_state.history)
    history.append(
        {
            "prompt": req.prompt,
            "use_llm": req.use_llm,
            "base_file_id": req.base_file_id,
        }
    )

    _DESIGN_STORE[file_id] = _DesignState(
        params=params.__dict__,
        layout_spec=layout_spec,
        last_prompt=req.prompt,
        history=history,
    )

    return GenerateResponse(
        file_id=file_id,
        file_url=file_url,
        download_url=file_url,
        parsed={
            "width_m": params.width_m,
            "depth_m": params.depth_m,
            "height_m": params.height_m,
            "wall_thickness_m": params.wall_thickness_m,
            "slab_thickness_m": params.slab_thickness_m,
            "windows_per_wall": int(getattr(params, "windows_per_wall", 0)),
            "windows_size_preset": str(getattr(params, "windows_size_preset", "medium")),
            "avoid_bathroom_zone": bool(getattr(params, "avoid_bathroom_zone", False)),
            "exterior_door": bool(getattr(params, "exterior_door", False)),
            "base_file_id": req.base_file_id,
            "llm_used": bool(req.use_llm and llm_data is not None),
            "llm_error": llm_error,
            "applied_ops": applied_ops,
            "skipped_ops": skipped_ops,
        },
        llm=llm_data,
        llm_raw_json=llm_raw_json,
    )


@app.post("/api/agent/generate", response_model=AgentGenerateResponse)
def agent_generate(req: AgentGenerateRequest) -> AgentGenerateResponse:
    """Agentic wrapper: generate -> verify -> (optional) retry with corrective prompt.

    This prevents a common failure mode: user asks for an incremental change twice,
    but the model repeats an absolute set operation and nothing changes.

    The verifier is intentionally limited to supported, deterministic checks.
    """

    iterations: list[dict[str, Any]] = []
    current_prompt = req.prompt
    base_file_id = req.base_file_id

    before_summary: dict[str, Any] | None = None
    if base_file_id:
        base_state = _DESIGN_STORE.get(base_file_id)
        if base_state is not None:
            before_params = BuildingParams(**base_state.params)
            before_summary = {
                "windows_per_wall": int(getattr(before_params, "windows_per_wall", 0)),
                "exterior_door": bool(getattr(before_params, "exterior_door", False)),
                "layout_spec": base_state.layout_spec,
            }

    last_resp: GenerateResponse | None = None
    for _ in range(max(0, int(req.max_iters)) + 1):
        resp = generate(GenerateRequest(prompt=current_prompt, use_llm=req.use_llm, base_file_id=base_file_id))
        last_resp = resp

        after_state = _DESIGN_STORE.get(resp.file_id)
        after_summary = {
            "windows_per_wall": int(resp.parsed.get("windows_per_wall") or 0),
            "exterior_door": bool(resp.parsed.get("exterior_door") or False),
            "layout_spec": after_state.layout_spec if after_state is not None else None,
        }

        ver = verify_supported_intents(prompt=req.prompt, before=before_summary, after=after_summary)
        next_prompt = None
        if not ver.satisfied:
            next_prompt = build_corrective_prompt(
                original_prompt=req.prompt,
                unmet=ver.unmet,
                before=before_summary,
                after=after_summary,
            )

        iterations.append(
            {
                "prompt": current_prompt,
                "file_id": resp.file_id,
                "parsed": resp.parsed,
                "applied_ops": resp.parsed.get("applied_ops"),
                "skipped_ops": resp.parsed.get("skipped_ops"),
                "verification": {"satisfied": ver.satisfied, "unmet": ver.unmet},
                "next_prompt": next_prompt,
            }
        )

        if ver.satisfied or not next_prompt:
            return AgentGenerateResponse(status="satisfied" if ver.satisfied else "failed", final=resp, iterations=iterations)

        # Retry as a delta edit applied to the latest design.
        before_summary = after_summary
        base_file_id = resp.file_id
        current_prompt = next_prompt

    # Should not reach due to early return
    assert last_resp is not None
    return AgentGenerateResponse(status="failed", final=last_resp, iterations=iterations)


@app.post("/api/interpret", response_model=InterpretResponse)
def interpret(req: InterpretRequest) -> InterpretResponse:
    os.environ.setdefault("HF_HOME", str(MODELS_DIR))
    out = interpret_prompt(req.prompt)
    return InterpretResponse(model_id="Qwen/Qwen2.5-7B-Instruct", data=out.data, raw_json=out.raw_text)


@app.get("/api/interpret", response_model=InterpretResponse)
def interpret_get(prompt: str = Query(min_length=1, max_length=5000)) -> InterpretResponse:
    os.environ.setdefault("HF_HOME", str(MODELS_DIR))
    out = interpret_prompt(prompt)
    return InterpretResponse(model_id="Qwen/Qwen2.5-7B-Instruct", data=out.data, raw_json=out.raw_text)


@app.get("/api/llm/status")
def llm_status() -> dict[str, Any]:
    return get_llm_status()


@app.get("/api/files/{filename}")
def get_file(filename: str):
    # basic safety: only allow UUID.ifc
    if not filename.endswith(".ifc"):
        raise HTTPException(status_code=400, detail="Only .ifc is allowed")
    file_id = filename.removesuffix(".ifc")
    try:
        uuid.UUID(file_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid file id") from e

    path = OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path,
        media_type="application/octet-stream",
        filename=filename,
    )


def main() -> None:
    # For `python -m backend.app`
    import uvicorn

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("backend.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
