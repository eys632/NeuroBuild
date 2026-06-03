import os
from pathlib import Path
import sys

os.environ["USE_HF_LLM"] = "0"

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neurobuild.orchestrator import generate

base = generate(
    "남자 4명이서 살기 좋은 총 비용 3억원 이하의 집을 짓고자 해. "
    "방은 4개가 좋겠고 다같이 시간을 보낼 수 있도록 거실을 크게 만들어줘. "
    "1층집으로 넓게 만들어줘."
)

modified = generate("방을 5개로 늘리고 예산은 2억원으로 낮춰줘.", mode="modify", previous_result=base)
assert modified.brief.occupants == 4
assert modified.brief.room_count == 5
assert modified.brief.budget_krw == 200_000_000

added = generate("방 하나 추가해줘.", mode="modify", previous_result=base)
assert added.brief.room_count == 5
assert added.brief.budget_krw == base.brief.budget_krw

print("Base rooms:", base.brief.room_count, "Modified rooms:", modified.brief.room_count, "Added rooms:", added.brief.room_count)
print("Modified budget:", modified.brief.budget_krw)
