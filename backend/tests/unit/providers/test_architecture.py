from __future__ import annotations

import ast
from pathlib import Path

BACKEND_SOURCE = Path(__file__).parents[3] / "src" / "predictionlab"
PROVIDER_SOURCE = BACKEND_SOURCE / "providers"
COLLECTOR_SOURCE = BACKEND_SOURCE / "collectors"
APPROVED_LAYERS = ("domain", "application", "api")
FORBIDDEN_PROVIDER_DEPENDENCIES = (
    *(
        f"predictionlab.{layer}"
        for layer in (
            "domain",
            "application",
            "api",
            "infrastructure",
            "integrations",
            "collectors",
        )
    ),
    "sqlalchemy",
)


def test_provider_sdk_does_not_import_existing_layers() -> None:
    violations = _find_imports(PROVIDER_SOURCE, FORBIDDEN_PROVIDER_DEPENDENCIES)

    assert violations == []


def test_approved_layers_do_not_import_provider_sdk() -> None:
    violations = []
    for layer in APPROVED_LAYERS:
        violations.extend(
            _find_imports(
                BACKEND_SOURCE / layer,
                ("predictionlab.providers",),
            )
        )

    assert violations == []


def test_collector_depends_on_infrastructure_ports_not_adapters() -> None:
    violations = _find_imports(
        COLLECTOR_SOURCE,
        ("predictionlab.infrastructure", "sqlalchemy"),
    )

    assert violations == []


def _find_imports(
    source: Path,
    forbidden_prefixes: tuple[str, ...],
) -> list[str]:
    violations: list[str] = []
    for path in source.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported_modules = _imported_modules(node)
            for imported_module in imported_modules:
                if imported_module.startswith(forbidden_prefixes):
                    violations.append(
                        f"{path.relative_to(BACKEND_SOURCE)} imports {imported_module}"
                    )
    return violations


def _imported_modules(node: ast.AST) -> tuple[str, ...]:
    if isinstance(node, ast.Import):
        return tuple(alias.name for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return (node.module,)
    return ()
