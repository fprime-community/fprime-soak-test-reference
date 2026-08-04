"""Helpers for soak RF integration tests (Ref-style; no pytest conftest).

GDS Test API guide:
https://fprime.jpl.nasa.gov/latest/docs/user-manual/gds/gds-test-api-guide/

RF HIL notes:
- OpCode EVRs often never reach GDS; confirm via Pi fsw.log when needed.
- While TRANSMIT is DISABLED, do not await downlinked EVRs (TX is off).
- File uplink is verified by FSW file size while muted.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

INT_DIR = Path(__file__).parent.resolve()
CONFIG_PATH = INT_DIR / "int_config.json"

with open(CONFIG_PATH, encoding="utf-8") as _cfg:
    CONFIG: dict = json.load(_cfg)

FSW_TMP = str(CONFIG.get("soak.fsw_tmp", "/tmp"))
CMD_TIMEOUT_S = int(CONFIG.get("soak.cmd_timeout_s", 30))
UPLINK_TIMEOUT_S = int(CONFIG.get("soak.uplink_timeout_s", 90))
UPLINK_LARGE_TIMEOUT_S = int(CONFIG.get("soak.uplink_large_timeout_s", 120))
DP_PRODUCE_TIMEOUT_S = int(CONFIG.get("soak.dp_produce_timeout_s", 45))
DP_XMIT_TIMEOUT_S = int(CONFIG.get("soak.dp_xmit_timeout_s", 90))
PI_HOST = os.environ.get("SOAK_PI_HOST", "pi@raspberrypi.local")
FSW_LOG = os.environ.get("SOAK_FSW_LOG", "/home/pi/fprime/fsw.log")


def dp_serialize_state_path() -> Path:
    name = os.environ.get("DEPLOYMENT_NAME", "fprime-soak-test-reference")
    return Path.home() / f".fprime-soak-{name}-dp-serialize"


def cmd(api, component_key: str, command: str) -> str:
    return f"{api.get_mnemonic(component_key)}.{command}"


def pi_ssh(remote_cmd: str, timeout: int = 15) -> str:
    return subprocess.check_output(
        [
            "ssh",
            "-o",
            "ConnectTimeout=8",
            "-o",
            "BatchMode=yes",
            PI_HOST,
            remote_cmd,
        ],
        text=True,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )


def pi_put(local_path: Path, dest: str, timeout: int = 30) -> None:
    """Copy a local file to the FSW over SSH (integrity-guaranteed staging).

    Used when a test needs a *correct* file on the FSW independent of RF-uplink
    reliability (e.g. a sequence for CmdSequencer): RF uplink can silently corrupt
    bytes, so we do not route test fixtures through it.
    """
    subprocess.check_call(
        ["scp", "-o", "ConnectTimeout=8", "-o", "BatchMode=yes", str(local_path),
         f"{PI_HOST}:{dest}"],
        timeout=timeout,
    )


def fsw_log_count(pattern: str) -> int:
    try:
        out = pi_ssh(f"grep -cE '{pattern}' {FSW_LOG} || true").strip()
        return int(out.splitlines()[-1] or "0")
    except Exception:
        return -1


def opcode_hex(api, command: str) -> str:
    cmd_id = api.translate_command_name(command)
    return f"0x{cmd_id:x}" if isinstance(cmd_id, int) else str(cmd_id)


def set_default_filters(api) -> None:
    for severity in (
        "COMMAND",
        "ACTIVITY_LO",
        "ACTIVITY_HI",
        "WARNING_LO",
        "WARNING_HI",
    ):
        api.send_command("CdhCore.events.SET_EVENT_FILTER", [severity, "ENABLED"])
        time.sleep(0.5)
    api.send_command("CdhCore.events.SET_EVENT_FILTER", ["DIAGNOSTIC", "DISABLED"])
    time.sleep(1.5)
    api.clear_histories()


def _confirm_fsw_completed(
    api, command: str, args: list, before: int, timeout_s: int
) -> bool:
    ox = opcode_hex(api, command)
    deadline = time.time() + timeout_s
    resent = False
    while time.time() < deadline:
        after = fsw_log_count(f"OpCodeCompleted.*Opcode {ox}")
        if after < 0:
            after = fsw_log_count(f"OpCodeCompleted.*{ox}")
        if before >= 0 and after > before:
            api.log(f"FSW confirmed {command} ({ox}) completed")
            return True
        if not resent and time.time() > deadline - timeout_s + 4:
            api.send_command(command, args)
            resent = True
        time.sleep(1.0)
    return False


def send_cmd(api, command: str, args=None, timeout_s: int = CMD_TIMEOUT_S, events=None):
    """send_and_assert_command, with FSW-log confirmation if RF drops EVRs."""
    args = args or []
    ox = opcode_hex(api, command)
    before = fsw_log_count(f"OpCodeCompleted.*Opcode {ox}")
    if before < 0:
        before = fsw_log_count(f"OpCodeCompleted.*{ox}")

    try:
        return api.send_and_assert_command(
            command,
            args,
            max_delay=1.0,
            timeout=int(timeout_s),
            events=events,
        )
    except AssertionError as exc:
        api.log(f"GDS EVR assert missed for {command}; checking FSW log")
        after = fsw_log_count(f"OpCodeCompleted.*Opcode {ox}")
        if after < 0:
            after = fsw_log_count(f"OpCodeCompleted.*{ox}")
        if before >= 0 and after > before:
            api.log(f"FSW already confirmed {command} ({ox})")
            return []
        api.send_command(command, args)
        if _confirm_fsw_completed(api, command, args, before, timeout_s):
            return []
        raise AssertionError(
            f"Command {command} ({ox}) not confirmed via GDS EVRs or FSW log"
        ) from exc


def mute_downlink(api) -> None:
    """Disable flight TX without expecting downlinked OpCode EVRs."""
    command = cmd(api, "Rfm69.Rfm69Manager", "TRANSMIT")
    api.send_command(command, ["DISABLED"])
    time.sleep(1.5)


def unmute_downlink(api, timeout_s: int = CMD_TIMEOUT_S) -> None:
    """Re-enable flight TX and prove the path with a NO-OP."""
    command = cmd(api, "Rfm69.Rfm69Manager", "TRANSMIT")
    api.send_command(command, ["ENABLED"])
    time.sleep(1.5)
    send_cmd(api, "CdhCore.cmdDisp.CMD_NO_OP", timeout_s=timeout_s)


def rf_uplink(
    api,
    local_path: Path,
    dest: str,
    uplink_timeout_s: int = UPLINK_TIMEOUT_S,
) -> None:
    """Uplink over RF with TX muted; verify by FSW file size (EVRs cannot downlink)."""
    expected = local_path.stat().st_size
    last_size = -1
    mute_downlink(api)
    try:
        for attempt in range(2):
            try:
                pi_ssh(f"rm -f {dest}")
            except Exception:
                pass
            api.uplink_file(str(local_path), dest)
            deadline = time.time() + int(uplink_timeout_s)
            last_size = -1
            while time.time() < deadline:
                try:
                    # Avoid `wc < missing` (bash redirect error); always emit an int.
                    out = pi_ssh(
                        f"if [ -f {dest} ]; then wc -c < {dest}; else echo 0; fi"
                    ).strip()
                    size = int(out.splitlines()[-1])
                    if size != last_size:
                        api.log(
                            f"uplink attempt {attempt + 1} {dest} size={size}/{expected}"
                        )
                        last_size = size
                    if size == expected:
                        api.log(f"FSW file size match for {dest} ({size} bytes)")
                        return
                except Exception as exc:
                    api.log(f"size poll error: {exc}")
                time.sleep(1.0)
            api.log(f"uplink attempt {attempt + 1} incomplete (size {last_size}/{expected})")
        raise AssertionError(
            f"Uplink failed for {local_path} -> {dest} (size {last_size}/{expected})"
        )
    finally:
        unmute_downlink(api)


def fsw_mark(pattern: str) -> int:
    """Capture an FSW-log baseline count for `pattern`.

    Call this BEFORE the command/action that produces the event, then pass the
    result as `fsw_before` to await_event_or_fsw. This avoids the race where the
    event is already written to fsw.log by the time the fallback samples its
    baseline (the triggering command has usually completed inside send_cmd), which
    would make growth-detection wait forever for a second occurrence.
    """
    return fsw_log_count(pattern)


def await_event_or_fsw(
    api,
    event_name: str,
    fsw_pattern: str,
    start,
    timeout_s: int,
    fsw_before: int | None = None,
):
    """Await a GDS event (including already-buffered), else FSW-log growth.

    Over the lossy RF link EVRs are frequently dropped on downlink, so the FSW
    log is the source of truth. Pass `fsw_before` captured via fsw_mark() BEFORE
    the triggering command; if omitted we sample now (only correct when the event
    has not been produced yet).
    """
    if fsw_before is None:
        fsw_before = fsw_log_count(fsw_pattern)
    # Already in GDS history?
    ev = api.await_event(event_name, start=start, timeout=0)
    if ev is not None:
        return ev
    ev = api.await_event(event_name, start=start, timeout=int(timeout_s))
    if ev is not None:
        return ev
    deadline = time.time() + timeout_s
    while True:
        after = fsw_log_count(fsw_pattern)
        if fsw_before >= 0 and after > fsw_before:
            api.log(f"FSW confirmed event pattern {fsw_pattern!r} (EVR likely dropped)")
            return True
        if time.time() >= deadline:
            return None
        time.sleep(1.0)


def clear_dp_catalog_dir() -> None:
    """Remove accumulated .fdp files so BUILD_CATALOG / xmit stay small."""
    try:
        # FSW cwd is /home/pi/fprime; catalog is ./DpCat
        pi_ssh("rm -f /home/pi/fprime/DpCat/*.fdp 2>/dev/null; mkdir -p /home/pi/fprime/DpCat")
    except Exception:
        pass


def wait_rf_quiet(seconds: float = 3.0) -> None:
    time.sleep(seconds)


def latest_channel_value(api, channel: str, timeout_s: int = CMD_TIMEOUT_S):
    """Return the most recent value of a telemetry channel, or None.

    Prefers a freshly downlinked sample (await_telemetry) but falls back to the
    newest matching sample already in history -- over lossy RF a given channel
    may not update within the window even though earlier samples arrived.
    """
    update = api.await_telemetry(channel, timeout=int(timeout_s))
    if update is not None:
        return update.get_val()
    history = api.get_telemetry_test_history()
    latest = None
    for item in history.retrieve():
        try:
            if item.get_full_name() == channel:
                latest = item
        except Exception:
            continue
    return latest.get_val() if latest is not None else None
