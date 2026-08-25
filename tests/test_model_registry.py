from custom_components.eufy_smart_scale_ble.model_registry import (
    SUPPORTED_MODELS,
    Capability,
    SupportLevel,
    TransportMode,
    capability_enabled,
)


def test_all_official_eufylife_models_are_registered() -> None:
    assert set(SUPPORTED_MODELS) == {
        "eufy T9120",
        "eufy T9130",
        "eufy T9140",
        "eufy T9146",
        "eufy T9147",
        "eufy T9148",
        "eufy T9149",
        "eufy T9150",
    }


def test_p3_raw_capabilities_are_verified() -> None:
    model = SUPPORTED_MODELS["eufy T9150"]
    assert model.transport is TransportMode.ADVERTISEMENT
    assert model.capability(Capability.IMPEDANCE).level is SupportLevel.VERIFIED
    assert capability_enabled(model, Capability.BODY_COMPOSITION, {})


def test_p2_impedance_is_explicitly_unsupported() -> None:
    model = SUPPORTED_MODELS["eufy T9148"]
    assert model.capability(Capability.IMPEDANCE).level is SupportLevel.UNSUPPORTED
    assert not capability_enabled(model, Capability.IMPEDANCE, {})


def test_c1_extended_metrics_are_opt_in() -> None:
    model = SUPPORTED_MODELS["eufy T9146"]
    assert not capability_enabled(model, Capability.IMPEDANCE, {})
    assert capability_enabled(model, Capability.IMPEDANCE, {"extended_metrics": True})


def test_c1_composition_requires_extended_metrics_and_explicit_opt_in() -> None:
    model = SUPPORTED_MODELS["eufy T9146"]
    assert not capability_enabled(
        model,
        Capability.BODY_COMPOSITION,
        {"experimental_cross_model_composition": True},
    )
    assert capability_enabled(
        model,
        Capability.BODY_COMPOSITION,
        {
            "experimental_cross_model_composition": True,
            "extended_metrics": True,
        },
    )


def test_t9140_composition_requires_experimental_impedance() -> None:
    model = SUPPORTED_MODELS["eufy T9140"]
    assert not capability_enabled(
        model,
        Capability.BODY_COMPOSITION,
        {"experimental_cross_model_composition": True},
    )
    assert capability_enabled(
        model,
        Capability.BODY_COMPOSITION,
        {
            "experimental_cross_model_composition": True,
            "experimental_impedance": True,
        },
    )
