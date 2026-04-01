from __future__ import annotations

import argparse
import sys
import tarfile
import zipfile
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="配布物のライセンス同梱とメタデータを検証する")
    parser.add_argument("--wheel", required=True, help="検証対象 wheel の path または glob")
    parser.add_argument("--sdist", required=True, help="検証対象 sdist の path または glob")
    parser.add_argument("--license-file", default="LICENSE", help="配布物に含める license file 名")
    parser.add_argument(
        "--license-expression",
        default="MIT",
        help="wheel metadata で期待する license expression",
    )
    parser.add_argument(
        "--project-name",
        default="cifter-cli",
        help="wheel metadata で期待する project name",
    )
    return parser.parse_args()


def _resolve_path(pattern: str) -> Path:
    path = Path(pattern)
    if path.is_absolute():
        if path.exists():
            return path.resolve()
        raise FileNotFoundError(f"対象が見つかりません: {pattern}")

    matches = sorted(Path.cwd().glob(pattern))
    if not matches:
        if path.exists():
            return path.resolve()
        raise FileNotFoundError(f"対象が見つかりません: {pattern}")
    if len(matches) != 1:
        raise RuntimeError(f"候補が一意ではありません: {pattern}: {matches}")
    return matches[0].resolve()


def _read_wheel_metadata(wheel_path: Path) -> str:
    with zipfile.ZipFile(wheel_path) as wheel:
        for name in wheel.namelist():
            if name.endswith(".dist-info/METADATA"):
                return wheel.read(name).decode("utf-8")
    raise ValueError(f"wheel metadata が見つかりません: {wheel_path}")


def _wheel_has_license_file(wheel_path: Path, license_file: str) -> bool:
    expected_suffix = f".dist-info/licenses/{license_file}"
    with zipfile.ZipFile(wheel_path) as wheel:
        return any(name.endswith(expected_suffix) for name in wheel.namelist())


def _sdist_has_license_file(sdist_path: Path, license_file: str) -> bool:
    expected_suffix = f"/{license_file}"
    with tarfile.open(sdist_path, "r:gz") as sdist:
        return any(name.endswith(expected_suffix) for name in sdist.getnames())


def _metadata_has_license_expression(metadata: str, expected: str) -> bool:
    value = _metadata_first_value(metadata, "License-Expression")
    return value == expected


def _metadata_has_name(metadata: str, expected: str) -> bool:
    value = _metadata_first_value(metadata, "Name")
    return value == expected


def _metadata_has_project_urls(metadata: str, expected_urls: dict[str, str]) -> bool:
    actual_urls: dict[str, str] = {}
    for value in _metadata_values(metadata, "Project-URL"):
        label, separator, url = value.partition(",")
        if not separator:
            return False
        actual_urls[label.strip()] = url.strip()
    return actual_urls == expected_urls


def _metadata_has_keywords(metadata: str, expected_keywords: list[str]) -> bool:
    value = _metadata_first_value(metadata, "Keywords")
    if value is None:
        return False
    actual_keywords = [keyword.strip() for keyword in value.split(",") if keyword.strip()]
    return actual_keywords == expected_keywords


def _metadata_has_classifiers(metadata: str, expected_classifiers: list[str]) -> bool:
    actual_classifiers = _metadata_values(metadata, "Classifier")
    return actual_classifiers == expected_classifiers


def _metadata_first_value(metadata: str, field: str) -> str | None:
    values = _metadata_values(metadata, field)
    if not values:
        return None
    return values[0]


def _metadata_values(metadata: str, field: str) -> list[str]:
    prefix = f"{field}:"
    values: list[str] = []
    for line in metadata.splitlines():
        if line.startswith(prefix):
            values.append(line.removeprefix(prefix).strip())
    return values


def main() -> None:
    args = _parse_args()
    wheel = _resolve_path(args.wheel)
    sdist = _resolve_path(args.sdist)
    metadata = _read_wheel_metadata(wheel)
    expected_project_urls = {
        "Homepage": "https://github.com/t-kenji/cifter",
        "Repository": "https://github.com/t-kenji/cifter",
        "Issues": "https://github.com/t-kenji/cifter/issues",
        "Changelog": "https://github.com/t-kenji/cifter/blob/main/CHANGELOG.md",
    }
    expected_keywords = [
        "c",
        "c++",
        "cpp",
        "cli",
        "tree-sitter",
        "source-extraction",
        "static-analysis",
    ]
    expected_classifiers = [
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: 3.14",
        "Programming Language :: C",
        "Programming Language :: C++",
        "Topic :: Software Development",
    ]

    if not _metadata_has_name(metadata, args.project_name):
        raise ValueError(f"wheel metadata の Name が一致しません: expected={args.project_name}")
    if not _metadata_has_license_expression(metadata, args.license_expression):
        raise ValueError(
            "wheel metadata の License-Expression が一致しません: "
            f"expected={args.license_expression}"
        )
    if not _metadata_has_project_urls(metadata, expected_project_urls):
        raise ValueError("wheel metadata の Project-URL が一致しません")
    if not _metadata_has_keywords(metadata, expected_keywords):
        raise ValueError("wheel metadata の Keywords が一致しません")
    if not _metadata_has_classifiers(metadata, expected_classifiers):
        raise ValueError("wheel metadata の Classifier が一致しません")
    if not _wheel_has_license_file(wheel, args.license_file):
        raise ValueError(f"wheel に {args.license_file} が含まれていません")
    if not _sdist_has_license_file(sdist, args.license_file):
        raise ValueError(f"sdist に {args.license_file} が含まれていません")

    print(
        "distribution metadata validated: "
        f"{wheel.name} / {sdist.name} / {args.project_name} / {args.license_expression}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
