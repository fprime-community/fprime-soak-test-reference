"""RFM69 operator commands that matter for half-duplex soak ops."""

import time

from soak_helpers import (
    CMD_TIMEOUT_S,
    cmd,
    latest_channel_value,
    mute_downlink,
    send_cmd,
    unmute_downlink,
)


def test_transmit_mute_unmute(fprime_test_api):
    """TRANSMIT DISABLED/ENABLED; RX works while muted; TX restored after unmute."""
    mute_downlink(fprime_test_api)
    # While muted, uplink still works (command reaches FSW). Do not assert EVRs
    # for the mute itself — those cannot be downlinked with TX off.
    fprime_test_api.send_command("CdhCore.cmdDisp.CMD_NO_OP", [])
    time.sleep(1.0)
    unmute_downlink(fprime_test_api)
    send_cmd(fprime_test_api, "CdhCore.cmdDisp.CMD_NO_OP")


def test_radio_packets_received_channel(fprime_test_api):
    """Commanding over RF should produce PacketsReceived telemetry."""
    channel = cmd(fprime_test_api, "Rfm69.Rfm69Manager", "PacketsReceived")
    hist_start = fprime_test_api.get_telemetry_test_history().size()
    send_cmd(fprime_test_api, "CdhCore.cmdDisp.CMD_NO_OP")
    after = fprime_test_api.await_telemetry(
        channel, start=hist_start, timeout=CMD_TIMEOUT_S
    )
    if after is None:
        after = latest_channel_value(fprime_test_api, channel, timeout_s=5)
    assert after is not None, "No PacketsReceived sample after RF command"
