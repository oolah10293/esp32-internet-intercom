# Proposed architecture and hardware

**Status:** DESIGN PROPOSAL, not implemented or bench-verified. **Last reviewed:** 2026-11-14.
See [research baseline](research-baseline.md) for source evidence and [validation plan](validation-plan.md) for acceptance tests.

## Intended operation

1. Each box starts on USB power and joins its own Wi-Fi automatically.
2. Each box establishes an authenticated, encrypted outbound connection to a relay on the existing Raspberry Pi.
3. While idle, both connections remain ready and exchange lightweight keepalives.
4. Holding a physical PTT button starts live microphone sampling and voice transmission. The remote box plays incoming audio immediately after normal buffering; no acceptance action.
5. Releasing PTT ends the transmission; the recipient can then speak. Implement clear busy/receive semantics when both PTT buttons are pressed.
6. If Wi-Fi, DNS, relay or internet access fails, indicate offline state, back off and retry automatically, and re-register after reconnection.

No phone or computer should be needed in normal use. First-time Wi-Fi provisioning is to be designed separately.

## Network proposal

```text
        Residential ISP A                  Residential ISP B
     +--------------------+              +--------------------+
     | XIAO ESP32-C3 #1   |              | XIAO ESP32-C3 #2   |
     | MAX4466 -> ADC     |              | MAX4466 -> ADC     |
     | I2S -> MAX98357A   |              | I2S -> MAX98357A   |
     +----------+---------+              +----------+---------+
                | outbound WSS                       | outbound WSS
                +-------------------+----------------+
                                    |
                            Internet, TLS
                                    |
                          Tailscale Funnel URL
                          (publicly reachable)
                                    |
                       Raspberry Pi (owner's)
                          local-only voice service
                       - authenticate each device
                       - manage online state
                       - enforce half-duplex turn
                       - forward audio frames
```

- **Proposed transport:** WSS/WebSocket messages carrying short PCM frames. Connection per box is long-lived while power and internet are available.
- **Proposed hosting:** Debian Raspberry Pi already used for House Audio and reported to have Tailscale installed. Keep intercom processes and ports separate from House Audio.
- **Proposed exposure:** Funnel provides a publicly accessible TLS endpoint to a specifically bound local service on the Pi. Do not expose the existing House Audio or an unauthenticated management page through Funnel.
- **Authentication:** distinct non-public credential per box; verify on each new connection and authorize room membership. `NODE_NAME` is a display label, not a secret. Never commit credentials, Wi-Fi passwords, access tokens or private keys.
- **Connection integrity:** verify server TLS certificate/hostname on ESP32; do not disable validation as a shortcut. Test C3 library memory and connection recovery.
- **Availability:** reconnection must be resilient on both client and server. Funnel may drop or throttle connections; no published indefinite-session guarantee was established in research. Keep this risk open until tested.
- **Backup idea, not an adopted design:** direct Pi hosting with dynamic DNS and router port forwarding if Funnel proves unsuitable and the home ISP allows incoming connections.

**Not decided:** exact protocol message schema, PTT arbitration behavior at disconnects, authenticated provisioning, heartbeat interval and transport library. Avoid a protocol rewrite beyond what secure transport requires.

## Audio proposal

Follow the upstream sample format initially rather than add compression or other complexity:

- 16,000 samples/sec, one channel, signed 16-bit PCM.
- 320 samples (20 ms) per audio frame = 640 bytes of payload per frame.
- 50 frames/sec => 32,000 bytes/sec => **256 kbit/s** raw audio payload during PTT.
- Upstream UDP packet: 6-byte header + 640 audio bytes = 646 bytes before IP/UDP headers. A new WebSocket representation is NOT implemented yet.
- With two endpoints and one active talker, the Pi accepts and re-sends roughly 256 kbit/s of raw audio, or about 512 kbit/s of aggregate raw ingress+egress. Actual network transfer rates will be higher.
- Reuse/port the upstream basic filtering, gain adjustment and jitter buffer where suitable. Upstream starts playback when five 20-ms frames have been buffered (nominal 100 ms audio buffer). End-to-end latency is unknown until tested.
- A WSS/TCP connection may experience retransmission delays on impaired networks; measure rather than assume suitability.

## Proposed hardware per box

| Item | Status | Design notes |
|---|---|---|
| Seeed XIAO ESP32-C3 | Owner has | Primary target; no S3 requirement |
| MAX4466-style adjustable-gain analog electret mic | Owner has, identity based on supplied image | Amplifier included; proposed supply 3V3, GND common, output to ADC1 pin |
| MAX98357A I2S mono amplifier | Proposed purchase | Direct speaker drive, no separate DAC or I2S mic needed |
| 4–8 ohm small speaker | Proposed | Match amplifier and power supply |
| PTT button | Owner has | Active-low GPIO with pull-up; avoid boot-strapping GPIO |
| Connection/TX/RX LED | Owner has | One multi-color LED or simple separate indications, final pin assignment TBD |
| Adjustable volume | Required, mechanism TBD | Analog pot possible but C3 ADC allocation/driver interaction needs a decision |
| USB power supply | Ordinary existing/new USB supply | No battery |
| OLED, display, ES8311 codec | Not planned | Upstream board-specific peripherals to omit |

### ADC details worth checking first

- Seeed documents XIAO ESP32-C3 **D1 = GPIO3 = ADC1_CH3**, **D0 = GPIO2 = ADC1_CH2**, **D2 = GPIO4 = ADC1_CH4**. Seeed cautions against relying on D3/GPIO5 (ADC2) for analog sampling.
- **Tentative microphone input:** D1/GPIO3; not a final electrical/wiring sign-off. Use the MIC module's 3V3 supply and common ground.
- MAX4466-style microphone amplifier output is DC biased near VCC/2. Determine ADC attenuation and output swing at speaking volume so the signal does not clip; digitally subtract the offset before converting to signed PCM.
- ESP32-C3 has an ADC continuous/DMA mode suitable for periodic sampling. Confirm exact behavior and core/driver compatibility at 16 kHz with active Wi-Fi.
- **One ADC module cannot run oneshot and continuous modes simultaneously.** A volume potentiometer on ADC1 therefore needs a compatible sampling strategy (for example scanning a second ADC channel in the same continuous-mode acquisition, or a different volume control). Do not assume a standalone `analogRead` can be mixed with continuous mic sampling.
- Proposed output: ESP32-C3 I2S BCLK + WS + data to MAX98357A. The MAX98357A accepts 16-kHz I2S and does not require MCLK.
- GPIO allocation (PTT, I2S, LED, volume) remains provisional until a pin plan is checked against XIAO boot-strap, USB/serial and available pins.

## Behavioral details to decide/test

- **Half-duplex enforcement:** the upstream relay forwards any approved sender. Proposed change: first active sender owns the room until PTT release or timeout; receiving box cannot talk over that transmission. Specific busy indications remain TBD.
- **Audio on arrival:** play after a short jitter buffer; no ringtone or accept button.
- **Release:** stop voice quickly and clear stale packets/buffer. Upstream roger beep exists; keep optional rather than assume desired.
- **Status:** ready/connected, transmitting, receiving/busy, offline/retrying.
- **Volume:** speaker output adjusts locally, without altering the remote mic signal.
- **Security isolation:** expose a dedicated intercom handler, keep admin available only privately or behind stronger authentication.

## Design priorities

Reliability > minimal wiring > cost (with **$0 additional recurring expense**) > adequate latency/voice quality > simple onboarding. Do not add an S3, codec, paid VPS, batteries, display, compression, advanced UI or multiple servers unless evidence shows a concrete need.
