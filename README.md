# whatsapp-mcp-kit

Connect Claude (Claude Code / Claude Desktop / Codex — any MCP client) to **a WhatsApp account** so it can read your chats and send messages. The server already exists and is good; what nobody ships is the **linking procedure**. Ours took an evening of broken iterations and a re-scan loop; with this kit it should take you ~20 minutes.

Built and battle-tested at [Palo Alto AI Research Lab](https://github.com/tonydzi/Palo-Alto-AI-Research-Lab) — our Claude fleet has been reading WhatsApp through exactly this setup since June 2026.

> ⚠️ Read [`docs/SECURITY.md`](docs/SECURITY.md) first. Baileys is an **unofficial** WhatsApp client; upstream recommends a dedicated number, not your personal one. We linked a main number knowingly and accept the ban risk. That should be a decision, not an accident.

## What you get

1. **A working setup path** on top of the upstream server [`@sjawhar/whatsapp-mcp`](https://github.com/sjawhar/whatsapp-mcp-2.0) (Node/Baileys, security-hardened fork of `karlfoster/whatsapp-mcp-2.0`; 17 tools — list/search chats, messages, contacts, send text & files, download media, transcribe voice notes).
2. **[`PROMPT.md`](PROMPT.md)** — a copy-paste prompt you hand to Claude Code or Codex; it performs the installation and walks you through the QR scan, gotchas included.
3. **[`pair/wa_qr_live.py`](pair/wa_qr_live.py)** — the piece that made linking actually work: it keeps the stdio server alive, scrapes the raw QR string out of its log, renders a **PNG** and serves a **live localhost page** that refreshes the code by itself. Plus a 27-check regression test that needs no phone, no network and no server installed.
4. **Patches** we run in production, pinned to upstream **npm v2.4.0** (`git apply --check` proven on a fresh `npm pack` unpack):
   - [`patches/0001-qr-raw-to-stderr.patch`](patches/0001-qr-raw-to-stderr.patch) — print the raw QR string, always. Upstream only emits terminal ASCII art (and the raw string solely in a `.catch()` fallback), and that art is unscannable mosaic in most Windows console fonts. Without this patch there is nothing to render a PNG from.
   - [`patches/0002-group-subject-resolve.patch`](patches/0002-group-subject-resolve.patch) — real group names. `db.getChat` always fills a `<digits> (group)` placeholder, so `resolveChatName` never fires and every group shows up as a number. Cost us ~70 unnamed groups.
5. **[`docs/GOTCHAS.md`](docs/GOTCHAS.md)** — every trap we paid hours for, with dates.
6. **[`docs/SECURITY.md`](docs/SECURITY.md)** — a WhatsApp MCP is your whole WhatsApp. Read before linking.

## Quickstart (manual)

```bash
# 0. get the kit (patches/ and pair/ must sit together on disk)
git clone https://github.com/tonydzi/whatsapp-mcp-kit ~/whatsapp-mcp-kit

# 1. install the server (Node >= 18)
npm i -g @sjawhar/whatsapp-mcp

# 2. apply the kit patches to the installed package
#    (the folder is not a git repo -- git apply patches a plain working tree just fine)
cd "$(npm root -g)/@sjawhar/whatsapp-mcp"
git apply ~/whatsapp-mcp-kit/patches/0001-qr-raw-to-stderr.patch
git apply ~/whatsapp-mcp-kit/patches/0002-group-subject-resolve.patch

# 3. link the phone: live QR page on http://127.0.0.1:8799
pip install qrcode pillow
python ~/whatsapp-mcp-kit/pair/wa_qr_live.py

# 4. register in Claude Code
claude mcp add whatsapp --scope user -- node "$(npm root -g)/@sjawhar/whatsapp-mcp/dist/index.js"
```

On the page: phone → WhatsApp → **Settings → Linked devices → Link a device** → point the camera. Restart your Claude session (a newly added stdio MCP appears only after a restart), then call `get_my_profile`.

Exit codes of the pairing tool: `0` linked · `1` timeout · `2` already linked · `3` environment not ready · `4` crash — and they do not lie: a `--heal-patch` that patched nothing exits 3, not 0. Diagnose anytime with `--check` (zero side effects), prove the tool itself with `--selftest`.

## The lazy path

Open Claude Code, paste the contents of [`PROMPT.md`](PROMPT.md), scan one QR. Done.

## The three things that actually cost us the evening

1. **An MCP stdio server kills itself when stdin closes.** Any standalone pairing run dies instantly with "stdin closed (parent disconnected) — shutting down". The pairing tool holds stdin open forever.
2. **"Check your connection and try again later" on the phone is not a network error** — it means you scanned an **expired** QR (they live ~18-20s). Hence the auto-refreshing page: you always scan the current one.
3. **A pause between codes is normal; killing the live client to "fix" it makes things worse.** Measured 2026-08-05: hands-off run produced 17 codes in a row; the run that restarted the client three times got 2 codes per client and gave up in 4 minutes — WhatsApp throttles frequent reconnects. We respawn a corpse only (`child.poll() is not None`).

## Why a user-account server and not the Business API?

The Cloud/Business API cannot read your existing personal chats — that is the entire point of giving an assistant your WhatsApp. It is also why the security page exists. If your use case fits the official API, use the official API: it is supported and cannot get you banned.

## Known limits (honest)

- **History loads gradually.** A companion device receives recent chats, not your multi-year archive. For the full archive you need a phone-backup path — not in this kit.
- **One writer per link.** A second READ-ONLY client coexists (the server degrades the newcomer to read-only); a second WRITE client gives `AUTH_KEY_DUPLICATED` and forces a re-scan.
- **Patches live in `node_modules`** and are wiped by any `npm update` / reinstall. Re-apply, or run `python pair/wa_qr_live.py --heal-patch` for patch 0001.
- **The QR scan itself cannot be automated.** WhatsApp accepts a companion device only from the owner's phone. Everything around the scan is automated here; the scan is yours.

## License

MIT (same as upstream). Upstream code is not vendored — we ship patches against it and credit the original authors: [`sjawhar/whatsapp-mcp-2.0`](https://github.com/sjawhar/whatsapp-mcp-2.0), forked from `karlfoster/whatsapp-mcp-2.0`, built on [Baileys](https://github.com/WhiskeySockets/Baileys).

---

Part of the connector kit series by Palo Alto AI Research Lab — see also [`telegram-mcp-kit`](https://github.com/tonydzi/telegram-mcp-kit) and [`mcp-daemon-diet`](https://github.com/tonydzi/mcp-daemon-diet) (one shared MCP daemon per machine instead of a copy in every session; the recipe applies to this server too). Questions / broken step? Open an issue — we answer within 24h.

## AI contributors

This project is built by a human + AI team, and the git log says so: Claude writes most of
the code, Codex and Grok review it, Gemini feeds the research. Each is credited on a commit
**only if its output changed that commit's content** — no decorative credits. Lab-wide
policy, one source for every repo: [AI-CONTRIBUTORS.md](https://github.com/tonydzi/.github/blob/main/AI-CONTRIBUTORS.md).

---


> **Publishing your own internals?** This repo was sanitized for release with
> [`oss-publish`](https://github.com/tonydzi/oss-publish) — our substitution pipeline:
> personal data is replaced by plausible fakes of the same shape (never `<REDACTED>`),
> and a fail-closed gate re-scans the whole tree before the push. Free, MIT.

<!--kits-series:start-->

## 🧰 Connector & Ops Kits

Eight kits, all published 2026-08-10, each lifted out of the same live fleet after it
survived production rather than written as a demo. They are independent: take one, ignore
the rest. All stdlib-only Python, all free.

| kit | what it solves |
|---|---|
| [`telegram-mcp-kit`](https://github.com/tonydzi/telegram-mcp-kit) | Connect your agent to your own Telegram account in ~15 minutes, with the production patches and every gotcha |
| [`whatsapp-mcp-kit`](https://github.com/tonydzi/whatsapp-mcp-kit) | Link WhatsApp, using a live self-refreshing QR page that makes pairing actually work |
| [`mcp-daemon-diet`](https://github.com/tonydzi/mcp-daemon-diet) | One shared MCP daemon per machine instead of a stdio copy in every session, with a watchdog that will not blind your live sessions |
| [`agent-approval-gate`](https://github.com/tonydzi/agent-approval-gate) | Your agent needs a human's OK and nobody is at the terminal: the ask goes to a messenger, the answer comes back into the run |
| [`fleet-deploy`](https://github.com/tonydzi/fleet-deploy) | Roll a fix to N machines and prove it landed on each one: canary waves and a verify that must read a fact back |
| [`secondop-panel`](https://github.com/tonydzi/secondop-panel) | Nobody reviews themselves, and one reviewer model is one blind spot: fan a change out to several model families with quorum and honest skips |
| [`oss-publish`](https://github.com/tonydzi/oss-publish) | Open up internal work without leaking it: plausible substitutions of the same shape, then a fail-closed gate over the whole tree |
| [`llm-spend-audit`](https://github.com/tonydzi/llm-spend-audit) | What your own wiring charges on every session, and which paid subscriptions are going undrawn |

<!--kits-series:end-->

<!--ecosystem-map:start-->

## 🧩 One piece of a working system

This repository is one piece lifted out of a live operation: one non-technical founder, an AI
cofounder, and a fleet of machines that reach consensus with each other and wake the human only
for money or the irreversible. It was extracted after it survived production, not written as a
demo — and it runs on its own: nothing here phones home to the rest.

**See how the whole thing fits together → [SYSTEM.md](https://github.com/tonydzi/Palo-Alto-AI-Research-Lab/blob/main/SYSTEM.md)**

Its closest neighbours in the **connectors** layer: [`telegram-mcp-kit`](https://github.com/tonydzi/telegram-mcp-kit) · [`mcp-daemon-diet`](https://github.com/tonydzi/mcp-daemon-diet)

<!--ecosystem-map:end-->
