"""Repository-level readiness checks for future official HACS submission."""

import json
from pathlib import Path


def test_manifest_declares_issue_tracker() -> None:
    """Expose the public issue tracker required by HACS integration validation."""
    manifest = json.loads(
        Path("custom_components/eufy_p3_ble/manifest.json").read_text()
    )

    assert manifest["issue_tracker"] == (
        "https://github.com/Skriipt/eufy-smart-scale-ble/issues"
    )
