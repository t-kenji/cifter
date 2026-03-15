from __future__ import annotations

import importlib.util
import tarfile
import zipfile
from pathlib import Path

import pytest


def _load_check_dist():
    module_path = Path(__file__).resolve().parents[1] / "tools" / "check_dist.py"
    spec = importlib.util.spec_from_file_location("check_dist", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("check_dist.py を読み込めません")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_dist = _load_check_dist()


def test_metadata_has_license_expression() -> None:
    metadata = "Metadata-Version: 2.4\nLicense-Expression: MIT\n"
    assert check_dist._metadata_has_license_expression(metadata, "MIT")


def test_metadata_requires_expected_license_expression() -> None:
    metadata = "Metadata-Version: 2.4\nLicense-Expression: Apache-2.0\n"
    assert not check_dist._metadata_has_license_expression(metadata, "MIT")


def test_wheel_has_license_file(tmp_path: Path) -> None:
    wheel = tmp_path / "sample.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("sample-0.1.0.dist-info/METADATA", "License-Expression: MIT\n")
        archive.writestr("sample-0.1.0.dist-info/licenses/LICENSE", "MIT License\n")

    assert check_dist._wheel_has_license_file(wheel, "LICENSE")


def test_sdist_has_license_file(tmp_path: Path) -> None:
    sdist = tmp_path / "sample.tar.gz"
    license_path = tmp_path / "LICENSE"
    license_path.write_text("MIT License\n", encoding="utf-8")
    with tarfile.open(sdist, "w:gz") as archive:
        archive.add(license_path, arcname="sample-0.1.0/LICENSE")

    assert check_dist._sdist_has_license_file(sdist, "LICENSE")


def test_read_wheel_metadata_fails_without_metadata(tmp_path: Path) -> None:
    wheel = tmp_path / "sample.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("sample-0.1.0.dist-info/licenses/LICENSE", "MIT License\n")

    with pytest.raises(ValueError, match="wheel metadata が見つかりません"):
        check_dist._read_wheel_metadata(wheel)
