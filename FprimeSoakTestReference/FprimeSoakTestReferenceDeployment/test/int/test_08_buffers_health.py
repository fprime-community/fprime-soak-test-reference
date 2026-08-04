"""BufferManager + Health checks -- the other half of the soak monitor's gate.

The soak monitor trends every managed pool's CurrBuffs (leak alert at >= 20%) and
alerts if NoBuffs or EmptyBuffs is ever > 0; health degradation surfaces as
CdhCore.health.PingLateWarnings > 0.

Telemetry-rate nuance (measured on HW): TlmPacketizer uses ON_CHANGE rate logic,
so a packet only downlinks when one of its channels changes.
  * ComCcsds.commsBufferManager allocates/frees a buffer on every RF packet, so
    its packet downlinks ~continuously -- we use it to prove telemetry liveness.
  * The DataProducts / DpCompression pools only change when a data product is
    produced (~every 25 s while serializing) or not at all when idle, so their
    CurrBuffs downlinks slowly/never. Requiring a fresh sample would be flaky.
  * The error counters (NoBuffs, EmptyBuffs, PingLateWarnings) sit at a constant 0
    in nominal ops, so they downlink rarely -- but a nonzero value IS a change and
    downlinks immediately, exactly when the monitor needs it.

So this suite proves liveness once via the comms pool, and everywhere else asserts
"within bounds / zero *if a sample is present*" -- catching every real fault
(nonzero error, CurrBuffs > TotalBuffs) without false failures from ON_CHANGE.
"""

import pytest

from soak_helpers import latest_channel_value

LIVENESS_POOL = "ComCcsds.commsBufferManager"
POOLS = [
    "ComCcsds.commsBufferManager",
    "DataProducts.dpBufferManager",
    "DpCompression.dpZLibCompressorBufferManager",
]


def test_telemetry_path_alive(fprime_test_api):
    """commsBufferManager.CurrBuffs ticks on every RF packet -> proves TM is live."""
    curr = latest_channel_value(
        fprime_test_api, f"{LIVENESS_POOL}.CurrBuffs", timeout_s=15
    )
    assert curr is not None, "No commsBufferManager.CurrBuffs sample (telemetry path down?)"
    assert int(curr) >= 0, f"CurrBuffs negative: {curr}"


@pytest.mark.parametrize("pool", POOLS)
def test_buffer_manager_curr_within_total(fprime_test_api, pool):
    """CurrBuffs stays within TotalBuffs when reported (ON_CHANGE: absence is OK).

    A leak makes CurrBuffs rise, which is a change and downlinks -- so a real leak
    surfaces here; a steady/idle pool that simply hasn't re-sent does not fail.
    """
    curr = latest_channel_value(fprime_test_api, f"{pool}.CurrBuffs", timeout_s=8)
    total = latest_channel_value(fprime_test_api, f"{pool}.TotalBuffs", timeout_s=8)
    if curr is None:
        fprime_test_api.log(f"{pool}: no CurrBuffs sample this window (ON_CHANGE, idle)")
        return
    assert int(curr) >= 0, f"{pool}.CurrBuffs negative: {curr}"
    if total is not None:
        assert int(curr) <= int(total), f"{pool}.CurrBuffs {curr} > TotalBuffs {total}"


@pytest.mark.parametrize("pool", POOLS)
def test_buffer_manager_no_alloc_failures(fprime_test_api, pool):
    """NoBuffs/EmptyBuffs are 0 when reported (ON_CHANGE: absence == nominal 0)."""
    no_buffs = latest_channel_value(fprime_test_api, f"{pool}.NoBuffs", timeout_s=8)
    empty_buffs = latest_channel_value(fprime_test_api, f"{pool}.EmptyBuffs", timeout_s=8)
    if no_buffs is not None:
        assert int(no_buffs) == 0, f"{pool}.NoBuffs={no_buffs} (allocation failures)"
    if empty_buffs is not None:
        assert int(empty_buffs) == 0, f"{pool}.EmptyBuffs={empty_buffs} (null/zero returns)"
    if no_buffs is None and empty_buffs is None:
        fprime_test_api.log(
            f"{pool}: no NoBuffs/EmptyBuffs sample this window (ON_CHANGE, nominal 0)"
        )


def test_health_no_ping_late_warnings(fprime_test_api):
    """Health reports no late pings when reported (ON_CHANGE: absence == nominal 0)."""
    late = latest_channel_value(
        fprime_test_api, "CdhCore.health.PingLateWarnings", timeout_s=8
    )
    if late is None:
        fprime_test_api.log(
            "PingLateWarnings: no sample this window (ON_CHANGE, nominal 0 -- healthy)"
        )
        return
    assert int(late) == 0, f"Health reported {late} late ping warnings"
