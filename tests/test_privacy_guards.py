"""Repository privacy regression guards."""

from __future__ import annotations

import re
from pathlib import Path

MAC_PATTERN = re.compile(r"(?i)(?:[0-9a-f]{2}:){5}[0-9a-f]{2}")


def test_public_tests_and_docs_contain_no_concrete_mac_literals() -> None:
    roots = (Path("tests"), Path("docs"), Path("README.md"))
    offenders: list[str] = []
    for root in roots:
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if not path.is_file() or path.suffix not in {".py", ".md", ".yml", ".yaml"}:
                continue
            text = path.read_text(encoding="utf-8")
            if MAC_PATTERN.search(text):
                offenders.append(str(path))
    assert offenders == []


def test_fixture_policy_explicitly_forbids_real_captures() -> None:
    policy = Path("tests/fixtures/README.md").read_text(encoding="utf-8").lower()
    assert "do **not** commit raw ble captures" in policy
    assert "real weight/impedance/heart-rate" in policy
