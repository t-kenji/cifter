from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="wheel install smoke を実行する")
    parser.add_argument("--wheel", required=True, help="install 対象 wheel の path または glob")
    parser.add_argument("--source", required=True, help="smoke で使う source file")
    parser.add_argument("--function", required=True, help="smoke で使う関数名")
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


def _venv_python(venv_dir: Path) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def _venv_command(venv_dir: Path, name: str) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / f"{name}.exe"
    return venv_dir / "bin" / name


def _run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def main() -> None:
    args = _parse_args()
    wheel = _resolve_path(args.wheel)
    source = _resolve_path(args.source)
    repo_root = Path.cwd()

    with tempfile.TemporaryDirectory(prefix="cifter-smoke-") as tempdir:
        venv_dir = Path(tempdir) / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
        python = _venv_python(venv_dir)
        cift = _venv_command(venv_dir, "cift")

        _run([str(python), "-m", "pip", "install", str(wheel)], cwd=repo_root)
        _run([str(cift), "--help"], cwd=repo_root)
        _run([str(python), "-m", "cifter", "--help"], cwd=repo_root)

        result = _run(
            [
                str(cift),
                "function",
                "--name",
                args.function,
                "--source",
                str(source),
            ],
            cwd=repo_root,
        )
        if args.function not in result.stdout:
            raise RuntimeError("smoke 実行結果に対象関数名が含まれていません")

    print(f"install smoke succeeded: {wheel.name}")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as error:
        if error.stdout:
            print(error.stdout, file=sys.stderr, end="")
        if error.stderr:
            print(error.stderr, file=sys.stderr, end="")
        raise SystemExit(error.returncode) from error
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from error
