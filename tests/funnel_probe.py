#!/usr/bin/env python3
"""Isolated, authenticated WebSocket echo probe for Tailscale Funnel.

Research test only: no intercom/audio implementation, no background service.
Binds exclusively to 127.0.0.1:18765. Requires aiohttp.
"""
import asyncio
import hmac
import json
import os
import secrets
import time
from urllib.parse import quote, urlsplit

from aiohttp import WSMsgType, web

HOST = "127.0.0.1"
PORT = 18765
AUDIO_FRAME_BYTES = 640  # 320 samples x 16 bits; one 20 ms frame
MAX_FRAMES_PER_SEC = 100  # 2x the expected 50/s, for safety
TOKEN = secrets.token_urlsafe(32)  # new token each server restart

HTML = r"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Intercom Funnel WebSocket Probe</title>
<style>
 body {font:16px system-ui,sans-serif;max-width:680px;margin:2rem auto;padding:0 1rem;line-height:1.5}
 button,input {font:inherit;padding:.5rem;margin:.3rem 0}
 input {width:min(95%,32rem)}
 pre {white-space:pre-wrap;background:#f2f3f5;padding:1rem;border-radius:8px}
 .row {display:flex;gap:.5rem;flex-wrap:wrap}
</style>
<h2>Funnel / WebSocket intercom traffic test</h2>
<p>This is an isolated test, not the intercom server. Scan the QR code displayed
by the Pi to connect automatically on your phone, or paste the one-time token below.
The traffic test sends 640-byte frames every 20 ms and echoes them back.</p>
<label for="token">One-time test token</label><br>
<input id="token" type="password" autocomplete="off" placeholder="Token printed on Pi">
<div class="row">
 <button id="connect">Connect</button>
 <button id="start" disabled>Start traffic</button>
 <button id="stop" disabled>Stop traffic</button>
 <button id="disconnect" disabled>Disconnect</button>
</div>
<pre id="stats">Not connected.</pre>
<p>Keep this page open to test idle continuity; try traffic while the tab is
foregrounded, because browsers may throttle timers in background tabs.</p>
<script>
"use strict";
let socket = null, authorized = false, timer = null, seq = 0;
let sent = 0, received = 0, totalRTT = 0, missed = 0;
let openedAt = 0, disconnectedAt = 0, note = "Not connected.";
const times = new Map();
const $ = id => document.getElementById(id);
function controls() {
 $("connect").disabled = socket !== null;
 $("start").disabled = !authorized || timer !== null;
 $("stop").disabled = timer === null;
 $("disconnect").disabled = socket === null;
}
function stopTraffic() {
 if (timer !== null) { clearInterval(timer); timer = null; }
 controls();
}
function report() {
 const up = openedAt && socket && socket.readyState === WebSocket.OPEN
    ? ((performance.now()-openedAt)/1000).toFixed(0)+" s" : "—";
 $("stats").textContent = note + "\nConnected uptime: " + up +
   "\nSent frames: " + sent + " (640 bytes each)" +
   "\nEchoed frames: " + received +
   "\nSkipped sends (backpressure): " + missed +
   "\nMean echo round-trip: " + (received ? (totalRTT / received).toFixed(1)+" ms" : "—") +
   "\nSocket buffered bytes: " + (socket ? socket.bufferedAmount : 0);
}
function sendFrame() {
 if (!authorized || !socket || socket.readyState !== WebSocket.OPEN) {
   stopTraffic(); return;
 }
 if (socket.bufferedAmount > 32768) { missed++; return; }
 const frame = new ArrayBuffer(640);
 const id = seq >>> 0;
 new DataView(frame).setUint32(0, id, true);
 times.set(id, performance.now());
 if (times.size > 2000) times.delete(times.keys().next().value);
 seq = (seq + 1) >>> 0;
 socket.send(frame);
 sent++;
}
$("connect").onclick = () => {
 const token = $("token").value.trim();
 if (!token) { note = "Enter the token from the Pi terminal."; report(); return; }
 authorized = false; sent = 0; received = 0; totalRTT = 0; missed = 0;
 times.clear(); seq = 0; openedAt = 0;
 const url = (location.protocol === "https:" ? "wss://" : "ws://") + location.host + "/ws";
 socket = new WebSocket(url);
 socket.binaryType = "arraybuffer";
 note = "Connecting...";
 controls(); report();
 socket.onopen = () => { openedAt = performance.now(); socket.send(JSON.stringify({type:"auth", token: token})); };
 socket.onmessage = event => {
   if (typeof event.data === "string") {
     try {
       const msg = JSON.parse(event.data);
       if (msg.type === "auth_ok") { authorized = true; note = "Authenticated; WebSocket open."; $("token").value = ""; }
       else if (msg.type === "error") note = "Server error: " + msg.message;
     } catch (_) {}
   } else if (event.data instanceof ArrayBuffer && event.data.byteLength === 640) {
     const id = new DataView(event.data).getUint32(0, true);
     const sentAt = times.get(id);
     if (sentAt !== undefined) {
       totalRTT += performance.now() - sentAt;
       received++;
       times.delete(id);
     }
   }
   controls(); report();
 };
 socket.onerror = () => { note = "WebSocket error (check TLS/Funnel and server log)."; report(); };
 socket.onclose = e => {
   stopTraffic(); authorized = false; disconnectedAt = performance.now();
   socket = null; note = "Disconnected; close code " + e.code;
   controls(); report();
 };
};
$("start").onclick = () => {
 if (!authorized) return;
 timer = setInterval(sendFrame, 20);
 note = "Sending 50 frames/sec; keep this tab visible.";
 controls();
};
$("stop").onclick = () => {
 stopTraffic(); note = "Traffic stopped; keeping connection open for idle test."; report();
};
$("disconnect").onclick = () => { stopTraffic(); if (socket) socket.close(1000, "user"); };
setInterval(report, 1000);
controls(); report();
// QR pairing URL: the fragment is never transmitted in an HTTP request.
// Drop it from the address bar before authenticating via WSS.
const scannedToken = new URLSearchParams(location.hash.substring(1)).get("token");
if (scannedToken) {
 $("token").value = scannedToken;
 history.replaceState(null, "", location.pathname + location.search);
 $("connect").click();
}
</script>
</html>
"""

async def index(_request):
    return web.Response(text=HTML, content_type="text/html",
                        headers={"Cache-Control": "no-store"})

async def websocket_probe(request):
    ws = web.WebSocketResponse(heartbeat=20.0, max_msg_size=2048, compress=False)
    await ws.prepare(request)
    authorized = False
    frames = 0
    started = time.monotonic()
    rate_start = started
    rate_count = 0
    try:
        first = await asyncio.wait_for(ws.receive(), timeout=10.0)
        if first.type != WSMsgType.TEXT:
            await ws.close(code=1008, message=b"authentication required")
            return ws
        try:
            hello = json.loads(first.data)
        except json.JSONDecodeError:
            hello = {}
        if hello.get("type") != "auth" or not hmac.compare_digest(
            str(hello.get("token", "")), TOKEN
        ):
            await ws.close(code=1008, message=b"invalid token")
            return ws
        authorized = True
        await ws.send_json({"type": "auth_ok"})
        print("Authenticated WebSocket connected.", flush=True)
        async for msg in ws:
            if msg.type == WSMsgType.BINARY:
                now = time.monotonic()
                if now - rate_start >= 1.0:
                    rate_start, rate_count = now, 0
                rate_count += 1
                if len(msg.data) != AUDIO_FRAME_BYTES or rate_count > MAX_FRAMES_PER_SEC:
                    await ws.close(code=1008, message=b"invalid frame or rate")
                    break
                frames += 1
                await ws.send_bytes(msg.data)
            elif msg.type == WSMsgType.TEXT:
                if msg.data == "ping":
                    await ws.send_str("pong")
                else:
                    await ws.close(code=1008, message=b"unexpected text")
                    break
            elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                break
    except asyncio.TimeoutError:
        await ws.close(code=1008, message=b"authentication timeout")
    finally:
        if authorized:
            print(f"WebSocket disconnected: {frames} echoed frames in "
                  f"{time.monotonic()-started:.1f}s (code {ws.close_code}).", flush=True)
    return ws

def print_phone_qr():
    """Show a locally generated QR for the public Funnel URL and ephemeral secret."""
    url = os.environ.get("FUNNEL_PUBLIC_URL", "").strip()
    if not url:
        print("Phone pairing QR: set FUNNEL_PUBLIC_URL to your HTTPS Funnel URL.")
        return
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.netloc or parts.username or parts.password or parts.query or parts.fragment:
        print("Phone QR unavailable: FUNNEL_PUBLIC_URL must be an HTTPS URL without query or fragment.")
        return
    try:
        import qrcode
    except ImportError:
        print("Phone QR unavailable: install qrcode in the test virtual environment.")
        return
    pair_url = url.rstrip("/") + "/#token=" + quote(TOKEN, safe="")
    qr = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(pair_url)
    qr.make(fit=True)
    print("\nScan the QR below with your phone camera (cellular data; Wi-Fi and Tailscale off).")
    print("Do not post the QR as an image: it contains the temporary test credential.")
    qr.print_ascii(invert=True)
    print("The phone will connect automatically. Tap Start traffic on the phone.\n", flush=True)


def main():
    app = web.Application(client_max_size=2048)
    app.router.add_get("/", index)
    app.router.add_get("/ws", websocket_probe)
    print("Isolated Funnel/WebSocket TEST only (not an intercom service).")
    print(f"Local URL: http://{HOST}:{PORT}/")
    print(f"One-time test token: {TOKEN}")
    print("Token changes on every server restart; do not put it in GitHub.")
    print_phone_qr()
    print("Press Ctrl+C to stop this test service.", flush=True)
    web.run_app(app, host=HOST, port=PORT, print=None, access_log=None)

if __name__ == "__main__":
    main()
