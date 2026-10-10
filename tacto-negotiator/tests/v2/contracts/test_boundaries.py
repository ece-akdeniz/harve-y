"""Static import enforcement; sample violations prove the checker isn't a vacuous scan."""

import ast
import importlib.util
import sys
from pathlib import Path

import pytest

from tests.v2.support import require

ALLOWED = {
    "core": {"core"}, "evidence": {"core", "evidence"},
    "economics": {"core", "economics"}, "intelligence": {"core", "intelligence"},
    "strategy": {"core", "strategy"}, "execution": {"core", "execution"},
    "orchestration": {"core", "orchestration"}, "adapters": {"core", "adapters"},
    "config": {"core", "config"},
}


def violations(source, module):
    owner = module.removeprefix("negotiator.v2.").split(".")[0]
    failures = []
    for node in ast.walk(ast.parse(source)):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parent = module.rsplit(".", 1)[0].split(".")
                base = parent[:len(parent) - node.level + 1]
                resolved = ".".join([*base, *([node.module] if node.module else [])])
                names = [resolved + "." + alias.name for alias in node.names]
            else:
                names = [node.module + "." + alias.name for alias in node.names]
        for name in names:
            if owner == "factory":
                continue
            root = name.split(".")[0]
            if name.startswith("tests."):
                failures.append(name)
            elif name.startswith("negotiator.v2."):
                target = name.removeprefix("negotiator.v2.").split(".")[0]
                if target not in ALLOWED[owner]:
                    failures.append(name)
            elif name.startswith("negotiator."):
                if owner != "adapters":
                    failures.append(name)
            elif root not in sys.stdlib_module_names and root != "pydantic":
                if owner != "adapters":
                    failures.append(name)
            elif root in {"sqlite3", "socket", "urllib", "subprocess"} and owner != "adapters":
                failures.append(name)
        if isinstance(node, ast.Call) and (
            isinstance(node.func, ast.Name) and node.func.id in {"__import__", "eval", "exec"}
            or isinstance(node.func, ast.Attribute) and node.func.attr == "import_module"
        ):
            failures.append("dynamic_import_or_execution")
    return failures


@pytest.mark.parametrize("module,source", [
    ("core.models", "import httpx"), ("core.models", "import sqlite3"),
    ("evidence.context", "from negotiator.v2.strategy.baseline import Policy"),
    ("economics.official", "from negotiator.agent import PackageAgent"),
    ("economics.official", "from negotiator.v2.adapters.model import Gateway"),
    ("strategy.capacity", "from ..execution.executor import Executor"),
    ("strategy.capacity", "from negotiator.v2.factory import build"),
    ("intelligence.interpreter", "from negotiator.v2.economics.prices import solve"),
    ("execution.render", "from negotiator.v2.adapters.model import Gateway"),
    ("orchestration.loop", "from negotiator.v2.strategy.capacity import Policy"),
    ("strategy.capacity", "import socket"), ("adapters.arena", "from tests.v2 import fakes"),
    ("strategy.registry", "__import__('arbitrary_strategy')"),
])
def test_boundary_checker_rejects_known_violations(module, source):
    assert violations(source, "negotiator.v2." + module)


@pytest.mark.parametrize("module,source", [
    ("core.models", "from decimal import Decimal\nfrom pydantic import BaseModel"),
    ("strategy.capacity", "from ..core.models import StrategyIntent"),
    ("economics.official", "from negotiator.v2.core.ports import OfficialCostOracle"),
    ("adapters.official", "from arena_kit.cost import total_cost"),
    ("adapters.sqlite", "import sqlite3"),
])
def test_boundary_checker_accepts_allowed_dependencies(module, source):
    assert violations(source, "negotiator.v2." + module) == []


def test_implemented_v2_import_graph(request):
    require(request, "core.models")
    namespace = importlib.util.find_spec("negotiator.v2")
    root = Path(next(iter(namespace.submodule_search_locations)))
    files = list(root.rglob("*.py"))
    assert files, "An empty namespace is not an implemented architecture"
    for file in files:
        relative = file.relative_to(root).with_suffix("")
        parts = list(relative.parts)
        if parts[-1] == "__init__":
            parts[-1] = "_package"
        module = "negotiator.v2." + ".".join(parts)
        if parts[0] == "_package":
            assert not ast.parse(file.read_text()).body, "Root __init__ must be empty, without facade imports"
            continue
        assert violations(file.read_text(), module) == [], str(file)
