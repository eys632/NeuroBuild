from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from neurobuild.orchestrator import generate

result = generate(
    "남자 4명이서 살기 좋은 총 비용 3억원 이하의 집을 짓고자 해. "
    "방은 4개가 좋겠고 다같이 시간을 보낼 수 있도록 거실을 크게 만들어줘. "
    "1층집으로 넓게 만들어줘."
)
print("IFC:", result.ifc_path)
print("Report:", result.report_path)
print("Rooms:", len(result.plan.rooms))
print("IFC length:", len(result.ifc_text))
assert "IFCPROJECT" in result.ifc_text
assert "IFCWALL" in result.ifc_text
