"""CmdSequencer: validate and run a sequence over RF.

The sequence binary is staged on the FSW over SSH, not RF-uplinked: RF can
silently corrupt bytes (a size-matching uplink still failed CS_VALIDATE with
CS_FileCrcFailure on HW), and this test is about the sequencer, not uplink
integrity. Uplink itself is covered by test_03.
"""

from pathlib import Path

from soak_helpers import (
    CMD_TIMEOUT_S,
    FSW_TMP,
    await_event_or_fsw,
    fsw_mark,
    pi_put,
    send_cmd,
)

INT_DIR = Path(__file__).parent.resolve()


def test_sequence_validate_and_run(fprime_test_api):
    """CS_VALIDATE + CS_RUN BLOCK on an SSH-staged sequence binary."""
    local = INT_DIR / "sequences" / "soak_radio_probe.bin"
    assert local.is_file(), (
        f"missing {local}; compile sequences/soak_radio_probe.seq with fprime-seqgen"
    )
    seq_path = f"{FSW_TMP}/soak_seq_staged.bin"
    pi_put(local, seq_path)

    sequencer = fprime_test_api.get_mnemonic("Svc.CmdSequencer")
    send_cmd(fprime_test_api, f"{sequencer}.CS_VALIDATE", [seq_path])

    # Baseline the FSW log BEFORE CS_RUN so the EVR-loss fallback detects the
    # completion even if the CS_SequenceComplete EVR is dropped on downlink.
    fsw_before = fsw_mark("CS_SequenceComplete")
    start = fprime_test_api.get_event_test_history().size()
    send_cmd(fprime_test_api, f"{sequencer}.CS_RUN", [seq_path, "BLOCK"])
    done = await_event_or_fsw(
        fprime_test_api,
        f"{sequencer}.CS_SequenceComplete",
        "CS_SequenceComplete",
        start=start,
        timeout_s=CMD_TIMEOUT_S,
        fsw_before=fsw_before,
    )
    assert done is not None, "CS_SequenceComplete not observed"
