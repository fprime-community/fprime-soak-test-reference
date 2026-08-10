# Soak / integration tests — FprimeSoakTestReferenceDeployment

Pytest suite for the RF soak deployment. Compatible with
[`nasa/fprime-actions/soak-test`](https://github.com/nasa/fprime-actions): each
~30 minute soak interval first runs `soak_monitor.py` over accumulated telemetry,
then runs everything under this directory against the persistent GDS.

Layout matches [Ref `test/int`](https://github.com/nasa/fprime/tree/devel/TestDeploymentsProject/Ref/test/int):
no custom `conftest.py` — fixtures come from `fprime-gds`; helpers live in
`soak_helpers.py`.

## What the soak monitor gates on (why these tests exist)

`soak_monitor.py` fails an interval on **any** `FATAL` / `WARNING_HI` /
`WARNING_LO` event in the GDS log, plus: `MEMORY_USED` leak ≥ 5 %, any
`BufferManager` `CurrBuffs` leak ≥ 20 %, any `NoBuffs`/`EmptyBuffs` > 0,
`CPU` > 95 %, or `NON_VOLATILE_FREE` < 1 GiB. Two consequences drive this suite:

1. **Tests must not emit warnings.** Events produced *during* pytest land in the
   same GDS log the monitor reads next interval. So the DP tests never issue a
   `STOP_XMIT_CATALOG` while idle (`XmitNotActive`) or a second `START_XMIT`
   (`DpXmitInProgress`), and the multi-chunk uplink test is skipped (see below).
2. **`test_07`/`test_08` mirror the monitor's own thresholds** so a regression in
   memory, buffers, CPU, disk, or health is caught in one interval instead of
   only after a long trend.

## What is covered

| Module | Purpose |
|--------|---------|
| `test_01_link.py` | TM streaming + command NO-OP over RF |
| `test_02_radio.py` | `TRANSMIT` mute/unmute; `PacketsReceived` |
| `test_03_file_uplink.py` | Small + sequence single-chunk uplink (multi-chunk skipped) |
| `test_04_sequence.py` | `CS_VALIDATE` + `CS_RUN` of uplinked sequence |
| `test_05_dataproducts.py` | Catalog build, serialize → `.fdp`, self-draining catalog xmit |
| `test_06_soak_interval.py` | Alternates `START`/`STOP_SERIALIZING` each soak run |
| `test_07_system_resources.py` | `MEMORY_USED`/`NON_VOLATILE_FREE`/`CPU` present & within monitor thresholds |
| `test_08_buffers_health.py` | All 3 `BufferManager` pools (`NoBuffs`/`EmptyBuffs`=0, `CurrBuffs`≤`TotalBuffs`) + `Health.PingLateWarnings`=0 |

Half-duplex note: file-uplink helpers mute `Rfm69.rfm69Manager.TRANSMIT` for the
transfer, then re-enable. DP downlink leaves TX enabled (it *is* the downlink).

## RF-loss discipline (EVR fallback)

Over the lossy 19.2 kb/s half-duplex link, downlinked EVRs are frequently
dropped, so **the Pi's `fsw.log` is the source of truth** for command effects.
`await_event_or_fsw()` first checks the GDS event history, then falls back to
growth in `fsw.log`. The FSW-log baseline **must be captured with `fsw_mark()`
before the triggering command** — otherwise the command completes (and logs its
event) inside `send_cmd` before the baseline is sampled, and growth detection
waits forever for a second occurrence. `send_cmd()` similarly confirms via
`OpCodeCompleted` in `fsw.log` when the GDS `OpCode` EVR is dropped.

## Flight runtime requirement: realtime scheduling

The FSW binary **must** run with `CAP_SYS_NICE` so F´ Posix tasks get `SCHED_RR`
priorities. Without it the 1 kHz base rate group runs `SCHED_OTHER` and
`RateGroupCycleSlip` (WARNING_HI) floods the soak log, failing the gate. The
`nasa/fprime-actions` `deploy.sh` does this via `setcap cap_sys_nice=eip`; the Pi
launcher `run_fsw.sh` does the same. Verify with `getcap <binary>` and confirm
`SCHED_RR` threads via `ps -eLo pid,cls,rtprio,comm`.

## Parameter DB

On first boot with no `PrmDb.dat`, `PrmDb` emits `PrmFileReadError` (WARNING_HI)
and `PrmIdNotFound` (WARNING_LO). Run the `seq/fix_prm_missing.bin` sequence once
(it sets all defaults and `PRM_SAVE_FILE`s them); subsequent boots are clean.

## Known limitations

* **Multi-chunk file uplink is unreliable and intentionally skipped.** F´
  `Svc.FileUplink` has no ARQ, so a single dropped/corrupted DATA packet on the
  lossy half-duplex RF link stalls the whole transfer and emits
  `InvalidReceiveMode` / `InvalidPacketReceived` (WARNING_HI). Measured on HW;
  widening `file-uplink-cooldown` did not help. Single-chunk (≤ 255 B MTU)
  uplink is reliable and covered. Run the skipped case manually while
  investigating uplink: `pytest --runxfail -k larger_than_mtu` (expect flakes).
* **`UnexpectedSequenceCount` (WARNING_LO)** can still appear from genuine RF
  packet loss; it reflects link physics, not a flight defect.

## Local HIL run (GDS already up)

```bash
cd FprimeSoakTestReference/FprimeSoakTestReferenceDeployment/test/int
export SOAK_PI_HOST=pi@raspberrypi.local   # ssh target for fsw.log / uplink checks
pytest -o python_files='test_*.py' -rs \
  --dictionary ../../../../build-artifacts/aarch64-linux/FprimeSoakTestReference_FprimeSoakTestReferenceDeployment/dict/FprimeSoakTestReferenceDeploymentTopologyDictionary.json \
  --deployment-config int_config.json \
  --tts-port 52051 --tts-addr 127.0.0.1
```

Bring up a GUI GDS first (`fprime-gds --tts-port 52051 --tts-addr 127.0.0.1`) so
`channel.log`/`event.log` populate; the deployment's `fprime-gds.yml` supplies the
UART device, baud, framing, and file-uplink pacing.

## Config knobs (`int_config.json`)

| Key | Role |
|-----|------|
| `soak.fsw_tmp` | FSW-side uplink destination dir (default `/tmp`) |
| `soak.cmd_timeout_s` | Command / EVR waits |
| `soak.uplink_timeout_s` | Single-chunk RF uplink wait |
| `soak.uplink_large_timeout_s` | Multi-chunk uplink wait (skipped test) |
| `soak.dp_*_timeout_s` | DP produce / xmit waits |

Env: `SOAK_PI_HOST` (default `pi@raspberrypi.local`), `SOAK_FSW_LOG` (default
`/home/pi/fprime/fsw.log`). DP serialize duty state is stored at
`~/.fprime-soak-${DEPLOYMENT_NAME}-dp-serialize` (`on`/`off`).
