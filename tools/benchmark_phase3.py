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
        c_path.write_text(_build_c_source(args.functions), encoding="utf-8")
        cpp_path.write_text(_build_cpp_source(args.functions), encoding="utf-8")

        cases = [
            ("parse_source(c)", lambda: parse_source(c_path, [])),
            ("parse_source(cpp)", lambda: parse_source(cpp_path, [])),
            (
                "function(c)",
                lambda: _run_cli(repo_root, "function", "--name", "BenchTargetC", "--source", str(c_path)),
            ),
            (
                "flow(c)",
                lambda: _run_cli(
                    repo_root,
                    "flow",
                    "--function",
                    "BenchTargetC",
                    "--source",
                    str(c_path),
                    "--track",
                    "state",
                ),
            ),
            (
                "path(c)",
                lambda: _run_cli(
                    repo_root,
                    "path",
                    "--function",
                    "BenchTargetC",
                    "--source",
                    str(c_path),
                    "--route",
                    "if x > 0",
                ),
            ),
            (
                "function(cpp)",
                lambda: _run_cli(
                    repo_root,
                    "function",
                    "--name",
                    "BenchTargetCpp",
                    "--source",
                    str(cpp_path),
                ),
            ),
            (
                "flow(cpp)",
                lambda: _run_cli(
                    repo_root,
                    "flow",
                    "--function",
                    "BenchTargetCpp",
                    "--source",
                    str(cpp_path),
                    "--track",
                    "current",
                ),
            ),
            (
                "path(cpp)",
                lambda: _run_cli(
                    repo_root,
                    "path",
                    "--function",
                    "BenchTargetCpp",
                    "--source",
                    str(cpp_path),
                    "--route",
                    "if current > 0",
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


if __name__ == "__main__":
    main()
