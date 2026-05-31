from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VerificationResult:
    satisfied: bool
    unmet: list[dict[str, Any]]


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


def verify_supported_intents(*, prompt: str, before: dict[str, Any] | None, after: dict[str, Any]) -> VerificationResult:
    """Verify a small set of supported intents.

    This is intentionally limited to capabilities we can check deterministically.
    The goal is to avoid silent failures and enable agentic retries.

    `before`/`after` should be summaries like:
    {
      "windows_per_wall": int,
      "exterior_door": bool,
      "layout_spec": dict|None,
    }
    """

    unmet: list[dict[str, Any]] = []
    p = (prompt or "").strip()

    before_windows = int((before or {}).get("windows_per_wall") or 0)
    after_windows = int((after or {}).get("windows_per_wall") or 0)

    before_exterior_door = bool((before or {}).get("exterior_door") or False)
    after_exterior_door = bool((after or {}).get("exterior_door") or False)

    before_layout = (before or {}).get("layout_spec")
    after_layout = (after or {}).get("layout_spec")

    before_bath = _infer_bathroom_count(before_layout if isinstance(before_layout, dict) else None)
    after_bath = _infer_bathroom_count(after_layout if isinstance(after_layout, dict) else None)

    # 1) Remove all windows
    if any(k in p for k in ("창문", "창")) and any(k in p for k in ("전부", "모두", "다", "전체")) and any(
        k in p for k in ("제거", "삭제", "없애", "빼")
    ):
        if after_windows != 0:
            unmet.append(
                {
                    "intent": "remove_all_windows",
                    "expected": 0,
                    "actual": after_windows,
                }
            )

    # 2) Add exterior door
    if any(k in p for k in ("현관문", "출입문", "밖으로", "바깥", "외부")) and "문" in p:
        if not after_exterior_door:
            unmet.append({"intent": "exterior_door", "expected": True, "actual": after_exterior_door})

    # 3) Add bathroom (increment)
    if any(k in p for k in ("화장실", "욕실")) and any(k in p for k in ("추가", "더", "늘려")):
        # If before is unknown (no base), treat as not verifiable.
        if before is not None:
            if after_bath <= before_bath:
                unmet.append(
                    {
                        "intent": "add_bathroom",
                        "expected": before_bath + 1,
                        "actual": after_bath,
                    }
                )

    # 4) Set bathroom count explicitly
    # (Simple heuristic; we only verify if prompt includes an explicit integer count)
    import re

    m = re.search(r"(?:화장실|욕실)\s*(\d+)\s*개", p)
    if m:
        target = int(m.group(1))
        if after_bath != target:
            unmet.append({"intent": "set_bathroom_count", "expected": target, "actual": after_bath})

    return VerificationResult(satisfied=(len(unmet) == 0), unmet=unmet)


def build_corrective_prompt(*, original_prompt: str, unmet: list[dict[str, Any]], before: dict[str, Any] | None, after: dict[str, Any]) -> str:
    """Generate a more explicit follow-up prompt for the same intent.

    This is the key to "재발 방지": when something isn't applied, we don't guess silently.
    We produce an explicit prompt that anchors to the current numeric state.
    """

    before_layout = (before or {}).get("layout_spec") if before else None
    after_layout = after.get("layout_spec")
    before_bath = _infer_bathroom_count(before_layout if isinstance(before_layout, dict) else None)
    after_bath = _infer_bathroom_count(after_layout if isinstance(after_layout, dict) else None)

    lines: list[str] = []
    for item in unmet:
        intent = item.get("intent")
        if intent == "remove_all_windows":
            lines.append("창문을 모두 제거해서 외벽 창문이 0개가 되게 해줘.")
        elif intent == "exterior_door":
            lines.append("외벽에 밖으로 나갈 수 있는 출입문(현관문)을 추가해줘.")
        elif intent == "add_bathroom":
            # Anchor to current state to force increment semantics.
            target = max(after_bath + 1, before_bath + 1)
            lines.append(f"현재 화장실이 {after_bath}개야. 화장실을 1개 더 추가해서 총 {target}개로 만들어줘.")
        elif intent == "set_bathroom_count":
            target = int(item.get("expected") or 0)
            lines.append(f"화장실(욕실) 개수를 정확히 {target}개로 맞춰줘.")
        else:
            # Generic fallback: restate original prompt more explicitly.
            lines.append(f"다음 요구사항을 정확히 반영해줘: {original_prompt}")

    # De-duplicate while keeping order
    seen = set()
    out: list[str] = []
    for ln in lines:
        if ln in seen:
            continue
        seen.add(ln)
        out.append(ln)

    return "\n".join(out).strip() or (original_prompt or "").strip()
