from __future__ import annotations

import argparse
import re
import sys
import tomllib
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="release tag と changelog を検証する")
    parser.add_argument("--tag", required=True, help="vX.Y.Z または refs/tags/vX.Y.Z")
    parser.add_argument("--pyproject", default="pyproject.toml", help="pyproject.toml の path")
    parser.add_argument("--changelog", default="CHANGELOG.md", help="CHANGELOG.md の path")
    return parser.parse_args()


def _normalize_tag(tag: str) -> str:
    normalized = tag.removeprefix("refs/tags/")
    if not re.fullmatch(r"v\d+\.\d+\.\d+", normalized):
        raise ValueError(f"tag 形式が不正です: {tag}")
    return normalized


def _read_version(pyproject_path: Path) -> str:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    version = data["project"]["version"]
    if not isinstance(version, str):
        raise TypeError("project.version は文字列でなければなりません")
    return version


def _validate_changelog(changelog_path: Path, version: str) -> None:
    text = changelog_path.read_text(encoding="utf-8")
    if "## [Unreleased]" not in text:
        raise ValueError("CHANGELOG.md に Unreleased 節がありません")
    if f"## [{version}] -" not in text:
        raise ValueError(f"CHANGELOG.md に {version} の節がありません")


def main() -> None:
    args = _parse_args()
    tag = _normalize_tag(args.tag)
    version = _read_version(Path(args.pyproject))
    expected_tag = f"v{version}"
    if tag != expected_tag:
        raise ValueError(f"tag と version が一致しません: tag={tag} version={version}")
    _validate_changelog(Path(args.changelog), version)
    print(f"release metadata validated: {tag}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
