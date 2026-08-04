"""SystemResources telemetry health -- mirrors the soak monitor's own checks.

The soak monitor (nasa/fprime-actions soak-test) trends SystemResources over the
whole soak and fails on: MEMORY_USED leak >= 5%, NON_VOLATILE_FREE < 1 GiB, or
CPU > 95%. This per-interval test is the fast feedback loop for those same
signals: it proves the channels are downlinking and are within sane bounds right
now, so a regression is caught in one interval instead of only after a long trend.
"""

from soak_helpers import CMD_TIMEOUT_S, latest_channel_value

SR = "FprimeSoakTestReference.systemResources"
# Soak monitor thresholds (Svc/SystemResources units: KB and percent).
NON_VOLATILE_FREE_FLOOR_KB = 1 * 1024 * 1024  # 1 GiB
HIGH_CPU_PERCENT = 95.0


def test_memory_used_present_and_sane(fprime_test_api):
    """MEMORY_USED downlinks and is a positive, below-total value."""
    used = latest_channel_value(fprime_test_api, f"{SR}.MEMORY_USED", timeout_s=15)
    total = latest_channel_value(fprime_test_api, f"{SR}.MEMORY_TOTAL", timeout_s=15)
    assert used is not None, "No MEMORY_USED sample (SystemResources not downlinking?)"
    assert float(used) > 0, f"MEMORY_USED not positive: {used}"
    if total is not None:
        assert 0 < float(used) <= float(total), f"MEMORY_USED {used} > MEMORY_TOTAL {total}"


def test_non_volatile_free_above_floor(fprime_test_api):
    """Free disk is above the soak monitor's 1 GiB floor."""
    free = latest_channel_value(
        fprime_test_api, f"{SR}.NON_VOLATILE_FREE", timeout_s=15
    )
    assert free is not None, "No NON_VOLATILE_FREE sample"
    assert float(free) >= NON_VOLATILE_FREE_FLOOR_KB, (
        f"NON_VOLATILE_FREE {float(free) / 1024 / 1024:.2f} GiB below 1 GiB floor"
    )


def test_cpu_below_threshold(fprime_test_api):
    """Average CPU load is below the soak monitor's 95% ceiling."""
    cpu = latest_channel_value(fprime_test_api, f"{SR}.CPU", timeout_s=CMD_TIMEOUT_S)
    assert cpu is not None, "No CPU sample"
    assert 0.0 <= float(cpu) <= HIGH_CPU_PERCENT, f"CPU {cpu}% exceeds {HIGH_CPU_PERCENT}%"
