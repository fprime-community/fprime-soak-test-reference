"""Basic radio / GDS link health (GDS Test API / Ref patterns)."""

import time

from soak_helpers import (
    CMD_TIMEOUT_S,
    fsw_log_count,
    send_cmd,
    set_default_filters,
    wait_rf_quiet,
)


def test_telemetry_streaming(fprime_test_api):
    """FSW is alive and TM is crossing the RF link into GDS."""
    results = fprime_test_api.assert_telemetry_count(3, timeout=CMD_TIMEOUT_S)
    assert results, "Expected telemetry updates over the radio link"


def test_command_noop_over_radio(fprime_test_api):
    """Ground → RF → cmdDisp NO-OP (Ref test_send_command)."""
    set_default_filters(fprime_test_api)
    send_cmd(fprime_test_api, "CdhCore.cmdDisp.CMD_NO_OP")
    assert fprime_test_api.get_command_test_history().size() >= 1


def test_command_noop_string_over_radio(fprime_test_api):
    """NO-OP with string argument (Ref test_send_command_args)."""
    value = "soak-radio-probe"
    events = [
        fprime_test_api.get_event_pred(
            "CdhCore.cmdDisp.NoOpStringReceived",
            [value],
        )
    ]
    send_cmd(
        fprime_test_api,
        "CdhCore.cmdDisp.CMD_NO_OP_STRING",
        [value],
        events=events,
    )


def test_downlink_opcode_events_reach_gds(fprime_test_api):
    """OpCode EVRs must be generated onboard; GDS should see most of them.

    Pi fsw.log is the source of truth (RF can drop a downlink packet). Spacing
    exceeds flight RX_TX_HOLDOFF so each command's EVRs get a TX window.
    """
    wait_rf_quiet(1.0)
    before = fsw_log_count("NoOpReceived")
    gds_ok = 0
    for _ in range(5):
        start = fprime_test_api.get_event_test_history().size()
        # Do not use max_delay: Dispatched and Completed often land >1 s
        # apart on RF, which fails send_and_assert_command even when both
        # EVRs arrive. send_cmd confirms via FSW; GDS is scored separately.
        send_cmd(fprime_test_api, "CdhCore.cmdDisp.CMD_NO_OP")
        if fprime_test_api.await_event(
            "CdhCore.cmdDisp.NoOpReceived", start=start, timeout=5
        ) is not None:
            gds_ok += 1
        time.sleep(1.2)
    after = fsw_log_count("NoOpReceived")
    onboard = (after - before) if before >= 0 and after >= 0 else -1
    fprime_test_api.log(f"NO-OP EVRs: onboard={onboard} GDS={gds_ok}/5")
    assert onboard >= 5, f"FSW only logged {onboard} NoOpReceived (events not generated)"
    assert gds_ok >= 3, (
        f"GDS saw {gds_ok}/5 NO-OP EVR sequences; onboard had {onboard} "
        "(generated on Pi, dropped on RF downlink)"
    )
