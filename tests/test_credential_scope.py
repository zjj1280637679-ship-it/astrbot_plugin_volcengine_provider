from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"


def read(relative: str) -> str:
    return (ROOT / relative).read_text("utf-8")


ordinary_workflow = read(".github/workflows/real-volcengine-runtime-matrix.yml")
assert "secrets.HUOSHANYINQINGAPI" in ordinary_workflow
assert "secrets.VOLCENGINE_AGENT_PLAN_API_KEY" in ordinary_workflow

seedance_workflows = (
    "seedance-chat-transfer-test.yml",
    "seedance-image-to-video-test.yml",
    "seedance-model-controlled-probe.yml",
    "seedance-pro-250528-i2v-probe.yml",
    "seedance-qqshow-smug-sticker.yml",
    "seedance-remaining-models-probe.yml",
)
for name in seedance_workflows:
    workflow = (WORKFLOWS / name).read_text("utf-8")
    assert "secrets.HUOSHANYINQINGAPI" not in workflow, name
    assert "secrets.VOLCENGINE_SEEDANCE_API_KEY" in workflow, name
    assert "SEEDANCE_API_KEY" in workflow, name
    assert "ARK_API_KEY" not in workflow, name

matrix = read("tests/e2e/real_volcengine_runtime_matrix.py")
assert 'ARK_API_KEY = os.environ.get("ARK_API_KEY", "").strip()' in matrix
assert (
    'AGENT_PLAN_API_KEY = os.environ.get("AGENT_PLAN_API_KEY", "").strip()'
    in matrix
)
assert '"key": [ARK_API_KEY]' in matrix
assert '"key": [AGENT_PLAN_API_KEY]' in matrix
assert '"key": [API_KEY]' not in matrix
assert '"ordinary_ark_key_reuse_forbidden": True' in matrix
assert '"execution": "skipped"' in matrix
assert '"reason": "optional_agent_plan_credential_missing"' in matrix
assert '"not_run_missing_dedicated_agent_plan_api_key"' in matrix

print("CREDENTIAL_SCOPE_CONTRACT=OK")
