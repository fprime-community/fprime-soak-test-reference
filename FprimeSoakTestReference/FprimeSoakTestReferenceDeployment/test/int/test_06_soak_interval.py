"""Per-interval soak duty cycle: alternate DP serialization each 30-min run.

This module models what one soak interval actually exercises: it flips the
producer's serialize state, confirms the toggle, and proves the radio is still
commandable afterward. It intentionally issues no catalog-xmit stop (that would
emit XmitNotActive / WARNING_LO and fail the soak gate).
"""

from soak_helpers import (
    CMD_TIMEOUT_S,
    await_event_or_fsw,
    dp_serialize_state_path,
    fsw_mark,
    latest_channel_value,
    send_cmd,
    wait_rf_quiet,
)


def test_soak_interval_dp_serialize_duty(fprime_test_api):
    """Flip START/STOP_SERIALIZING each soak-test invocation; persist choice."""
    wait_rf_quiet(2.0)

    producer = fprime_test_api.get_mnemonic("Components.SensorDataProducer")
    state_path = dp_serialize_state_path()
    last = (
        state_path.read_text(encoding="utf-8").strip() if state_path.is_file() else "off"
    )
    enable = last != "on"
    next_state = "on" if enable else "off"

    fprime_test_api.log(
        f"Soak DP serialize duty: last={last!r} -> commanding {next_state!r}"
    )

    start = fprime_test_api.get_event_test_history().size()
    if enable:
        mark = fsw_mark("DpProductionStarted")
        send_cmd(fprime_test_api, f"{producer}.START_SERIALIZING")
        ev = await_event_or_fsw(
            fprime_test_api,
            f"{producer}.DpProductionStarted",
            "DpProductionStarted",
            start=start,
            timeout_s=CMD_TIMEOUT_S,
            fsw_before=mark,
        )
    else:
        mark = fsw_mark("DpProductionStopped")
        send_cmd(fprime_test_api, f"{producer}.STOP_SERIALIZING")
        ev = await_event_or_fsw(
            fprime_test_api,
            f"{producer}.DpProductionStopped",
            "DpProductionStopped",
            start=start,
            timeout_s=CMD_TIMEOUT_S,
            fsw_before=mark,
        )
    assert ev is not None

    # DpActive rides the 1 Hz SensorMediumRate packet, so it recovers from RF
    # drops within a few seconds; poll with a generous window for a fresh sample.
    val = latest_channel_value(
        fprime_test_api, f"{producer}.DpActive", timeout_s=max(CMD_TIMEOUT_S, 10)
    )
    assert val is not None, "No DpActive telemetry sample after toggle"
    expect = True if enable else False
    assert bool(val) is expect, f"DpActive={val!r}, expected {expect}"

    state_path.write_text(next_state + "\n", encoding="utf-8")
    fprime_test_api.log(f"Persisted soak DP serialize state -> {next_state!r}")


def test_soak_interval_radio_still_commandable(fprime_test_api):
    """After duty-cycle toggle, still accept a command over RF."""
    wait_rf_quiet(2.0)
    send_cmd(fprime_test_api, "CdhCore.cmdDisp.CMD_NO_OP")
