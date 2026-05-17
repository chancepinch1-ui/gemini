"""Zero-dependency web dashboard so the agent is visible in a browser."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Tuple

from .scheduler import Scheduler
from .state import AgentState

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Agent Dashboard</title>
<style>
  body { font: 14px/1.5 system-ui, sans-serif; margin: 0; background: #0f1115; color: #e6e6e6; }
  header { padding: 16px 24px; background: #161922; border-bottom: 1px solid #262b36;
           display: flex; align-items: center; gap: 16px; }
  h1 { font-size: 16px; margin: 0; }
  .dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
  .on { background: #2ecc71; } .off { background: #e74c3c; }
  main { padding: 24px; display: grid; gap: 24px; grid-template-columns: 1fr 1fr; }
  .card { background: #161922; border: 1px solid #262b36; border-radius: 8px; padding: 16px; }
  .card h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .05em;
             color: #8a93a2; margin: 0 0 12px; }
  .stat { font-size: 22px; font-weight: 600; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  td, th { text-align: left; padding: 6px 8px; border-bottom: 1px solid #262b36; }
  pre { background: #0b0d12; padding: 12px; border-radius: 6px; max-height: 320px;
        overflow: auto; margin: 0; font-size: 12px; }
  button { background: #3b82f6; color: #fff; border: 0; padding: 8px 14px;
           border-radius: 6px; cursor: pointer; font-size: 13px; }
  button:hover { background: #2563eb; }
  .full { grid-column: 1 / -1; }
  .ok { color: #2ecc71; } .bad { color: #e74c3c; }
</style>
</head>
<body>
<header>
  <span id="dot" class="dot off"></span>
  <h1>Background Automation Agent</h1>
  <span id="uptime" style="color:#8a93a2"></span>
  <span style="flex:1"></span>
  <button onclick="trigger()">Run now</button>
</header>
<main>
  <div class="card"><h2>Status</h2><div id="status" class="stat">…</div></div>
  <div class="card"><h2>Total runs</h2><div id="runs" class="stat">…</div></div>
  <div class="card full"><h2>Recent runs</h2>
    <table><thead><tr><th>Task</th><th>When</th><th>Result</th><th>Detail</th><th>ms</th></tr></thead>
    <tbody id="history"></tbody></table>
  </div>
  <div class="card full"><h2>Logs</h2><pre id="logs"></pre></div>
</main>
<script>
function fmt(ts){ return ts ? new Date(ts*1000).toLocaleTimeString() : "-"; }
async function refresh(){
  const s = await (await fetch("/api/state")).json();
  document.getElementById("dot").className = "dot " + (s.running ? "on" : "off");
  document.getElementById("status").textContent = s.running ? "Running" : "Stopped";
  document.getElementById("runs").textContent = s.run_count;
  document.getElementById("uptime").textContent = "uptime " + s.uptime_seconds + "s · next "
    + fmt(s.next_run_at);
  document.getElementById("history").innerHTML = s.history.map(r =>
    `<tr><td>${r.task}</td><td>${fmt(r.started_at)}</td>`
    + `<td class="${r.ok?'ok':'bad'}">${r.ok?'ok':'fail'}</td>`
    + `<td>${r.detail}</td><td>${r.duration_ms}</td></tr>`).join("");
  document.getElementById("logs").textContent = s.logs.join("\\n");
}
async function trigger(){ await fetch("/api/trigger", {method:"POST"}); refresh(); }
refresh(); setInterval(refresh, 2000);
</script>
</body>
</html>
"""


def make_server(
    state: AgentState, scheduler: Scheduler, host: str, port: int
) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args) -> None:  # silence default stderr noise
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path in ("/", "/index.html"):
                self._send(200, _PAGE.encode(), "text/html; charset=utf-8")
            elif self.path == "/api/state":
                body = json.dumps(state.snapshot()).encode()
                self._send(200, body, "application/json")
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self) -> None:
            if self.path == "/api/trigger":
                scheduler.trigger_now()
                state.log("manual trigger requested via dashboard")
                self._send(200, b'{"ok":true}', "application/json")
            else:
                self._send(404, b"not found", "text/plain")

    httpd = ThreadingHTTPServer((host, port), Handler)
    return httpd


def address(httpd: ThreadingHTTPServer) -> Tuple[str, int]:
    return httpd.server_address[0], httpd.server_address[1]
