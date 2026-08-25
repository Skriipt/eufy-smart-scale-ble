"""Repository-level readiness checks for future official HACS submission."""

import json
import tomllib
from pathlib import Path


def test_repository_has_one_generic_integration() -> None:
    integrations = [
        path
        for path in Path("custom_components").iterdir()
        if path.is_dir() and (path / "manifest.json").exists()
    ]
    assert [path.name for path in integrations] == ["eufy_smart_scale_ble"]
    manifest = json.loads((integrations[0] / "manifest.json").read_text())
    project = tomllib.loads(Path("pyproject.toml").read_text())
    assert manifest["domain"] == "eufy_smart_scale_ble"
    assert manifest["name"] == "Eufy Smart Scale BLE"
    assert manifest["version"] == project["project"]["version"]
    assert {match["local_name"] for match in manifest["bluetooth"]} == {
        "eufy T9120",
        "eufy T9130",
        "eufy T9140",
        "eufy T9146",
        "eufy T9147",
        "eufy T9148",
        "eufy T9149",
        "eufy T9150",
    }


def test_manifest_declares_issue_tracker() -> None:
    manifest = json.loads(
        Path("custom_components/eufy_smart_scale_ble/manifest.json").read_text()
    )
    assert manifest["issue_tracker"] == (
        "https://github.com/Skriipt/eufy-smart-scale-ble/issues"
    )


def test_hacs_validation_workflow_has_no_ignored_checks() -> None:
    workflow = Path(".github/workflows/hacs.yml").read_text()
    assert "hacs/action@main" in workflow
    assert 'category: "integration"' in workflow
    assert "ignore:" not in workflow


def test_hassfest_validation_workflow_is_enabled() -> None:
    workflow = Path(".github/workflows/hassfest.yml").read_text()
    assert "home-assistant/actions/hassfest@master" in workflow
    assert "continue-on-error: true" not in workflow


def test_temporary_workflows_are_absent() -> None:
    assert not Path(".github/workflows/export-source.yml").exists()
    assert not Path(".github/workflows/fetch-upstreams.yml").exists()
