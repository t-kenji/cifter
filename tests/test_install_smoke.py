from __future__ import annotations

import subprocess
from pathlib import Path

from tools import install_smoke


def test_run_decodes_utf8_output_from_subprocess(monkeypatch, tmp_path: Path) -> None:
    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[bytes]:
        assert kwargs["text"] is False
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="関数実装全体を切り出す\n".encode(),
            stderr=b"",
        )

    monkeypatch.setattr(install_smoke.subprocess, "run", fake_run)

    result = install_smoke._run(["cift", "--help"], cwd=tmp_path)

    assert result.stdout == "関数実装全体を切り出す\n"


def test_run_with_input_sends_utf8_bytes(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, bytes] = {}

    def fake_run(*args, **kwargs) -> subprocess.CompletedProcess[bytes]:
        captured["input"] = kwargs["input"]
        assert kwargs["text"] is False
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=b'{"results":[1]}',
            stderr=b"",
        )

    monkeypatch.setattr(install_smoke.subprocess, "run", fake_run)

    result = install_smoke._run_with_input(
        ["cift", "function", "Foo", "--files-from", "-"],
        cwd=tmp_path,
        input_text="examples/showcase/c/control_flow.c\n",
    )

    assert captured["input"] == b"examples/showcase/c/control_flow.c\n"
    assert result.stdout == '{"results":[1]}'
