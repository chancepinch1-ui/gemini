"""의존성 없는 웹 서버: 직원 입력 화면 + 관리자 통합조회 대시보드.

탭 하나로 직원이 통화기록을 입력하고, 다른 탭에서 관리자가 모든 직원의 기록을
검색·필터·통계와 함께 조회/삭제할 수 있습니다.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Tuple
from urllib.parse import parse_qs, urlparse

from .db import Database
from .models import CATEGORIES

_PAGE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>통화기록 통합관리</title>
<style>
  * { box-sizing: border-box; }
  body { font: 14px/1.6 system-ui, "Apple SD Gothic Neo", sans-serif; margin: 0;
         background: #0f1115; color: #e6e6e6; }
  header { padding: 16px 24px; background: #161922; border-bottom: 1px solid #262b36;
           display: flex; align-items: center; gap: 16px; }
  h1 { font-size: 17px; margin: 0; }
  .tabs { display: flex; gap: 8px; }
  .tab { background: #20242e; color: #c7cdd8; border: 1px solid #2b3140; padding: 7px 16px;
         border-radius: 6px; cursor: pointer; font-size: 13px; }
  .tab.active { background: #3b82f6; color: #fff; border-color: #3b82f6; }
  main { padding: 24px; max-width: 1100px; margin: 0 auto; }
  .view { display: none; }
  .view.active { display: block; }
  .card { background: #161922; border: 1px solid #262b36; border-radius: 8px;
          padding: 20px; margin-bottom: 20px; }
  .card h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .05em;
             color: #8a93a2; margin: 0 0 14px; }
  label { display: block; font-size: 12px; color: #8a93a2; margin-bottom: 4px; }
  input, select, textarea { width: 100%; background: #0b0d12; color: #e6e6e6;
        border: 1px solid #2b3140; border-radius: 6px; padding: 9px 10px; font: inherit; }
  textarea { resize: vertical; min-height: 80px; }
  .row { display: grid; gap: 14px; grid-template-columns: 1fr 1fr; margin-bottom: 14px; }
  .row3 { grid-template-columns: 1fr 1fr 1fr; }
  button { background: #3b82f6; color: #fff; border: 0; padding: 10px 18px;
           border-radius: 6px; cursor: pointer; font-size: 14px; }
  button:hover { background: #2563eb; }
  button.ghost { background: #20242e; border: 1px solid #2b3140; }
  button.danger { background: #20242e; color: #e87979; padding: 4px 10px; font-size: 12px; }
  button.danger:hover { background: #3a2226; }
  table { width: 100%; border-collapse: collapse; font-size: 13px; }
  td, th { text-align: left; padding: 8px 10px; border-bottom: 1px solid #262b36;
           vertical-align: top; }
  th { color: #8a93a2; font-size: 12px; font-weight: 600; }
  .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px,1fr));
           gap: 14px; }
  .stat { background: #0b0d12; border: 1px solid #2b3140; border-radius: 8px; padding: 14px; }
  .stat .n { font-size: 26px; font-weight: 700; }
  .stat .l { font-size: 12px; color: #8a93a2; }
  .pill { display: inline-block; padding: 1px 8px; border-radius: 999px; font-size: 11px;
          background: #20242e; border: 1px solid #2b3140; color: #c7cdd8; }
  .filters { display: flex; gap: 10px; flex-wrap: wrap; align-items: end; margin-bottom: 16px; }
  .filters > div { flex: 1; min-width: 150px; }
  .muted { color: #8a93a2; }
  .ok-msg { color: #2ecc71; margin-left: 12px; font-size: 13px; }
  .chips { display: flex; flex-wrap: wrap; gap: 8px; }
  .chip { background: #0b0d12; border: 1px solid #2b3140; border-radius: 6px;
          padding: 6px 12px; font-size: 12px; }
  .chip b { color: #fff; margin-left: 6px; }
  @media (max-width: 720px){ .row, .row3 { grid-template-columns: 1fr; } }
</style>
</head>
<body>
<header>
  <h1>📞 통화기록 통합관리</h1>
  <div class="tabs">
    <button class="tab active" data-view="entry" onclick="show('entry')">통화 입력</button>
    <button class="tab" data-view="admin" onclick="show('admin')">관리자 조회</button>
  </div>
</header>
<main>

  <!-- 직원 입력 화면 -->
  <section id="entry" class="view active">
    <div class="card">
      <h2>통화기록 입력</h2>
      <form id="entry-form" onsubmit="return submitLog(event)">
        <div class="row3">
          <div><label>직원명 *</label><input name="employee" required placeholder="홍길동"></div>
          <div><label>고객명 *</label><input name="customer" required placeholder="김고객"></div>
          <div><label>전화번호 *</label><input name="phone" required placeholder="010-1234-5678"></div>
        </div>
        <div class="row">
          <div><label>분류</label><select name="category" id="cat-select"></select></div>
          <div><label>통화 일시</label><input type="datetime-local" name="called_at"></div>
        </div>
        <div style="margin-bottom:14px">
          <label>통화내용 *</label>
          <textarea name="content" required placeholder="고객과 나눈 통화내용을 입력하세요"></textarea>
        </div>
        <button type="submit">기록 저장</button>
        <span id="entry-msg" class="ok-msg"></span>
      </form>
    </div>
  </section>

  <!-- 관리자 조회 화면 -->
  <section id="admin" class="view">
    <div class="card">
      <h2>통계 요약</h2>
      <div class="stats" id="stat-cards"></div>
      <div style="margin-top:16px"><div class="muted" style="margin-bottom:6px">직원별 통화 건수</div>
        <div class="chips" id="emp-chips"></div></div>
    </div>
    <div class="card">
      <h2>통화기록 조회</h2>
      <div class="filters">
        <div><label>직원</label><select id="f-employee"><option value="">전체</option></select></div>
        <div><label>분류</label><select id="f-category"><option value="">전체</option></select></div>
        <div><label>검색(고객명·전화·내용)</label><input id="f-query" placeholder="검색어"
             onkeydown="if(event.key==='Enter')loadLogs()"></div>
        <div style="flex:0">
          <button onclick="loadLogs()">조회</button>
          <button class="ghost" onclick="resetFilters()">초기화</button>
        </div>
      </div>
      <table>
        <thead><tr>
          <th>통화일시</th><th>직원</th><th>고객명</th><th>전화번호</th>
          <th>분류</th><th>통화내용</th><th></th>
        </tr></thead>
        <tbody id="log-rows"></tbody>
      </table>
      <div id="empty" class="muted" style="padding:16px 0; display:none">기록이 없습니다.</div>
    </div>
  </section>

</main>
<script>
let CATEGORIES = [];

function esc(s){ return (s==null?'':String(s)).replace(/[&<>"]/g,
  c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
function fmt(iso){ if(!iso) return '-'; const d=new Date(iso);
  return isNaN(d)? iso : d.toLocaleString('ko-KR',{dateStyle:'short',timeStyle:'short'}); }

function show(v){
  document.querySelectorAll('.view').forEach(e=>e.classList.toggle('active', e.id===v));
  document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active', b.dataset.view===v));
  if(v==='admin') refreshAdmin();
}

async function init(){
  const meta = await (await fetch('/api/meta')).json();
  CATEGORIES = meta.categories;
  document.getElementById('cat-select').innerHTML =
    CATEGORIES.map(c=>`<option>${esc(c)}</option>`).join('');
  document.getElementById('f-category').innerHTML =
    '<option value="">전체</option>' + CATEGORIES.map(c=>`<option>${esc(c)}</option>`).join('');
}

async function submitLog(e){
  e.preventDefault();
  const f = e.target, data = Object.fromEntries(new FormData(f));
  const r = await fetch('/api/logs', {method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify(data)});
  const msg = document.getElementById('entry-msg');
  if(r.ok){ msg.textContent='✓ 저장되었습니다'; f.reset();
            setTimeout(()=>msg.textContent='', 2500); }
  else { const j = await r.json().catch(()=>({error:'오류'}));
         msg.textContent='✗ ' + (j.error||'저장 실패'); msg.style.color='#e87979'; }
  return false;
}

async function refreshAdmin(){
  const meta = await (await fetch('/api/meta')).json();
  const s = meta.stats;
  document.getElementById('stat-cards').innerHTML =
    `<div class="stat"><div class="n">${s.total}</div><div class="l">전체 통화건수</div></div>`
   +`<div class="stat"><div class="n">${s.today}</div><div class="l">오늘 통화건수</div></div>`
   +`<div class="stat"><div class="n">${meta.employees.length}</div><div class="l">등록 직원수</div></div>`;
  document.getElementById('emp-chips').innerHTML = s.by_employee.length
    ? s.by_employee.map(e=>`<span class="chip">${esc(e.employee)}<b>${e.count}</b></span>`).join('')
    : '<span class="muted">데이터 없음</span>';
  const sel = document.getElementById('f-employee'), cur = sel.value;
  sel.innerHTML = '<option value="">전체</option>' +
    meta.employees.map(e=>`<option>${esc(e)}</option>`).join('');
  sel.value = cur;
  loadLogs();
}

async function loadLogs(){
  const p = new URLSearchParams();
  const emp = document.getElementById('f-employee').value;
  const cat = document.getElementById('f-category').value;
  const q = document.getElementById('f-query').value.trim();
  if(emp) p.set('employee', emp);
  if(cat) p.set('category', cat);
  if(q) p.set('q', q);
  const rows = await (await fetch('/api/logs?'+p)).json();
  document.getElementById('empty').style.display = rows.length ? 'none' : 'block';
  document.getElementById('log-rows').innerHTML = rows.map(r =>
    `<tr><td>${fmt(r.called_at)}</td><td>${esc(r.employee)}</td>`
   +`<td>${esc(r.customer)}</td><td>${esc(r.phone)}</td>`
   +`<td><span class="pill">${esc(r.category)}</span></td>`
   +`<td style="white-space:pre-wrap;max-width:340px">${esc(r.content)}</td>`
   +`<td><button class="danger" onclick="delLog(${r.id})">삭제</button></td></tr>`).join('');
}

async function delLog(id){
  if(!confirm('이 통화기록을 삭제하시겠습니까?')) return;
  await fetch('/api/logs/delete', {method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify({id})});
  refreshAdmin();
}

function resetFilters(){
  document.getElementById('f-employee').value='';
  document.getElementById('f-category').value='';
  document.getElementById('f-query').value='';
  loadLogs();
}

init();
</script>
</body>
</html>
"""


def make_server(db: Database, host: str, port: int) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args) -> None:
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

        def _read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", 0))
            if not length:
                return {}
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8"))
                return data if isinstance(data, dict) else {}
            except (ValueError, UnicodeDecodeError):
                return {}

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            if path in ("/", "/index.html"):
                self._send(200, _PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/api/meta":
                self._json(200, {
                    "categories": list(CATEGORIES),
                    "employees": db.employees(),
                    "stats": db.stats(),
                })
            elif path == "/api/logs":
                qs = parse_qs(parsed.query)
                logs = db.list(
                    employee=(qs.get("employee", [None])[0] or None),
                    category=(qs.get("category", [None])[0] or None),
                    query=(qs.get("q", [None])[0] or None),
                )
                self._json(200, [lg.to_dict() for lg in logs])
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            if path == "/api/logs":
                data = self._read_json()
                required = ("employee", "customer", "phone", "content")
                missing = [k for k in required if not str(data.get(k, "")).strip()]
                if missing:
                    self._json(400, {"error": f"필수 항목 누락: {', '.join(missing)}"})
                    return
                category = str(data.get("category") or "기타").strip()
                if category not in CATEGORIES:
                    category = "기타"
                called_at = str(data.get("called_at") or "").strip() or None
                new_id = db.add(
                    employee=str(data["employee"]).strip(),
                    customer=str(data["customer"]).strip(),
                    phone=str(data["phone"]).strip(),
                    content=str(data["content"]).strip(),
                    category=category,
                    called_at=called_at,
                )
                self._json(201, {"id": new_id})
            elif path == "/api/logs/delete":
                data = self._read_json()
                try:
                    log_id = int(data.get("id"))
                except (TypeError, ValueError):
                    self._json(400, {"error": "유효한 id가 필요합니다"})
                    return
                ok = db.delete(log_id)
                self._json(200 if ok else 404, {"ok": ok})
            else:
                self._send(404, b"not found", "text/plain")

    return ThreadingHTTPServer((host, port), Handler)


def address(httpd: ThreadingHTTPServer) -> Tuple[str, int]:
    return httpd.server_address[0], httpd.server_address[1]
