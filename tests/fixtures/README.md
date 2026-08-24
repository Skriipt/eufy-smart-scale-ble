# Synthetic test fixtures only

Everything in this directory must be generated from documented protocol layouts
using synthetic values chosen specifically for tests.

Do **not** commit raw BLE captures, packet dumps copied from real hardware,
Bluetooth/MAC addresses from real devices, real weight/impedance/heart-rate
measurements, profile data, or other personal data here.

When a new protocol needs a fixture, add or extend a builder in `builders.py` and
construct the packet from explicit fields. Test values should be clearly treated
as synthetic and must not be copied from a person's measurement session.
