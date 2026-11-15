# Checkpoint 1: Tailscale Funnel / WebSocket test

**Status: PROBE CODE COMMITTED, NOT RUN ON THE PI.**
This is **not** an intercom implementation or firmware build. Authorization to perform this isolated test was given in chat on 2026-11-14. No Pi access is available from the assistant's connection; steps below must be run on the Pi by the owner.

## What this exercises

- A small Python/aiohttp server **bound only to 127.0.0.1:18765**.
- An isolated Tailscale Funnel listener on **public HTTPS port 8443**.
- A browser client via **WSS**: authenticates with an ephemeral random token, then sends a 640-byte binary frame every 20 ms and receives the same frame echoed.
- The probe reports frame counts, round-trip time and browser send backpressure.
- When traffic is stopped, the WebSocket remains open; aiohttp issues WebSocket heartbeats while idle.

**Does not test:** real microphones, ESP32 hardware, two simultaneous nodes, actual audio playback, final relay implementation, or guaranteed 24/7 uptime.

## Phase A: read-only checks on Raspberry Pi

Run in a Pi terminal:

\`\`\`bash
tailscale version
tailscale funnel status
sudo ss -ltnp | grep -E ':(443|8443|10000|18765)\b' || true
python3 --version
\`\`\`

- Ensure **8443** is not already serving another Funnel/Serve configuration. Do not overwrite an existing listener.
- If an existing port conflict or service is found, stop here and review before changing anything.
- House Audio and its services are not to be changed.

## Phase B: install standalone test dependencies in a private virtual environment

Only if Phase A is clear:

\`\`\`bash
mkdir -p ~/esp32-internet-intercom/tests
curl -fsSL https://raw.githubusercontent.com/oolah10293/esp32-internet-intercom/main/tests/funnel_probe.py -o ~/esp32-internet-intercom/tests/funnel_probe.py
python3 -m venv ~/esp32-internet-intercom/.venv
~/esp32-internet-intercom/.venv/bin/python -m pip install aiohttp
\`\`\`

If \`python3 -m venv\` reports that the ensurepip module is unavailable, install the Debian \`python3-venv\` package separately (after confirming the error); do not modify the system Python packages or use \`pip --break-system-packages\`.

## Phase C: run only the local listener

**Pi terminal 1**:

\`\`\`bash
~/esp32-internet-intercom/.venv/bin/python ~/esp32-internet-intercom/tests/funnel_probe.py
\`\`\`

It prints a **one-time secret test token** in the terminal. Do not put this token in GitHub or paste it into public chats. The token is regenerated on restart.

Local check, in Pi terminal 2:

\`\`\`bash
curl -I http://127.0.0.1:18765/
\`\`\`

Expected: HTTP response from the probe. If the port is busy, **do not** kill the other process; investigate.

## Phase D: expose the isolated test service through Funnel

**Pi terminal 2** (foreground, so it can be stopped with Ctrl+C):

\`\`\`bash
sudo tailscale funnel --https=8443 http://127.0.0.1:18765
\`\`\`

If Tailscale prompts to enable Funnel/HTTPS in a web console, complete that required first-run approval. Tailscale documents public DNS propagation delays up to around ten minutes. Use the exact HTTPS URL printed by the command, including \`:8443\` if present; do not guess the hostname.

Check in an external browser **from a different ISP** (for example, phone cellular with Wi-Fi off and no active Tailscale connection):

1. Open the public HTTPS URL and enter the temporary token from the Pi terminal.
2. Click Connect and observe successful WSS authentication.
3. Click Start traffic for a short foreground-tab run; the intended send rate is **50 × 640 bytes/s = 256 kbit/s** raw payload.
4. Observe echoed frames, RTT, skipped sends, and any disconnections.
5. Click Stop traffic and leave the authenticated browser tab open for an idle test.
6. After approval for interruption tests, try reconnect after stopping/restarting the probe and/or changing the external network.

The browser may throttle JavaScript timing in background tabs; use a foreground tab for sustained-rate measurements. No claim of 24-hour reliability is valid from a short browser test.

## Cleanup

Stop the Funnel foreground command with **Ctrl+C** in terminal 2. Check:

\`\`\`bash
tailscale funnel status
\`\`\`

If the test listener on 8443 remains published, remove only that endpoint (not all Funnel configuration):

\`\`\`bash
sudo tailscale funnel --https=8443 off
\`\`\`

In terminal 1, stop the local probe with **Ctrl+C**. Do **not** run \`tailscale funnel reset\`; that would erase unrelated Funnel configuration.

## Record measurements

Append results to \`docs/validation-plan.md\` after actual execution. Record date, Pi Tailscale version, separate-ISP test setup, URL port (not the private token), session duration, echoed/sent counts, RTT, disconnections and recovery results.

## Source references

- [Official Tailscale Funnel command](https://tailscale.com/docs/reference/tailscale-cli/funnel)
- [Official Funnel requirements/limits](https://tailscale.com/docs/features/tailscale-funnel)
- [aiohttp WebSocket documentation](https://docs.aiohttp.org/en/stable/web_reference.html)

*Do not expose the upstream project's plain HTTP admin interface or unauthenticated UDP service.*
