# -*- coding: utf-8 -*-
r"""Regression test for wa_qr_live.py. No phone, no network, no server needed:
we swap the paths out.

The test checks BEHAVIOUR (QR parsing out of the log, link detection, environment
diagnosis, port fallback, exit codes), not the fact that the module imports -- a test
that cannot go red on broken code is not a test.

Two regressions are pinned here forever, both paid for in the field:
  * 2026-08-05 (morning): the crash guard caught BaseException and therefore swallowed
    its own SystemExit -- EVERY clean exit was painted 4, including a PASSing selftest.
    A tool with a lying exit code is a watchdog you cannot trust.
  * 2026-08-05 (evening): "healing" a pause between QR codes by killing the live client
    made WhatsApp throttle us. Hands-off: 17 codes in a row. With three restarts: 2 codes
    per client and a dead end in 4 minutes. We only ever respawn a corpse.

Run: python test_wa_qr_live.py   (exit 0 = all green)
"""
import json
import os
import shlex
import socket
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE = os.path.join(HERE, "wa_qr_live.py")
sys.path.insert(0, HERE)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

os.environ.setdefault("WA_QR_WORK_DIR", tempfile.mkdtemp(prefix="wa_qr_selftest_"))
import wa_qr_live as w  # noqa: E402

FAILS, RAN = [], []


def check(name, cond, detail=""):
    RAN.append(name)
    print(("  OK   " if cond else "  FAIL ") + name +
          (("  -- " + detail) if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


def main():
    tmp = tempfile.mkdtemp(prefix="wa_qr_test_")

    # --- 1. link detection: a code request can save draft creds before pairing.
    w.CREDS = os.path.join(tmp, "creds.json")
    check("no creds -> not linked", w.paired() is False)
    open(w.CREDS, "w").close()
    check("empty creds -> not linked", w.paired() is False, "a zero-byte file proves nothing")
    def creds_case(name, value, expected):
        with open(w.CREDS, "w", encoding="utf-8") as f:
            json.dump(value, f)
        check(name, w.paired() is expected)

    creds_case("draft me is not pairing", {"me": {"id": "test"}}, False)
    creds_case("requested pairing code is not pairing", {"pairingCode": "test"}, False)
    creds_case("registered alone is not pairing", {"registered": True}, False)
    creds_case("non-object JSON is not pairing", [], False)
    creds_case("account without identities is not pairing", {"account": {"signature": "test"}}, False)
    creds_case("identities without account is not pairing", {"signalIdentities": [{}]}, False)
    creds_case("empty identities is not pairing", {"account": {"signature": "test"}, "signalIdentities": []}, False)
    creds_case("wrong account type is not pairing", {"account": "test", "signalIdentities": [{}]}, False)
    creds_case("wrong identities type is not pairing", {"account": {"signature": "test"}, "signalIdentities": "test"}, False)
    linked = {"account": {"signature": "synthetic"}, "signalIdentities": [{"synthetic": True}]}
    creds_case("account and identities are structural pairing evidence", linked, True)
    creds_case("registered false cannot reject structural evidence", dict(linked, registered=False), True)
    with open(w.CREDS, "w", encoding="utf-8") as f:
        f.write("{broken")
    check("malformed JSON is not pairing", w.paired() is False)

    # --- 2. QR parsing: take the LAST block, codes rotate
    log = "noise\nQR_RAW_BEGIN1@aaaQR_RAW_END\nmore noise\nQR_RAW_BEGIN2@bbbQR_RAW_END\n"
    blocks = w.QR_RE.findall(log)
    check("parser sees every code", len(blocks) == 2, str(blocks))
    check("we take the freshest", blocks[-1] == "2@bbb", str(blocks[-1:]))
    check("no codes -> empty", w.QR_RE.findall("nothing here") == [])

    # --- 3. environment diagnosis goes red on a wiped vendor patch
    w.VENDOR_ENTRY = os.path.join(tmp, "index.js")
    w.VENDOR_PATCH_FILE = os.path.join(tmp, "whatsapp.js")
    check("no server -> problem named", any("server not found" in p for p in w.vendor_ok()))
    open(w.VENDOR_ENTRY, "w").close()
    with open(w.VENDOR_PATCH_FILE, "w", encoding="utf-8") as f:
        f.write("qrcode.generate(qr)")           # patch absent
    check("patch wiped -> problem named", any("patch" in p for p in w.vendor_ok()))
    with open(w.VENDOR_PATCH_FILE, "w", encoding="utf-8") as f:
        f.write('console.error("QR_RAW_BEGIN"+qr+"QR_RAW_END");qrcode.generate(qr)')
    check("patch present -> silent about it", not any("patch" in p for p in w.vendor_ok()))

    # --- 3b. heal_patch inserts the raw print, is idempotent, and REPORTS FAILURE.
    # A repair tool that says "ok" after repairing nothing is the false silence this
    # kit exists to kill (panel finding, 2026-08-10).
    with open(w.VENDOR_PATCH_FILE, "w", encoding="utf-8") as f:
        f.write("qrcode.generate(qr)")
    ok, msg = w.heal_patch()
    healed = open(w.VENDOR_PATCH_FILE, encoding="utf-8").read()
    check("heal-patch inserts QR_RAW", ok and "QR_RAW_BEGIN" in healed, msg)
    check("heal-patch is idempotent", w.heal_patch() == (True, "patch already in place"))
    with open(w.VENDOR_PATCH_FILE, "w", encoding="utf-8") as f:
        f.write("some server code with no anchor at all")
    ok2, msg2 = w.heal_patch()
    check("no anchor -> heal-patch reports FAILURE", ok2 is False, msg2)
    w.VENDOR_PATCH_FILE = os.path.join(tmp, "does-not-exist.js")
    check("missing file -> heal-patch reports FAILURE", w.heal_patch()[0] is False)
    rc_heal = subprocess.run([sys.executable, ENGINE, "--heal-patch"],
                             capture_output=True, text=True,
                             env=dict(os.environ, WHATSAPP_MCP_DIR=os.path.join(tmp, "nope")))
    check("failed heal-patch exits non-zero", rc_heal.returncode != 0,
          "code %s -- a repair that repaired nothing must not exit 0" % rc_heal.returncode)

    # --- 4. page and status: the whole live loop hangs off these two
    w.WORK = tmp
    w.PAGE = os.path.join(tmp, "index.html")
    w.STATUS = os.path.join(tmp, "status.json")
    w.write_page(1234)
    page = open(w.PAGE, encoding="utf-8").read()
    check("page polls the status", "status.json" in page)
    check("page busts the image cache", "qr.png?t=" in page)
    check("page knows about success", "LINKED" in page)
    w.set_status("QR", generation=7)
    st = json.load(open(w.STATUS, encoding="utf-8"))
    check("status written whole", st["state"] == "QR" and st["generation"] == 7, str(st))
    check("temp file cleaned up", not os.path.exists(w.STATUS + ".tmp"))

    # --- 5. port: first one taken -> sit on the next, do not die
    squat = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    squat.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    squat.bind(("127.0.0.1", 8901))
    squat.listen(1)
    httpd, got = w.serve(8901)
    check("busy port -> next one", httpd is not None and got == 8902, "got=%s" % got)
    if httpd:
        httpd.shutdown()
    squat.close()
    src = open(ENGINE, encoding="utf-8").read()
    check("no file:// fallback (the page would lie)", "url = PAGE" not in src)

    # --- 6. REGRESSION (2026-08-05 evening): never kill a LIVE vendor over a pause
    stale_block = src.split("stale = not paired()")[1].split("if paired():")[0]
    check("pause -> honest status, not a kill", "hard_kill" not in stale_block,
          stale_block[:120])
    check("pause -> WAIT state", '"WAIT"' in stale_block)
    check("pause threshold >= 3 minutes", w.STALE_SEC >= 180, "STALE_SEC=%s" % w.STALE_SEC)
    check("page explains the pause", "s.note" in open(w.PAGE, encoding="utf-8").read())

    # --- 7. REGRESSION (2026-08-05 morning): a clean exit is not painted as a crash
    rc = subprocess.run([sys.executable, ENGINE, "--selftest"], capture_output=True, text=True)
    check("selftest exits 0, not 4", rc.returncode == 0,
          "code %s -- the crash guard is swallowing SystemExit again" % rc.returncode)
    rc2 = subprocess.run([sys.executable, ENGINE, "--check"], capture_output=True, text=True)
    check("check exits meaningfully (0/1), not 4", rc2.returncode in (0, 1),
          "code %s" % rc2.returncode)

    # --- 8. Native absolute paths keep this valid on Windows Python 3.13+ too.
    entry = os.path.abspath(os.path.join(tmp, "isolated", "node_modules", "@sjawhar", "whatsapp-mcp", "dist", "index.js"))
    global_entry = os.path.abspath(os.path.join(tmp, "global", "node_modules", "@sjawhar", "whatsapp-mcp", "dist", "index.js"))
    unrelated = os.path.abspath(os.path.join(tmp, "other", "server.js"))
    def command(*argv):
        return subprocess.list2cmdline(argv) if os.name == "nt" else shlex.join(argv)
    rows = [
        (100, 90, "python3", command("python3", "whatsapp-mcp-kit/pair/wa_qr_live.py")),
        (90, 80, "node", command("node", entry)),
        (80, 1, "bash", "bash -c whatsapp-mcp-kit"),
        (101, 1, "node", command("node", unrelated)),
        (102, 1, "node", command("node", entry, "--http")),
        (103, 1, "node", command("node", entry + ".other")),
        (104, 1, "python3", command("python3", entry)),
    ]
    with patch.object(w, "VENDOR_ENTRY", entry), patch.object(w, "_process_cwd", return_value=None, create=True):
        found = w._server_rows(rows, 100)
        check("native selector excludes self and unrelated, counts real ancestor", found is not None and [p for p, _ in found] == [90, 102], str(found))
        found_global = w._server_rows([(200, 1, "node", command("node", global_entry))], 100)
        check("other installation of same vendor is detected", found_global is not None and [p for p, _ in found_global] == [200], str(found_global))
        alias = os.path.abspath(os.path.join(tmp, "bin", "custom-server-alias"))
        original_realpath = w.os.path.realpath
        def resolved_alias(value):
            return global_entry if os.path.normcase(os.path.abspath(value)) == os.path.normcase(alias) else original_realpath(value)
        with patch.object(w.os.path, "realpath", side_effect=resolved_alias):
            aliased = w._server_rows([(207, 1, "node", command("node", alias, "--http"))], 100)
            check("resolved npm bin alias from other install is detected", aliased is not None and [p for p, _ in aliased] == [207], str(aliased))
        shim = os.path.abspath(os.path.join(tmp, "bin", "whatsapp-mcp.cmd"))
        shimmed = w._server_rows([(208, 1, "node", command("node", shim, "--http"))], 100)
        check("explicit absolute WhatsApp bin name is conservative match", shimmed is not None and [p for p, _ in shimmed] == [208], str(shimmed))
        check("unrelated relative Node and REPL do not block", w._server_rows([(201, 1, "node", "node server.js"), (202, 1, "node", "node")], 100) == [])
        check("hidden Node command needs manual inventory", w._server_rows([(203, 1, "node.exe", "")], 100) is None)
        check("unresolved plausible npm start is UNKNOWN", w._server_rows([(204, 1, "node", "node dist/index.js")], 100) is None)
        check("unrelated relative mjs is not a WhatsApp owner", w._server_rows([(205, 1, "node", "node ./server.mjs")], 100) == [])
    cwd = os.path.dirname(os.path.dirname(entry))
    with patch.object(w, "VENDOR_ENTRY", entry), patch.object(w, "_process_cwd", return_value=cwd, create=True):
        resolved = w._server_rows([(206, 1, "node", "node dist/index.js")], 100)
        check("relative installed entry uses its own process cwd", resolved is not None and [p for p, _ in resolved] == [206], str(resolved))
    listing = "300 1 node " + shlex.quote(entry)
    with patch.object(w.os, "name", "posix"), patch.object(w, "VENDOR_ENTRY", entry), \
         patch.object(w.subprocess, "run", return_value=SimpleNamespace(stdout=listing, returncode=0)):
        parsed = w.live_nodes()
        check("POSIX ps parses pid ppid and argv without comm column", parsed is not None and [p for p, _ in parsed] == [300], str(parsed))
    spaced_listing = "301 1 /Applications/My Runtime/node " + shlex.quote(entry)
    with patch.object(w.os, "name", "posix"), patch.object(w, "VENDOR_ENTRY", entry), \
         patch.object(w.subprocess, "run", return_value=SimpleNamespace(stdout=spaced_listing, returncode=0)):
        parsed = w.live_nodes()
        check("POSIX executable path with spaces does not hide owner", parsed is not None and [p for p, _ in parsed] == [301], str(parsed))
    with patch.object(w.os, "name", "posix"), \
         patch.object(w.subprocess, "run", return_value=SimpleNamespace(stdout="", returncode=1)):
        check("failed process inventory is UNKNOWN not empty", w.live_nodes() is None)
    with patch.object(w, "paired", return_value=False), patch.object(w, "vendor_ok", return_value=[]), \
         patch.object(w, "WORK", tmp), \
         patch.object(w, "live_nodes", return_value=[(102, "node test")]), \
         patch.object(w, "hard_kill") as killer, patch.object(w, "serve", return_value=(None, None)):
        rc_force = w.pair(1234, 1, True, False)
        check("force never kills a foreign process", rc_force == 3 and not killer.called)
    with patch.object(w, "paired", return_value=False), patch.object(w, "vendor_ok", return_value=[]), \
         patch.object(w, "WORK", tmp), \
         patch.object(w, "live_nodes", return_value=None), patch.object(w, "serve") as server:
        try:
            rc_unknown = w.pair(1234, 1, False, False)
        except TypeError:
            rc_unknown = -1
        check("unknown inventory refuses pairing before server start", rc_unknown == 3 and not server.called)

    print("\n" + ("ALL GREEN (%d checks)" % len(RAN) if not FAILS
                  else "RED (%d of %d): %s" % (len(FAILS), len(RAN), ", ".join(FAILS))))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
