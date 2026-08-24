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


def test_hacs_validation_workflow_has_no_ignored_checks() -> None:
    """Run the official HACS validator as an integration without exemptions."""
    workflow = Path(".github/workflows/hacs.yml").read_text()

    assert "hacs/action@main" in workflow
    assert 'category: "integration"' in workflow
    assert "ignore:" not in workflow
