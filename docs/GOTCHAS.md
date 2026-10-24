# GOTCHAS — the hours we already paid, so you don't

Every item is a real incident from running this setup in production on a multi-machine Claude fleet since June 2026. Dates included so you know it is field data, not theory.

## 1. An MCP stdio server kills itself when stdin closes (2026-06-15)
Starting the server standalone to pair it dies instantly: *"stdin closed (parent disconnected) — shutting down"*. That is correct MCP behaviour and it makes naive pairing impossible. Fix: spawn it with `stdin=PIPE` and **never close that pipe** — that is the one thing `pair/wa_qr_live.py` exists to do. (Our first version was a `keepalive.js` wrapper; a python parent that holds the pipe is simpler and one process fewer.)

## 2. The terminal QR is unscannable, and the raw string is not printed (2026-06-15)
Upstream renders the code as terminal ASCII art, which is mosaic in most Windows console fonts, and only emits the raw string inside a `.catch()` fallback. There is nothing to render a picture from. Fix: `patches/0001` prints `QR_RAW_BEGIN<code>QR_RAW_END` on stderr unconditionally; the pairing tool scrapes it and draws a real PNG.

## 3. A phone connection error can be an expired QR
An expired QR was one measured cause of this wording in our setup. The text alone does not diagnose the cause. Check the current generation, time and logs before assuming either expiry or a network failure. The local page refreshes when a new code arrives.

## 4. Do not "heal" a pause by restarting the live client (2026-08-05) — our most expensive lesson
Our first tool treated a gap between codes as a hang and rebuilt the client. Measurement, same evening, both halves: **hands-off run = 17 codes in a row**; run with three automatic rebuilds = **2 codes per client** and a hard stop after 4 minutes. WhatsApp visibly throttles frequent reconnects, so the "fix" caused the failure. Fix: pauses only change the text on the page; we respawn **only** a process that is actually dead (`child.poll() is not None`). Generalised rule: before restarting somebody else's daemon for being quiet, prove it is dead — a live process in a pause and a corpse look identical only in your own timer.

## 5. Windows process cleanup must target only the child you created
Parent termination can leave a Node descendant alive. Before another pairing run, inventory the real connection owner. Cleanup of this helper's own child uses its PID tree. Never kill arbitrary Node processes or use a broad substring match as account ownership evidence. `--force` must not bypass ownership checks.

## 6. One connection owner, many MCP clients
Cached read-only access is not proof that another network socket is safe. Use one managed owner per auth directory, with both agents attached over HTTP. Clean server v2.4.0 does not acquire its stdio account lock in HTTP mode: sole-supervisor operation is required and is not an enforced guarantee. `AUTH_KEY_DUPLICATED` is a Telegram error, not a diagnosis for this Baileys stack.

## 7. "N zombie node processes" is usually a false alarm — diagnose by PARENT, not by count (2026-06-16)
We once counted 11 `node.exe` and assumed a leak. `Get-CimInstance Win32_Process -Filter "Name='node.exe'"` and check each `ParentProcessId`: a node whose parent is a **live** MCP client process is a legitimate per-session instance and gets reaped on disconnect. Only a node whose parent is **dead** is a real orphan. The count dropped 11 → 1 by itself within seconds.

## 8. Groups come back as numbers, and the cause is not where you look (2026-06-15)
`get_chat` / `resolve_contacts` return `<digits>@g.us`. The reason is not a permissions or metadata problem: `db.getChat` always fills a placeholder name `"<digits> (group)"` via `fromJid()`, so the code path that fetches the real subject (`resolveChatName` → `sock.groupMetadata().subject`) is never reached. Fix: `patches/0002` forces resolution when the name still matches the placeholder. Do **not** spawn a standalone Baileys script to fetch group metadata — that is a second write client, see gotcha 5.

## 9. `get_my_profile` and `list_chats` answer from cache — they cannot prove the link is alive (2026-07/08)
This one cost 26 days. Our health check called the profile tool, got a valid answer, and reported green while the bridge had been dead for weeks. Proof of current connectivity requires a new incoming nonce after startup, read through the owner by each client. Nonempty credentials alone can be draft state; the helper checks saved account/identity structure separately.

## 10. `npm update` silently removes both patches
The patches live in `node_modules`. After any update or reinstall, pairing stops working (no `QR_RAW_BEGIN` in the log) and groups turn back into numbers. Re-apply from `patches/`, or run `python pair/wa_qr_live.py --heal-patch` for patch 0001. Check first: `grep QR_RAW "$(npm root -g)/@sjawhar/whatsapp-mcp/dist/whatsapp.js"`.

## 11. History arrives gradually, and that is the protocol, not a bug
History depth and timing vary. Measure what actually arrived rather than assuming either a complete archive or a fixed recent-only window. A complete archive needs a separately verified export or backup process. Plan imports accordingly — an import run 10 minutes after linking will under-count and look broken.

## 12. Newly added stdio MCP tools appear only after a client restart
Registering the server mid-session and calling `mcp__whatsapp__*` gives "tool not found". Reload the client or start a fresh session, then check tool discovery and a fresh incoming nonce; a cached profile alone is insufficient.
