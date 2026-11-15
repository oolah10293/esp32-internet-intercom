# Validation plan and progress checkpoints

**Last updated:** 2026-11-14. **Project state:** research/design with one owner-performed WebSocket/Funnel traffic test; no ESP32 firmware, intercom implementation or build.

This is a record of **proposed tests**, not evidence that any have run. No test, implementation, firmware build, Pi configuration change, or deployment is authorized by this document alone.

## Authorization boundary

- Documentation/research and GitHub documentation commits are allowed by the owner's request to establish this baseline.
- **Before coding, modifying firmware/server software or creating implementation files:** obtain explicit implementation authorization.
- **Before configuring Funnel on the live Raspberry Pi, starting a public endpoint, installing services, or performing tests:** obtain explicit test/deployment authorization for the specific action.
- **Before compiling/building firmware, packaging releases/installers or flashing hardware:** obtain separate explicit build/flash/release authorization as applicable.
- Do not interpret design agreement, "sounds good", a roadmap, or a test plan as build authorization.
- Preserve House Audio availability; do not alter existing House Audio services as a side effect.

## Test sequence (pending authorization)

### Checkpoint 0 — Documentation baseline

- [x] Confirm new repository, default branch and initial state through GitHub.
- [x] Review current upstream README, firmware, relay and commit history.
- [x] Verify relevant Seeed/Espressif/Adafruit/Tailscale documentation.
- [x] Record design direction, evidence, risks and known unknowns.
- [x] Read-back verification of all four documents from GitHub after initial commits (2026-11-14).

**Result:** documentation files and commit history confirmed from GitHub (README, architecture, research baseline, validation plan). No functional conclusions.

### Checkpoint 1 — Isolated Funnel connectivity, without ESP32s

**Goal:** determine whether a Pi-local service accessed via Funnel can keep an authenticated WSS connection and carry intercom-sized bidirectional messages reliably from a different ISP.

**Proposed approach, not yet performed:**
1. Check actual Pi Tailscale version, current Funnel state, and whether exposing a *separate* local port risks existing services. Do not change House Audio.
2. With approval, start a temporary isolated, authenticated test listener; enable Funnel for only that service; do not publish admin endpoints.
3. Connect from a true external network (not the same home LAN), send/receive frames at **640 bytes / 20 ms** while active, and record observed throughput, delay variation, reconnect events and error logs.
4. Leave the connection idle for a defined observation period (provisionally 24 h). Send lightweight keepalives, log every disconnect and reconnect.
5. Interrupt internet/Wi-Fi as controllable, restart the test listener/Pi/Tailscale only with explicit permission, and verify autonomous recovery.
6. Disable test exposure after validation unless continuing deployment was explicitly authorized.

**Pass principle:** no human intervention needed for recovery, audio-sized traffic is sustained, and latency/reconnect observations are acceptable for a press-to-talk voice device. Numeric acceptable thresholds to be agreed after preliminary measurement.

**Status:** FUNNEL WEBSOCKET ECHO TEST OBSERVED VIA OWNER SCREENSHOT; CROSS-ISP, LONG-IDLE AND RECOVERY TESTS STILL OPEN. The owner authorized the isolated Funnel/WebSocket test on 2026-11-14. Probe source at `tests/funnel_probe.py`; setup, security and cleanup instructions at `tests/README.md`. **Owner-supplied read-only Pi checks:** Tailscale 1.104.7 and Python 3.13.5; Serve uses 443 for a tailnet-only share; Pi-hole uses TCP 8443; no listener shown at TCP 10000 or 18765. Select **Funnel public HTTPS 10000**. No direct Pi access from assistant. Owner has started the local probe and public Funnel endpoint, and demonstrated a browser WebSocket traffic test. Browser ISP/path independence and unattended endurance are not yet verified.

### Checkpoint 2 — One-box local audio

**Goal:** sample the existing analog MAX4466-style mic on an XIAO ESP32-C3 and hear intelligible sound from a MAX98357A and speaker.

**Proposed checks:**
- Identify module markings and measure/confirm supply, DC offset and speaking-level peak range.
- Check confirmed pin allocation before wiring. Avoid ADC2 and boot-strapping surprises.
- Check ADC1 continuous sampling at 16 kHz, conversions to 16-bit signed samples, filtering and clipping.
- Verify I2S amplifier, acceptable volume and no objectionable Wi-Fi-related noise.
- Resolve volume-control method without mixing incompatible ADC operation modes.
- Record Arduino core, libraries, configuration and exact wiring.

**Status:** NOT STARTED. No hardware test performed.

### Checkpoint 3 — Single-node encrypted client

**Goal:** retain upstream PCM and PTT flow while replacing board-specific audio and UDP transport.

- Verify TLS hostname/certificate checking and device authentication; no hardcoded secrets in public GitHub.
- Establish session, heartbeat and auto-reconnect after Wi-Fi, DNS, server and Funnel interruptions.
- Verify one C3 can send and receive frames reliably through the test relay.
- Check free memory, heap fragmentation and CPU usage during long idle and repeated messages.
- Ensure any build/flash occurs only after specific authorization.

**Status:** NOT STARTED.

### Checkpoint 4 — Two-node behavior, same location

**Goal:** complete two-box PTT interaction with server arbitration.

- Box A PTT -> Box B hears automatically; Box B PTT -> Box A hears automatically.
- Both press at the same time -> predictable single-floor ownership; no double-talk.
- Release/disconnect mid-speech -> room unlocks and buffers clear without persistent stuck busy.
- Volume and status LEDs work; no phone/computer needed once configured.
- Reconnect each node after loss of Wi-Fi, relay and power.

**Status:** NOT STARTED.

### Checkpoint 5 — Two real households

**Goal:** verify the original objective across distinct residential internet providers.

- Repeat two-way PTT, idle availability and restart/reconnect tests.
- Measure actual press-to-audible onset, packet/buffer errors, missed speech and audible quality.
- Verify simple first-time setup and unattended operation.
- Compare the evidence with the project's requirements; mark any failures openly.

**Status:** NOT STARTED.

## Dated result log

| Date (UTC) | Checkpoint | Source / environment | Action | Result | Evidence |
|---|---|---|---|---|---|
| 2026-11-14 | 0 | GitHub + documentation websites | Read sources and establish docs | **SOURCE REVIEW ONLY; NO TESTS** | `README.md`, `docs/architecture.md`, `docs/research-baseline.md` |
| 2026-11-14 | 1 (preparation) | GitHub source only | Created isolated authenticated WSS echo harness and Pi runbook | **UNTESTED CODE; NOT DEPLOYED** | `tests/funnel_probe.py`, `tests/README.md` |
| 2026-11-14 | 1 (read-only checks) | Owner-reported Raspberry Pi terminal output | Examined Tailscale, port listeners and Python version | **8443 IN USE BY PI-HOLE; 10000 NOT SHOWN IN LISTENERS; NO FUNNEL TEST YET** | Owner terminal output in project chat |
| 2026-11-14 | 1 (startup) | Owner-provided two-terminal screenshot | Started isolated aiohttp probe on 127.0.0.1:18765 and foreground Tailscale Funnel on HTTPS 10000 | **LOCAL STARTUP AND FUNNEL PUBLIC URL ADVERTISED** | Screenshot in project chat; one-time token not reproduced |
| 2026-11-14 | 1 (WebSocket echo traffic) | Owner-provided browser screenshot of public Funnel test page on Windows PC | Sent 640-byte framed WebSocket traffic via advertised HTTPS 10000 endpoint and echoed back | **5,131 frames sent; 5,131 echoed; 0 skipped sends/backpressure; mean echo RTT 70.6 ms; ended with close code 1000.** This proves successful browser-to-Pi round trips for the observed session, **not** separate-household ISP operation, long-term reliability, or one-way voice latency. | Screenshot in project chat; test token omitted |

For future entries, include: source commit SHA, test commands/configuration, equipment and board revision, network topology, reproducible measurements, screenshots or logs if available, success/failure and outstanding defects. Do not mark success based only on source inspection.

## Remaining decisions

- [ ] Confirm exact analog mic board details and safe operating range at C3 input.
- [ ] Pick concrete GPIOs for mic, amp, PTT, LED and volume.
- [ ] Choose volume input implementation compatible with mic ADC sampling.
- [ ] Test whether Funnel supports a persistent WSS session from outside without material throttling or inactivity failures.
- [ ] Choose ESP32 Arduino core and WSS library after compatibility checks.
- [ ] Specify secure pairing/provisioning for the second household.
- [ ] Verify and document redistribution rights before importing upstream source.
- [ ] Authorize implementation and later builds/deployment separately.

## Next suggested step

**Current next step:** Observed initial WSS echo data over public Funnel HTTPS 10000. Run a controlled test from a genuinely separate ISP and an extended idle/reconnect test before declaring Checkpoint 1 complete. Keep existing Pi-hole on 8443 and private Tailscale Serve on 443 untouched. No permission to build/flash firmware or modify House Audio is implied.
