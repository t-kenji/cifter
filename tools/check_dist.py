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
    prefix = "License-Expression:"
    for line in metadata.splitlines():
        if line.startswith(prefix):
            actual = line.removeprefix(prefix).strip()
            return actual == expected
    return False


def main() -> None:
    args = _parse_args()
    wheel = _resolve_path(args.wheel)
    sdist = _resolve_path(args.sdist)
    metadata = _read_wheel_metadata(wheel)

    if not _metadata_has_license_expression(metadata, args.license_expression):
        raise ValueError(
            "wheel metadata の License-Expression が一致しません: "
            f"expected={args.license_expression}"
        )
    if not _wheel_has_license_file(wheel, args.license_file):
        raise ValueError(f"wheel に {args.license_file} が含まれていません")
    if not _sdist_has_license_file(sdist, args.license_file):
        raise ValueError(f"sdist に {args.license_file} が含まれていません")

    print(
        "distribution metadata validated: "
        f"{wheel.name} / {sdist.name} / {args.license_expression}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
