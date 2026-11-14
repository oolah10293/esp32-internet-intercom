# Research baseline — source-verified versus untested

**Research snapshot:** 2026-11-14. **Evidence:** upstream GitHub files/commit history and manufacturer/provider documentation, read for this baseline. **No execution, compile, flashing, deployment or instrumented hardware tests have occurred for this project.**

This document records what the referenced sources actually show, not proof of successful intercom operation.

## Source reference and version

**Upstream:** https://github.com/sa7bnb/ip-radio-esp32c3

- Reviewed default branch: `main`
- Latest commit observed during review: `088bb7dbfe81608c4d01cb67545cc46995c09181` (README change to mention internet operation).
- Reviewed `README.md` at blob `5c5e883b2e80192c99a7d5a554516921bae3b8e5`.
- Reviewed `esp32_code.ino` (891 lines) at blob `91b64cde84804e279c1aa0ef0a74059eea772131`.
- Reviewed `server.py` (1179 lines) at blob `36a86dc4407f618ca342d2503762fd8d79dd8554`.
- The root listing contained the sketch, server, README, images and bundled `arduino-audio-driver-main.zip`; **no standalone standard LICENSE file** was present in that listing.
- README states personal/experimental use/modification is allowed. **Do not assume broad redistribution rights** from that wording; obtain clarification before publishing copied or derived upstream code.
- Upstream commit history reviewed; latest commits were primarily README updates. No evidence of verified two-ISP operation for our hardware was provided by the upstream repo.

Pinned source URLs:
- [Upstream README](https://github.com/sa7bnb/ip-radio-esp32c3/blob/088bb7dbfe81608c4d01cb67545cc46995c09181/README.md)
- [Upstream firmware](https://github.com/sa7bnb/ip-radio-esp32c3/blob/088bb7dbfe81608c4d01cb67545cc46995c09181/esp32_code.ino)
- [Upstream relay](https://github.com/sa7bnb/ip-radio-esp32c3/blob/088bb7dbfe81608c4d01cb67545cc46995c09181/server.py)

## Verified from upstream source (not verified in operation)

| Area | Source finding | Consequence for this project |
|---|---|---|
| Hardware | Firmware assumes ESP32-C3 Xmini with ES8311 I2S codec, NS4150B speaker amplifier, SSD1306 OLED and WS2812 LED. | Adapt to Seeed XIAO C3 + analog ADC mic + separate I2S amp. |
| PTT | BOOT/GPIO9 controls TX; release generates an optional 1760-Hz roger beep. | Use ordinary GPIO for external PTT and retain release semantics. |
| Audio format | 16-kHz mono, 16-bit PCM, 320 samples/20 ms, 640 audio bytes per outgoing frame. | Reuse format and frame pacing initially. |
| Buffer | RX circular jitter buffer holds at most 8 frames and waits for 5 frames before playback; underrun inserts silence. | Starting point for jitter handling; measure performance on internet. |
| Audio chain | TX DC-block filter, noise gate setting, gain and clipping; RX applies gain and writes I2S. | Parts can be reused conceptually; ES8311-specific sample format must change. |
| Server | Python asyncio UDP port 12345; aiohttp HTTP admin on port 8080; clients, room assignment, pending approval and persistent approved-node list. | Forwarding/management logic worth preserving; transport and security changes needed. |
| Identification | `NODE_NAME` string is sole permanent identifier for previously approved nodes; a new UDP address announcing an existing name replaces its session. | Not secure authentication; authenticated identity required before public exposure. |
| Audio security | Audio datagrams use magic bytes, type, client ID and 16-bit sequence; no cryptographic authentication or encryption in examined packet handling. | Do not expose original UDP server directly to internet. |
| Admin security | Session cookie, salted SHA-256 password hash, and plain HTTP listener (no HTTPS server in code). | Keep admin private or secure separately; do not publish default admin endpoint. |
| Half-duplex | PTT starts/stops local TX, but server forwards frames from any accepted source in a room without exclusive floor control. | Add explicit floor/busy arbitration to reliably prevent simultaneous talkers. |
| Boot failure | Firmware halts indefinitely if initial Wi-Fi connection fails or I2S initialization fails. | Must recover unattended rather than require power cycling. |
| Keepalive | HELLO sent every 5 s while Wi-Fi reports connected; server tracks 30 s client timeout. | Does not alone demonstrate recovery when transport or server changes state. |
| Shared buffer | Firmware TX/HELLO/audio paths use global outgoing packet state; multiple tasks can access UDP sending. | Audit concurrency and protect or separate buffers during changes. |
| Firmware stack | Uses the `driver/i2s_std.h` I2S API, I2S DMA and `arduino-audio-driver`. | Identify compatible Arduino ESP32 core before any compilation. |

## Verified from official external documentation

| Source | Verified documentation finding | Not established |
|---|---|---|
| [Tailscale Funnel](https://tailscale.com/docs/features/tailscale-funnel) | Public-access proxy for local service; clients do not need Tailscale; currently documented as beta; TLS required; Tailscale-hosted `.ts.net` naming; supported incoming ports 443/8443/10000; nonconfigurable bandwidth limits; available on all plans. | Published numeric bandwidth ceiling, persistent WebSocket uptime, latency, successful 24/7 voice on this Pi. |
| [Seeed XIAO ESP32-C3 guide](https://wiki.seeedstudio.com/XIAO_ESP32C3_Getting_Started/) | D0/GPIO2, D1/GPIO3 and D2/GPIO4 map to ADC1; D3/GPIO5 maps to ADC2 and Seeed cautions against ADC2 for reliable analog reads. | Exact selected pin plan with all peripherals and boot constraints. |
| [Espressif C3 continuous ADC driver](https://docs.espressif.com/projects/esp-idf/en/stable/esp32c3/api-reference/peripherals/adc_continuous.html) | C3 ADC driver supports continuous DMA-style sampling; one ADC module cannot operate in oneshot and continuous modes simultaneously; C3 ADC2 DMA results unstable. | Voice SNR with our analog microphone, exact Arduino-core API support, sampling while Wi-Fi traffic is active. |
| [Adafruit MAX4466 technical description](https://blog.adafruit.com/2012/10/10/new-product-electret-microphone-amplifier-max4466-with-adjustable-gain/) | MAX4466 mic module accepts 2.4–5V supply, provides adjustable analog gain and VCC/2 output bias; direct MCU ADC connection is described for that board. | Exact electrical characteristics of owner's pictured modules, trim setting, clipping at our ADC input. |
| [Adafruit MAX98357A description](https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp) | MAX98357A I2S amplifier supports 8–96 kHz, direct speaker drive and no MCLK. | Performance of specific low-cost breakout to be purchased and powered with our USB supply. |

**Owner-reported only:** working Tailscale on an existing Debian Raspberry Pi; XIAO C3 boards, MAX4466-style microphone boards, buttons and LEDs already owned; no monthly-cost service acceptable. Not independently audited on the physical equipment.

## Calculated estimates (derived from verified upstream constants, not measured)

- 16,000 samples/s × 16 bits/sample × 1 channel = **256,000 bits/s** audio payload while transmitting.
- 320 samples × 2 bytes = **640-byte audio frames** every 20 ms = 50 frames/s.
- Two clients with one active talker require a Pi relay to receive and send approximately **512 kbit/s of aggregate raw audio** across the two paths. Framing, TLS, HTTP/TCP, IP and link overhead increase actual transfer.
- The 5-frame startup threshold holds nominally **100 ms of audio**, not a guarantee of only 100 ms of end-to-end lag.
- Cost target: **$0 additional monthly** using existing Pi/Tailscale and free Funnel service. Additional hardware purchase is acceptable; no specific price is verified here.

## Technical risks: open, not hypothetical blockers asserted as facts

1. **Funnel performance:** undocumented numeric throughput and long-lived connection behavior; evaluate public WSS from an external ISP, with extended idle period, frame stream, recovery and Pi/Tailscale restart.
2. **Funnel/WSS compatibility:** Tailscale describes TLS TCP proxying but does not itself constitute a verified ESP32 WSS integration test.
3. **Analog input quality:** determine mic output bias/amplitude, 16-kHz ADC sampling stability while Wi-Fi is active, and resulting speech intelligibility. Filter/scale 12-bit ADC values to PCM without clipping.
4. **Volume control vs. ADC continuous mode:** design and verify shared ADC channels or different control input; avoid conflicting oneshot reads.
5. **ESP32 memory/toolchain:** confirm the chosen Arduino core supports the ADC/I2S/TLS/WSS stack and has enough resources, after authorization.
6. **Identity and security:** per-device credentials, TLS verification, no plaintext audio and no public unauthenticated admin.
7. **Room/busy and reconnect states:** implement measurable half-duplex and stale-session recovery, not just optimistic connected flags.
8. **Upstream code reuse rights:** personal/experimental rights stated; redistribution permission not established by standard license.

## Decision / evidence discipline

- **Adopted requirements:** physical PTT, automatic playback, half duplex, two ISPs, no monthly cost, minimal components, automatic recovery.
- **Working proposals:** C3 ADC mic + MAX98357A, Raspberry Pi relay exposed with Funnel, WSS with per-device credentials.
- **Not decided:** transport library, final pins, volume sampling/control, provisioning, floor-control protocol, latency acceptance threshold, and upstream code licensing for redistribution.
- **Not verified:** functioning two-node intercom or live Funnel capacity on owner's Raspberry Pi.

Advance each item to **VERIFIED** only with a dated experiment, wiring/software version and actual recorded result; log those in [validation-plan.md](validation-plan.md). This baseline is documentation only.
