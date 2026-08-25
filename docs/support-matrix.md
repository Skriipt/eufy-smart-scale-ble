# Eufy Smart Scale BLE support matrix

Support is tracked **per capability**. A model being supported for weight does not imply that every body-composition field is available or verified.

## Support levels

- **Verified** — tested with real hardware by this project.
- **Upstream Validated** — the protocol/behavior is implemented by reputable compatible upstream projects, but has not been hardware-tested by this project.
- **Experimental** — plausible protocol evidence exists, but the capability remains gated pending verification.
- **Unsupported** — the available protocol evidence is not reliable enough to expose the capability.

## Models

| Model | Discovery name | Weight / final | Heart rate | Raw impedance | Body composition | Transport |
|---|---|---|---|---|---|---|
| Smart Scale A1 | `eufy T9120` | Upstream Validated | Unsupported | Upstream Validated | Experimental opt-in | GATT |
| Smart Scale C20 | `eufy T9130` | Upstream Validated | Upstream Validated | Upstream Validated | Experimental opt-in | Advertisement |
| Smart Scale | `eufy T9140` | Upstream Validated | Unsupported | Experimental, off by default | Experimental, off by default | GATT |
| Smart Scale C1 | `eufy T9146` | Upstream Validated | Unsupported | Upstream Validated via optional GATT | Experimental opt-in | Advertisement + optional GATT |
| Smart Scale P1 | `eufy T9147` | Upstream Validated | Unsupported | Upstream Validated via optional GATT | Experimental opt-in | Advertisement + optional GATT |
| Smart Scale P2 | `eufy T9148` | Upstream Validated | Unsupported | Unsupported | Unavailable | Advertisement |
| Smart Scale P2 Pro | `eufy T9149` | Upstream Validated | Upstream Validated | Unsupported | Unavailable | Advertisement |
| Smart Scale P3 | `eufy T9150` | **Verified** | **Verified** | **Verified** | Experimental algorithm, enabled by default | Advertisement |

## Capability notes

### P3 / T9150

The raw advertisement protocol, sequence handling, final-weight behavior, impedance, and heart-rate fields are hardware-verified by this project. The local body-composition algorithm remains explicitly experimental.

### C20 / T9130

Weight, final-weight, heart-rate, and impedance advertisement fields are supported from compatible upstream protocol evidence. Cross-model body-composition calculations use the P3-compatible algorithm and therefore require explicit opt-in.

### A1 / T9120, C1 / T9146, P1 / T9147

These models share the documented Onebyone/Eufy `CF` measurement frame family. A1 requires GATT for measurement state. C1/P1 can provide passive weight through advertisements and only open GATT when extended metrics are enabled.

### Original Smart Scale / T9140

Weight is well documented, but several characteristic/firmware families exist. Raw impedance remains experimental and disabled by default until additional hardware verification is available.

### P2 / T9148 and P2 Pro / T9149

Weight is supported through advertisements; P2 Pro also exposes heart rate. A public 24-bit composition field is intentionally treated as opaque because real-hardware evidence shows that a naïve resistance interpretation is invalid. No impedance or impedance-derived body-composition entities are exposed.

## Community verification

Hardware verification is welcome. Please use the privacy-safe process in [model-verification.md](model-verification.md). A model/capability is only promoted after reproducible evidence shows that the implementation behaves correctly on real hardware.
