from __future__ import annotations

import tomllib
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

PACKAGE_NAME = "cifter-cli"
COMMAND_NAME = "cift"


def get_version() -> str:
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return _read_version_from_pyproject()


def format_version_output() -> str:
    return f"{COMMAND_NAME} {get_version()}"


def _read_version_from_pyproject() -> str:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project")
    if not isinstance(project, dict):
        raise RuntimeError("pyproject.toml に project セクションがありません")
    version_value = project.get("version")
    if not isinstance(version_value, str):
        raise RuntimeError("pyproject.toml の project.version が文字列ではありません")
    return version_value
