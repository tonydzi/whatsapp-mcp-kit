#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wa_qr_live.py -- link WhatsApp to this machine through a LIVE local QR page.

WHY THIS EXISTS. Linking a WhatsApp companion device is the one step that cannot be
automated: the code must be scanned by the phone that owns the account. Everything
*around* that scan can and should be one command -- and the code itself has to be a
picture in a browser that refreshes itself.

WHY A PAGE AND NOT THE TERMINAL (field-measured 2026-06-15):
  * the ASCII QR the server prints is unscannable mosaic in most Windows terminal fonts;
  * a QR lives ~18-20 seconds. Scanning an EXPIRED one makes the phone say
    "check your connection and try again later" -- that is NOT a network problem, it is
    a stale code. The page redraws every ~2s, so you always scan a fresh one;
  * a non-technical owner needs a window to look at, not a scrollback to squint at.

WHAT IT DOES:
  1. checks the environment (server present, QR_RAW patch in dist/whatsapp.js, qrcode module);
  2. starts ONE server client and never closes its stdin -- an MCP stdio server shuts
     itself down the moment stdin closes ("stdin closed -- shutting down");
  3. scrapes the raw QR string out of the server log, renders a PNG, writes status.json;
  4. serves a local page: QR + status + generation counter (markup generated here, one source);
  5. detects the moment auth_info/creds.json appears -> page says "done", bridge is killed,
     process exits 0.

EXIT CODES: 0 = linked · 1 = timeout / QR never arrived · 2 = already linked, nothing to do ·
  3 = environment not ready (no server / no patch / no qrcode / no free port) · 4 = crash.

TROUBLESHOOTING:
  * "no QR in 90s" -> look at server.log: no QR_RAW_BEGIN there means the vendor patch is
    gone (any `npm update` removes it) -> run with --heal-patch;
  * two clients on one link = AUTH_KEY_DUPLICATED and a forced re-scan. Preflight counts
    live clients and refuses to start without --force;
  * on Windows terminate()/kill() does not reliably kill a node child -> we use taskkill /F /T.

Requires: python3 with `qrcode` + `pillow` (pip install qrcode pillow), node in PATH,
and the WhatsApp MCP server installed (npm i -g @sjawhar/whatsapp-mcp).
Part of https://github.com/tonydzi/whatsapp-mcp-kit -- MIT.
"""
import argparse
import datetime as dt
import functools
import http.server
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import threading
import time

HOME = os.path.expanduser("~")
PKG = os.path.join("@sjawhar", "whatsapp-mcp")


def _find_vendor_dir():
    """Where the WhatsApp MCP server lives. Env override wins, then `npm root -g`,
    then the usual per-OS global install locations. We never hardcode one machine."""
    env = os.environ.get("WHATSAPP_MCP_DIR")
    if env:
        return env
    candidates = []
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if npm:
        try:
            root = subprocess.run([npm, "root", "-g"], capture_output=True, text=True,
                                  timeout=60).stdout.strip()
            if root:
                candidates.append(os.path.join(root, PKG))
        except Exception:
            pass
    candidates += [
        os.path.join(HOME, "AppData", "Roaming", "npm", "node_modules", PKG),   # Windows
        os.path.join("/usr", "local", "lib", "node_modules", PKG),              # macOS/Linux
        os.path.join(HOME, ".npm-global", "lib", "node_modules", PKG),
        os.path.join(HOME, "node_modules", PKG),
    ]
    for c in candidates:
        if os.path.exists(os.path.join(c, "dist", "index.js")):
            return c
    return candidates[0] if candidates else ""


def _auth_dir():
    """Must match the server's own paths.js:
    (XDG_DATA_HOME or ~/.local/share)/whatsapp-mcp/auth_info"""
    env = os.environ.get("WHATSAPP_MCP_AUTH_DIR")
    if env:
        return env
    data_home = os.environ.get("XDG_DATA_HOME") or os.path.join(HOME, ".local", "share")
    return os.path.join(data_home, "whatsapp-mcp", "auth_info")


VENDOR_DIR = _find_vendor_dir()
VENDOR_ENTRY = os.path.join(VENDOR_DIR, "dist", "index.js")
VENDOR_PATCH_FILE = os.path.join(VENDOR_DIR, "dist", "whatsapp.js")
AUTH_DIR = _auth_dir()
CREDS = os.path.join(AUTH_DIR, "creds.json")
WORK = os.environ.get("WA_QR_WORK_DIR") or os.path.join(HOME, ".whatsapp-mcp-kit")
LOG = os.path.join(WORK, "server.log")
QR_PNG = os.path.join(WORK, "qr.png")
QR_TXT = os.path.join(WORK, "qr_string.txt")
STATUS = os.path.join(WORK, "status.json")
PAGE = os.path.join(WORK, "index.html")
DEFAULT_PORT = 8799
STALE_SEC = 180        # how long we wait before SAYING there is a pause (never killing!)
QR_RE = re.compile(r"QR_RAW_BEGIN(.*?)QR_RAW_END", re.S)


# ---------------------------------------------------------------- state
def paired():
    """Linked = a NON-EMPTY creds.json exists. A responding profile or a chat list is
    NOT proof: the server answers those from its local cache and they lied to us for
    26 days straight while the link was dead."""
    try:
        return os.path.getsize(CREDS) > 0
    except OSError:
        return False


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def vendor_ok():
    problems = []
    if not os.path.exists(VENDOR_ENTRY):
        problems.append("server not found: %s (npm i -g @sjawhar/whatsapp-mcp, or set "
                        "WHATSAPP_MCP_DIR)" % VENDOR_ENTRY)
    elif "QR_RAW_BEGIN" not in _read(VENDOR_PATCH_FILE):
        problems.append("QR_RAW patch missing from dist/whatsapp.js (any npm update wipes "
                        "it) -> run with --heal-patch")
    try:
        import qrcode  # noqa: F401
    except Exception:
        problems.append("no qrcode module for this python: pip install qrcode pillow")
    if not shutil.which("node"):
        problems.append("node is not in PATH")
    return problems


def live_nodes():
    """[(pid, cmdline)] of live WhatsApp server processes. A second client on the same
    link means AUTH_KEY_DUPLICATED and a forced re-scan."""
    if os.name != "nt":
        try:
            out = subprocess.run(["pgrep", "-af", "whatsapp-mcp"], capture_output=True,
                                 text=True, timeout=30).stdout.strip()
        except Exception:
            return []
        rows = []
        for line in out.splitlines():
            parts = line.split(None, 1)
            if parts and parts[0].isdigit():
                rows.append((int(parts[0]), parts[1] if len(parts) > 1 else ""))
        return rows
    ps = ("Get-CimInstance Win32_Process -Filter \"Name='node.exe'\" | "
          "Where-Object { $_.CommandLine -like '*whatsapp-mcp*' } | "
          "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress")
    try:
        out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps],
                             capture_output=True, text=True, timeout=45).stdout.strip()
        if not out:
            return []
        j = json.loads(out)
        j = [j] if isinstance(j, dict) else j
        return [(int(x["ProcessId"]), x.get("CommandLine") or "") for x in j]
    except Exception:
        return []


def hard_kill(pid):
    """On Windows terminate()/kill() does not reliably take the node child down ->
    orphans pile up and the NEXT run becomes a second client on the link.

    Never raises: this runs in a `finally`, and a failed cleanup must not overwrite the
    real return code with a crash (an exit code that lies is worse than a stray process).
    """
    cmd = (["taskkill", "/F", "/T", "/PID", str(pid)] if os.name == "nt"
           else ["kill", "-9", str(pid)])
    try:
        subprocess.run(cmd, capture_output=True, timeout=30)
    except Exception as e:
        print("could not kill pid %s (%s: %s) -- check for a stray client before the next run"
              % (pid, type(e).__name__, e), file=sys.stderr)


def heal_patch():
    """Restore the raw-QR print in the server. Without it the code is only ever emitted
    as terminal ASCII art, which most phones cannot read off a Windows console.

    Returns (ok, message). The caller turns `ok` into the exit code -- a repair tool that
    exits 0 after repairing nothing is exactly the false silence this kit is about.
    """
    src = _read(VENDOR_PATCH_FILE)
    if not src:
        return False, "file not found: " + VENDOR_PATCH_FILE
    if "QR_RAW_BEGIN" in src:
        return True, "patch already in place"
    anchor = "qrcode.generate("
    if anchor not in src:
        return False, ("insertion point (%s) not found -- the server changed; patch by hand: "
                       'console.error("QR_RAW_BEGIN"+qr+"QR_RAW_END")' % anchor)
    shutil.copyfile(VENDOR_PATCH_FILE, VENDOR_PATCH_FILE + ".bak-prepatch")
    src = src.replace(anchor, 'console.error("QR_RAW_BEGIN"+qr+"QR_RAW_END");' + anchor, 1)
    with open(VENDOR_PATCH_FILE, "w", encoding="utf-8") as f:
        f.write(src)
    if "QR_RAW_BEGIN" not in _read(VENDOR_PATCH_FILE):     # prove it, don't assume it
        return False, "write went through but the patch is not in the file -- check permissions"
    return True, "patch restored (backup next to it: .bak-prepatch)"


# ---------------------------------------------------------------- page
def write_page(port):
    """The page is generated HERE (single source of markup) into the work folder."""
    html = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>WhatsApp - link a device</title>
<style>
 body{margin:0;background:#0b141a;color:#e9edef;font-family:Segoe UI,Arial,sans-serif;
      display:flex;flex-direction:column;align-items:center;justify-content:center;
      min-height:100vh;text-align:center;padding:18px}
 h1{font-size:23px;margin:0 0 6px} p{margin:3px 0;color:#8696a0;font-size:15px}
 b{color:#e9edef}
 .card{background:#fff;padding:16px;border-radius:16px;margin:16px 0 10px;
       box-shadow:0 8px 30px rgba(0,0,0,.45)}
 img{width:360px;height:360px;display:block}
 .st{font-size:16px;font-weight:600;margin-top:6px}
 .ok{color:#00a884} .warn{color:#e8a33d} .dim{color:#8696a0;font-size:13px}
 .done .card{opacity:.25}
</style></head>
<body>
 <h1>Link WhatsApp</h1>
 <p>phone -> WhatsApp -> <b>Settings</b> -> <b>Linked devices</b> -> <b>Link a device</b></p>
 <p>point the camera at the code below. it refreshes itself -- scan the one you see now</p>
 <div class="card"><img id="qr" src="qr.png" alt="QR"></div>
 <div class="st" id="st">starting the bridge...</div>
 <div class="dim" id="sub"></div>
<script>
 async function tick(){
  try{
   const r = await fetch('status.json?t='+Date.now(), {cache:'no-store'});
   const s = await r.json();
   const st = document.getElementById('st'), sub = document.getElementById('sub');
   if(s.state === 'LINKED'){
     document.body.classList.add('done');
     st.innerHTML = '<span class="ok">done - device linked. you can close this window</span>';
     sub.textContent = 'now verify from your MCP client: call get_my_profile';
     return;                                   // nothing left to poll
   }
   if(s.state === 'QR'){
     document.getElementById('qr').src = 'qr.png?t=' + Date.now();
     st.textContent = 'waiting for the scan...';
     sub.textContent = 'code #' + s.generation + ' at ' + s.qr_at + ' - lives ~20s, this page always shows the freshest';
   } else if(s.state === 'TIMEOUT'){
     st.innerHTML = '<span class="warn">timed out, the code is no longer refreshing</span>';
     sub.textContent = 'restart: python wa_qr_live.py';
   } else {
     st.textContent = s.note || 'starting the bridge...';
   }
  }catch(e){}
  setTimeout(tick, 2000);
 }
 tick();
</script></body></html>
"""
    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(html)


def set_status(state, **extra):
    row = {"state": state, "at": dt.datetime.now().strftime("%H:%M:%S")}
    row.update(extra)
    tmp = STATUS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:      # atomic: the page never sees half a file
        json.dump(row, f, ensure_ascii=False)
    os.replace(tmp, STATUS)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):                        # don't spam the caller's stdout
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, max-age=0")
        super().end_headers()


def serve(port):
    """Bring the page up. Returns (httpd, real_port) or (None, None).

    We do NOT pre-check the port: between the check and the bind another process can
    take it (TOCTOU). We just try to sit down, and move one seat over if it is taken.
    There is deliberately no file:// fallback -- from the file scheme the browser cannot
    read status.json, so the page would forever claim "starting the bridge" while the
    code was in fact rotating. A page that lies is worse than a page that fails.
    """
    handler = functools.partial(Quiet, directory=WORK)
    for cand in range(port, port + 6):
        try:
            httpd = socketserver.ThreadingTCPServer(("127.0.0.1", cand), handler)
        except OSError:
            continue
        httpd.daemon_threads = True
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        return httpd, cand
    return None, None


# ---------------------------------------------------------------- main
def render(code):
    import qrcode
    qrcode.make(code, box_size=10, border=3).save(QR_PNG)


def open_in_browser(url):
    try:
        if os.name == "nt":
            os.startfile(url)                                  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", url])
        else:
            subprocess.Popen(["xdg-open", url])
    except Exception:
        pass


def pair(port, timeout_sec, force, open_page):
    os.makedirs(WORK, exist_ok=True)
    if paired():
        print("ALREADY LINKED -- no scan needed (creds.json is present at %s)." % CREDS)
        print("If the channel is still silent, that is not the link: check your MCP client.")
        return 2
    problems = vendor_ok()
    if problems:
        print("ENVIRONMENT NOT READY:")
        for p in problems:
            print("  * " + p)
        return 3
    others = live_nodes()
    if others and not force:
        print("%d WhatsApp client(s) ALREADY RUNNING -- a second one on the same link"
              % len(others))
        print("gives AUTH_KEY_DUPLICATED and forces a re-scan. Kill them or use --force:")
        for pid, cmd in others:
            print("  pid=%s %s" % (pid, cmd[:90]))
        return 3
    for pid, cmd in others:                      # --force: kill LOUDLY, with names
        print("--force: killing foreign client pid=%s %s" % (pid, cmd[:70]))
        hard_kill(pid)

    write_page(port)
    set_status("BOOT", note="starting the bridge...", generation=0)
    for old in (QR_PNG, QR_TXT):
        if os.path.exists(old):
            os.remove(old)

    httpd, real_port = serve(port)
    if httpd is None:
        print("PORTS %d-%d ARE TAKEN -- no page, and without it there is nowhere to look"
              % (port, port + 5))
        print("at the code (opening the file directly cannot work: the page must read status).")
        print("Free a port or run with --port 9100.")
        return 3
    url = "http://127.0.0.1:%d/" % real_port
    if real_port != port:
        print("port %d was busy -- page is on %d" % (port, real_port))
    log = open(LOG, "w", encoding="utf-8")
    # stdin=PIPE and NEVER closed: an MCP stdio server kills itself once stdin closes
    child = subprocess.Popen([shutil.which("node"), VENDOR_ENTRY],
                             stdin=subprocess.PIPE, stdout=log, stderr=log)
    print("PAGE: %s" % url)
    print("bridge pid=%s, waiting for a QR... (timeout %ss)" % (child.pid, timeout_sec))
    if open_page:
        open_in_browser(url)

    last, gen, deadline = None, 0, time.time() + timeout_sec
    last_qr_at, respawns = time.time(), 0
    try:
        while time.time() < deadline:
            # A pause between codes is NORMAL, not a fault: the server emits a code, waits,
            # then reconnects on its own. FIELD MEASUREMENT 2026-08-05: killing a LIVE
            # client to "fix" the pause is harmful. Hands-off run = 17 codes in a row;
            # the run with three "helpful" restarts = 2 codes per client and a dead end
            # in 4 minutes -- WhatsApp visibly throttles frequent reconnects. So we never
            # touch a living process: we only tell the page honestly that it is a pause.
            # We respawn a CORPSE only.
            stale = not paired() and time.time() - last_qr_at > STALE_SEC
            if stale and child.poll() is None:
                set_status("WAIT", generation=gen,
                           note="bridge is reconnecting, a fresh code is coming")
            if paired():
                set_status("LINKED", generation=gen)
                print("LINKED: creds.json appeared.")
                time.sleep(4)                    # let the page show "done"
                return 0
            blocks = QR_RE.findall(_read(LOG))
            if blocks and blocks[-1] != last:
                last = blocks[-1]
                gen += 1
                with open(QR_TXT, "w", encoding="ascii", errors="ignore") as f:
                    f.write(last)
                render(last)
                last_qr_at = time.time()
                set_status("QR", generation=gen,
                           qr_at=dt.datetime.now().strftime("%H:%M:%S"))
            if child.poll() is not None and not paired():
                if respawns < 3:                 # raise the dead, never touch the living
                    respawns += 1
                    set_status("BOOT", generation=gen,
                               note="bridge died, restarting (%d/3)" % respawns)
                    child = subprocess.Popen([shutil.which("node"), VENDOR_ENTRY],
                                             stdin=subprocess.PIPE, stdout=log, stderr=log)
                    last, last_qr_at = None, time.time()
                    print("bridge died -- restarted (%d/3), pid=%s" % (respawns, child.pid),
                          flush=True)
                    continue
                set_status("TIMEOUT", note="bridge keeps dying (code %s)" % child.returncode)
                print("BRIDGE DIED %d times, code %s -- see %s"
                      % (respawns + 1, child.returncode, LOG), flush=True)
                return 1
            time.sleep(1.5)
        set_status("TIMEOUT", generation=gen)
        print("TIMEOUT after %ss: showed %d code(s), no scan." % (timeout_sec, gen))
        return 1
    finally:
        hard_kill(child.pid)                     # not one stray client left behind
        log.close()


def check():
    print("linked          : %s  (%s)" % ("YES" if paired() else "NO", CREDS))
    print("server dir      : %s" % (VENDOR_DIR or "<not found>"))
    probs = vendor_ok()
    print("environment     : " + ("ok" if not probs else "; ".join(probs)))
    nodes = live_nodes()
    print("live clients    : %d%s" % (len(nodes),
                                      (" (pids %s)" % [p for p, _ in nodes]) if nodes else ""))
    st = _read(STATUS)
    print("last run        : " + (st.strip() or "no status.json yet"))
    return 0 if paired() else 1


def selftest():
    """Runs without a phone, without network, without the server installed:
    proves the part is CAPABLE of working."""
    ok = True
    os.makedirs(WORK, exist_ok=True)
    write_page(DEFAULT_PORT)
    for probe, why in [(os.path.exists(PAGE), "page is generated"),
                       ("status.json" in _read(PAGE), "page polls the status"),
                       (callable(render), "QR renderer present")]:
        print(("  ok  " if probe else "  FAIL") + "  " + why)
        ok &= bool(probe)
    try:
        render("selftest-payload")
        good = os.path.getsize(QR_PNG) > 200
    except Exception as e:
        good = False
        print("  FAIL  renderer crashed: " + str(e))
    print(("  ok  " if good else "  FAIL") + "  PNG is drawn")
    ok &= good
    set_status("BOOT", note="selftest")
    print(("  ok  " if os.path.exists(STATUS) else "  FAIL") + "  status.json is written")
    for f in (QR_PNG, QR_TXT, STATUS):
        if os.path.exists(f):
            os.remove(f)
    print("SELFTEST " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


def main():
    # We are often started in the background: without line buffering the page URL is
    # invisible until the whole run ends (measured: 5 minutes of empty output).
    try:
        sys.stdout.reconfigure(line_buffering=True, encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="diagnose, no side effects")
    ap.add_argument("--selftest", action="store_true", help="verify the part without a phone")
    ap.add_argument("--heal-patch", action="store_true", help="restore the QR_RAW patch")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--timeout-sec", type=int, default=900)
    ap.add_argument("--force", action="store_true", help="kill live clients and start anyway")
    ap.add_argument("--no-open", action="store_true", help="do not open the browser")
    a = ap.parse_args()
    if a.check:
        return check()
    if a.selftest:
        return selftest()
    if a.heal_patch:
        ok, msg = heal_patch()
        print(msg)
        return 0 if ok else 3      # 3 = environment not ready, same as a missing patch
    return pair(a.port, a.timeout_sec, a.force, not a.no_open)


if __name__ == "__main__":
    # Crash guard: the death of a tool must not look like "it found a problem".
    # SystemExit must NOT be caught -- it IS our normal return code (the first version
    # of this guard painted every clean exit as 4, including a PASSing selftest).
    try:
        rc = main()
    except KeyboardInterrupt:
        rc = 1
    except BaseException as e:
        print("CRASH: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        rc = 4
    sys.exit(rc)
