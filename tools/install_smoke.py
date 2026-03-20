from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import tomllib
import venv
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="wheel install smoke を実行する")
    parser.add_argument("--wheel", required=True, help="install 対象 wheel の path または glob")
    parser.add_argument("--input", required=True, help="smoke で使う source file または dir")
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


def _run_with_input(command: list[str], *, cwd: Path, input_text: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        input=input_text,
    )


def _read_expected_version(repo_root: Path) -> str:
    data = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))
    version = data["project"]["version"]
    if not isinstance(version, str):
        raise TypeError("pyproject.toml の project.version は文字列でなければなりません")
    return version


def _assert_stdout(result: subprocess.CompletedProcess[str], expected: str) -> None:
    if result.stdout.strip() != expected:
        raise RuntimeError(
            f"想定外の出力です: expected={expected!r} actual={result.stdout.strip()!r}"
        )


def main() -> None:
    args = _parse_args()
    wheel = _resolve_path(args.wheel)
    input_path = _resolve_path(args.input)
    repo_root = Path.cwd()
    expected_version = f"cift {_read_expected_version(repo_root)}"

    with tempfile.TemporaryDirectory(prefix="cifter-smoke-") as tempdir:
        venv_dir = Path(tempdir) / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
        python = _venv_python(venv_dir)
        cift = _venv_command(venv_dir, "cift")

        _run([str(python), "-m", "pip", "install", str(wheel)], cwd=repo_root)
        _run([str(cift), "--help"], cwd=repo_root)
        _run([str(python), "-m", "cifter", "--help"], cwd=repo_root)
        _assert_stdout(_run([str(cift), "--version"], cwd=repo_root), expected_version)
        _assert_stdout(
            _run([str(python), "-m", "cifter", "--version"], cwd=repo_root),
            expected_version,
        )

        function_result = _run(
            [
                str(cift),
                "function",
                args.function,
                str(input_path),
                "--format",
                "text",
            ],
            cwd=repo_root,
        )
        if args.function not in function_result.stdout:
            raise RuntimeError("smoke 実行結果に対象関数名が含まれていません")

        json_result = _run(
            [
                str(cift),
                "flow",
                args.function,
                str(input_path),
                "--track",
                "ctx->state",
                "--format",
                "json",
            ],
            cwd=repo_root,
        )
        flow_payload = json.loads(json_result.stdout)
        if flow_payload["command"] != "flow":
            raise RuntimeError("flow JSON smoke の command が不正です")

        stdin_result = _run_with_input(
            [
                str(cift),
                "function",
                args.function,
                "--files-from",
                "-",
                "--format",
                "json",
            ],
            cwd=repo_root,
            input_text=f"{input_path}\n",
        )
        stdin_payload = json.loads(stdin_result.stdout)
        if not stdin_payload["results"]:
            raise RuntimeError("stdin --files-from smoke で結果が空です")

        route_result = _run(
            [
                str(cift),
                "route",
                args.function,
                str(input_path),
                "--route",
                "case[CMD_HOGE]/else-if[ret == 11]",
                "--format",
                "text",
            ],
            cwd=repo_root,
        )
        if "return -2;" not in route_result.stdout:
            raise RuntimeError("route smoke 実行結果が想定と異なります")

        auto_result = _run(
            [
                str(cift),
                "function",
                args.function,
                str(input_path),
            ],
            cwd=repo_root,
        )
        auto_payload = json.loads(auto_result.stdout)
        if auto_payload["command"] != "function":
            raise RuntimeError("非 TTY auto smoke の JSON 出力が不正です")

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
