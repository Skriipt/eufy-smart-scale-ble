"""Repository-level consistency checks."""

import json
from pathlib import Path

from custom_components.eufy_smart_scale_ble.model_registry import SUPPORTED_MODELS


def test_manifest_models_match_registry() -> None:
    manifest = json.loads(
        Path("custom_components/eufy_smart_scale_ble/manifest.json").read_text()
    )
    assert {match["local_name"] for match in manifest["bluetooth"]} == set(
        SUPPORTED_MODELS
    )
