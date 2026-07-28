from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).parents[3] / "src" / "predictionlab"


def test_agents_do_not_access_frameworks_storage_or_external_providers() -> None:
    forbidden = (
        "fastapi",
        "sqlalchemy",
        "predictionlab.api",
        "predictionlab.infrastructure",
        "predictionlab.integrations",
        "predictionlab.providers",
    )
    violations: list[str] = []
    for path in (PACKAGE / "agents").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            module = None
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(forbidden):
                        violations.append(f"{path.name}: {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module
            if module is not None and module.startswith(forbidden):
                violations.append(f"{path.name}: {module}")

    assert violations == []
