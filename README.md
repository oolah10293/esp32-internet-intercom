# ESP32 Internet Intercom

Two small, USB-powered, push-to-talk intercom boxes in different houses. Each connects to local Wi-Fi; holding the PTT button transmits voice and the other box plays it automatically, with no call acceptance, phone, or app.

**Project phase: research/design only — no implemented or tested intercom yet.**
**Recurring-cost requirement: $0 additional per month.**

## Requirements

- Two standalone boxes, initially one in each household on separate internet providers.
- Press-and-hold PTT; release to listen; half-duplex and automatic incoming playback.
- Persistent readiness, automatic Wi-Fi/network recovery, clear connection/TX/RX indication.
- Adjustable speaker volume, adequate conversational audio quality and low perceived delay.
- Ordinary USB power, inexpensive hardware, minimal wiring and maintenance.
- Encrypted transport and authenticated device access, without residential port forwarding if feasible.
- No paid hosting service, no phone/computer/app for daily use.

## Current design direction (proposed, not verified end to end)

```text
House A: XIAO ESP32-C3 -- Wi-Fi -- Internet --+
                                              |
                                     Tailscale Funnel (public HTTPS endpoint)
                                              |
                                     Existing Debian Raspberry Pi
                                     Intercom relay service
                                              |
House B: XIAO ESP32-C3 -- Wi-Fi -- Internet --+
```

Both clients would initiate outbound **WSS (encrypted WebSocket)** connections to a Pi-hosted relay exposed through **Tailscale Funnel**. Funnel is available to non-Tailscale clients; the ESP32s would not need a Tailscale client. Device-specific authentication is still necessary because a Funnel endpoint is publicly reachable.

**Owner-reported existing equipment:** Seeed XIAO ESP32-C3 boards; MAX4466-style adjustable-gain amplified analog microphone modules; buttons and LEDs; a Raspberry Pi running Debian, House Audio and Tailscale.

**Proposed additions:** MAX98357A I²S mono amplifier and small speaker for each box; volume control (mechanism/pin allocation not finalized). No display or battery planned.

## Starting point

Evaluate and reuse components of [SA7BNB's IP-Radio ESP32-C3 project](https://github.com/sa7bnb/ip-radio-esp32c3) where permitted. It provides an Arduino firmware client and Python UDP relay with 16-kHz PCM, jitter buffer, PTT, room/node management and a web admin page. It targets **different audio hardware** (ES8311-based C3 Xmini board) and uses unencrypted UDP; it is not drop-in firmware for these boxes.

Do **not** import or republish upstream source merely because it is readable on GitHub. Its README grants personal/experimental use and modification but no standard license file was found in the reviewed root; clarify redistribution rights before publishing derivatives.

## Documentation / progress checkpoints

- [Architecture and hardware design](docs/architecture.md)
- [Research and upstream source audit](docs/research-baseline.md)
- [Validation plan and project checkpoints](docs/validation-plan.md)
- [Funnel/WebSocket probe instructions](tests/README.md)

## Current status

- **Verified from sources:** GitHub upstream code and official hardware/network documentation have been reviewed; details and URLs are logged in `docs/research-baseline.md`.
- **Owner-reported, not independently checked on equipment:** Raspberry Pi runs Tailscale; existing hardware listed above.
- **Verified by owner-provided browser screenshot on 2026-11-14:** WSS echo traffic through public Funnel HTTPS 10000 completed 5,131 sent/5,131 echoed 640-byte frames, with zero reported send backpressure and a 70.6 ms mean echo round trip. This is one browser session, not an ESP32 or different-ISP test.
- **Not yet verified:** hardware wiring, ADC audio quality, amplifier operation, continuous idle/reconnection reliability, real voice latency and two-house operation.
- **Current test progress:** isolated WSS/Funnel probe in `tests/funnel_probe.py` was run on the owner's Pi and returned all frames echoed in the observed browser test. Funnel HTTPS 10000 avoids existing Pi-hole port 8443 and private Tailscale Serve on 443.
- **Not done:** no intercom firmware/relay implementation, firmware build, firmware flash, service deployment or live WebSocket traffic testing.

## Change control

Keep GitHub as the project record. Record dated observations, exact test conditions, results and failures in `docs/validation-plan.md` (or linked later test logs). Never describe planned or untested changes as verified. **Do not implement, build, package, flash, install or deploy without the owner's explicit authorization for the corresponding action.** Documentation updates are separate from build/release approval.

**Baseline date:** 2026-11-14.
