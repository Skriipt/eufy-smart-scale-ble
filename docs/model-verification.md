# Help verify an Eufy scale model

The project only owns and directly verifies a P3/T9150. Other models are implemented from compatible public protocol sources and benefit from community hardware verification.

## What to test

Use the integration normally and report whether the capabilities already listed for your model behave as expected, for example:

- live weight updates while weighing;
- final weight settles correctly;
- P2 Pro heart rate appears when produced by the scale;
- optional C1/P1 extended metrics connect and disconnect cleanly;
- supported impedance appears only after the corresponding measurement;
- experimental capabilities behave consistently when you explicitly enable them.

## Safe diagnostics

Home Assistant's normal integration diagnostics are intentionally sanitized and are the preferred attachment for a public issue. Before uploading anything, verify that it contains no personal data.

Do **not** post publicly:

- Bluetooth/MAC addresses;
- raw BLE advertisements or notification payloads;
- weight, impedance, or heart-rate measurements;
- age, height, sex, profile mode, or other profile details;
- screenshots containing body measurements or personal profile information.

The advanced protocol-capture option is for deliberate protocol research only. Its raw bytes can encode personal measurement data and should not be attached to a normal public verification issue.

## Submit a verification report

Open the repository's **Model verification** issue form, select the model and capability, describe only whether the feature worked, and attach only privacy-safe diagnostics if useful.

A capability is promoted from Upstream Validated or Experimental only after the evidence is reproducible and consistent with the public protocol sources.
