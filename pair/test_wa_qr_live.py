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
import socket
import subprocess
import sys
import tempfile

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

    # --- 1. link detection: missing/empty creds = NOT linked, non-empty = linked
    w.CREDS = os.path.join(tmp, "creds.json")
    check("no creds -> not linked", w.paired() is False)
    open(w.CREDS, "w").close()
    check("empty creds -> not linked", w.paired() is False, "a zero-byte file proves nothing")
    with open(w.CREDS, "w", encoding="utf-8") as f:
        f.write('{"me":1}')
    check("non-empty creds -> linked", w.paired() is True)

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

    print("\n" + ("ALL GREEN (%d checks)" % len(RAN) if not FAILS
                  else "RED (%d of %d): %s" % (len(FAILS), len(RAN), ", ".join(FAILS))))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
