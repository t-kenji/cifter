from __future__ import annotations

import argparse
import statistics
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from cifter.parser import parse_source


def main() -> None:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="cifter-bench-") as tmp_dir:
        tmp_path = Path(tmp_dir)
        c_path = tmp_path / "bench_large.c"
        cpp_path = tmp_path / "bench_large.cpp"
        dir_root = tmp_path / "repo"
        dir_root.mkdir()
        files_from_path = tmp_path / "targets.txt"
        mixed_files_from_path = tmp_path / "targets_mixed.txt"
        c_path.write_text(_build_c_source(args.functions), encoding="utf-8")
        cpp_path.write_text(_build_cpp_source(args.functions), encoding="utf-8")
        _write_repo_fixture(dir_root, args.files)
        repo_files = _iter_repo_files(dir_root)
        target_path = dir_root / "target.c"
        files_from_path.write_text(f"{target_path}\n", encoding="utf-8")
        mixed_files_from_path.write_text("\n".join(str(path) for path in repo_files), encoding="utf-8")

        cases = [
            ("parse_source(c)", lambda: parse_source(c_path, [])),
            ("parse_source(cpp)", lambda: parse_source(cpp_path, [])),
            (
                "function(c)",
                lambda: _run_cli(repo_root, "function", "BenchTargetC", str(c_path)),
            ),
            (
                "flow(c)",
                lambda: _run_cli(
                    repo_root,
                    "flow",
                    "BenchTargetC",
                    str(c_path),
                    "--track",
                    "state",
                ),
            ),
            (
                "route(c)",
                lambda: _run_cli(
                    repo_root,
                    "route",
                    "BenchTargetC",
                    str(c_path),
                    "--route",
                    "if[x > 0]",
                ),
            ),
            (
                "function(cpp)",
                lambda: _run_cli(
                    repo_root,
                    "function",
                    "BenchTargetCpp",
                    str(cpp_path),
                ),
            ),
            (
                "flow(cpp)",
                lambda: _run_cli(
                    repo_root,
                    "flow",
                    "BenchTargetCpp",
                    str(cpp_path),
                    "--track",
                    "current",
                ),
            ),
            (
                "route(cpp)",
                lambda: _run_cli(
                    repo_root,
                    "route",
                    "BenchTargetCpp",
                    str(cpp_path),
                    "--route",
                    "if[current > 0]",
                ),
            ),
            (
                "function(dir)",
                lambda: _run_cli(repo_root, "function", "BenchTargetDir", str(dir_root), "--format", "json"),
            ),
            (
                "function(files-from)",
                lambda: _run_cli(
                    repo_root,
                    "function",
                    "BenchTargetDir",
                    "--files-from",
                    str(files_from_path),
                    "--format",
                    "json",
                ),
            ),
            (
                "function(files-from-mixed)",
                lambda: _run_cli(
                    repo_root,
                    "function",
                    "BenchTargetDir",
                    "--files-from",
                    str(mixed_files_from_path),
                    "--format",
                    "json",
                ),
            ),
            (
                "route(dir)",
                lambda: _run_cli(
                    repo_root,
                    "route",
                    "BenchTargetDir",
                    str(dir_root),
                    "--route",
                    "if[value > 0]",
                    "--format",
                    "json",
                ),
            ),
        ]

        print(f"functions={args.functions} iterations={args.iterations}")
        print("case,median_ms,runs_ms")
        for label, case in cases:
            samples = [_measure(case) for _ in range(args.iterations)]
            median_ms = statistics.median(samples)
            runs = ", ".join(f"{sample:.2f}" for sample in samples)
            print(f"{label},{median_ms:.2f},{runs}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="フェーズ3向け性能計測")
    parser.add_argument("--functions", type=int, default=400, help="生成する補助関数数")
    parser.add_argument("--iterations", type=int, default=3, help="各ケースの反復回数")
    parser.add_argument("--files", type=int, default=120, help="dir/files-from 計測で生成する file 数")
    return parser.parse_args()


def _measure(task: Callable[[], object]) -> float:
    start = time.perf_counter()
    task()
    return (time.perf_counter() - start) * 1000


def _run_cli(repo_root: Path, *args: str) -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "cifter", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr or completed.stdout)


def _build_c_source(functions: int) -> str:
    parts = [_c_helper(index) for index in range(functions)]
    parts.append(
        """int BenchTargetC(int x)
{
    int state = 0;
    if (x > 0) {
        state = 1;
    } else {
        state = 2;
    }
    return state;
}
"""
    )
    return "\n".join(parts)


def _build_cpp_source(functions: int) -> str:
    helpers = "\n".join(_cpp_helper(index) for index in range(functions))
    return f"""namespace Bench {{
{helpers}

template <typename T>
T PassThrough(T value)
{{
    return value;
}}

int BenchTargetCpp(int value)
{{
    auto current = value;
    if (current > 0) {{
        return 1;
    }} else {{
        return 0;
    }}
}}
}}  // namespace Bench
"""


def _c_helper(index: int) -> str:
    return f"""int HelperC{index}(int x)
{{
    if (x > {index % 7}) {{
        return x + {index};
    }}
    return x - {index};
}}
"""


def _cpp_helper(index: int) -> str:
    return f"""int HelperCpp{index}(int value)
{{
    auto current = value;
    if (current > {index % 5}) {{
        return current + {index};
    }}
    return current - {index};
}}"""


def _write_repo_fixture(root: Path, files: int) -> None:
    for index in range(max(1, files - 1)):
        path = root / f"helper_{index:04d}.c"
        path.write_text(
            f"""int HelperFile{index}(int value)
{{
    return value + {index};
}}
""",
            encoding="utf-8",
        )
    (root / "target.c").write_text(
        """int BenchTargetDir(int value)
{
    if (value > 0) {
        return 1;
    } else {
        return 0;
    }
}
""",
        encoding="utf-8",
    )


def _iter_repo_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(root.glob("*.c")))


if __name__ == "__main__":
    main()
