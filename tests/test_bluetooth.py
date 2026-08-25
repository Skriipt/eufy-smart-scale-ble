"""Advertisement parser dispatch tests."""

from custom_components.eufy_smart_scale_ble.bluetooth import create_advertisement_parser
from custom_components.eufy_smart_scale_ble.model_registry import get_model
from tests.fixtures.t9150_packets import FINAL_SAMPLE, LIVE_SAMPLE


def test_p3_parser_selects_newest_packet() -> None:
    model = get_model("eufy T9150")
    assert model is not None
    parser = create_advertisement_parser(model)
    assert parser is not None
    events = parser.parse({1: LIVE_SAMPLE, 2: FINAL_SAMPLE})
    assert len(events) == 1
    assert events[0].status == "locked"
    assert events[0].weight_kg == 72.35


def test_gatt_only_model_has_no_advertisement_parser() -> None:
    model = get_model("eufy T9120")
    assert model is not None
    assert create_advertisement_parser(model) is None
