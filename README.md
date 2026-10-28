# whatsapp-mcp-kit

Connect Claude (Claude Code / Claude Desktop / Codex — any MCP client) to **a WhatsApp account** so it can read your chats and send messages. Includes portable setup skills, prompts, private pairing, shared HTTP configuration and recovery instructions.

## Start in 3 steps

1. Open Claude Code or Codex in an empty folder on the machine that should read WhatsApp.
2. Paste the block from [`PROMPT.md`](PROMPT.md) (Russian versions: [Claude Code](PROMPT-CLAUDE.ru.md), [Codex](PROMPT-CODEX.ru.md)). Read it first: the agent checks what you already have, explains the account risk once, installs one shared local service and opens a QR page.
3. On your phone: **WhatsApp → Settings → Linked devices → Link a device**, scan the page.

**Done when:** you send yourself a fresh test word in WhatsApp and the agent reads that exact word back. Everything below is the detail behind these three steps.

Built and battle-tested at [Palo Alto AI Research Lab](https://github.com/tonydzi/tonydzi) — our Claude fleet has been reading WhatsApp through exactly this setup since June 2026.

## Current setup for Claude Code and Codex

Read the [complete runbook (Russian)](README.ru.md), then use the [Claude Code prompt](PROMPT-CLAUDE.ru.md) or [Codex prompt](PROMPT-CODEX.ru.md). Install the portable [whatsapp-connect skill](skills/whatsapp-connect/SKILL.md) for future sessions. Both clients connect to one loopback HTTP service; they must not each launch a full WhatsApp connection.

This is one linked-device stack: [`@sjawhar/whatsapp-mcp`](https://github.com/sjawhar/whatsapp-mcp-2.0) + Baileys. Multiple accounts need separate private data roots and owners. The unofficial-client account restriction risk and access to private message content must be understood before linking; see [security](docs/SECURITY.md).

### Pinned setup and pairing

The runbook uses isolated npm installation of version **2.4.0**, checked historical patches, private environment storage and one operational supervisor. Its HTTP branch has **no built-in account lock** in that release; do not start another owner manually or through a second service. The docs distinguish this operational rule from enforced exclusion.

The [QR helper](pair/wa_qr_live.py) holds stdin open and renders a refreshing local PNG page. It now rejects nonempty draft credentials: saved account/Signal-identity structure is required. That is persisted-state evidence, not fresh network connectivity. Prove a new incoming nonce in each AI client after startup and restart. A port, cached profile, old chat list or exit 0 does not prove live delivery.

For code-based phone pairing see the [bounded prompt](PROMPT-PHONE-CODE.ru.md). Baileys has the API; this kit does not yet ship a ready phone-code CLI. Do not invent flags for the MCP server or launch a second socket on the same auth directory.

### What is tested

Offline synthetic regression covers draft/invalid persisted state, QR parsing and helper process behavior. New phone pairing, a fresh three-OS installation and recipient acceptance have **not** been rerun for this documentation update. Preserve these limits in your own report.

Do not run remote prompts blindly or enter secrets in an agent conversation. Follow [pairing documentation](pair/README.md) with the selected package bytes. Phone errors can have several causes; expiry is one possible cause, not a diagnosis from the wording alone. History depth is not guaranteed: measure actual sync rather than assuming a complete archive.

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

<!--we-ask:start-->

## Contributors welcome — and here is what we are missing

We spend a lot of time answering other people's issues. It was fair to say out loud
what we have not built ourselves:

- [Add a phone-backup path for the full archive](https://github.com/tonydzi/whatsapp-mcp-kit/issues/1)
- [Make the patches survive `npm update`](https://github.com/tonydzi/whatsapp-mcp-kit/issues/2)
- [Extend `--heal-patch` beyond patch 0001](https://github.com/tonydzi/whatsapp-mcp-kit/issues/3)

Issues labelled [`accepted`](https://github.com/tonydzi/whatsapp-mcp-kit/issues?q=is%3Aissue+is%3Aopen+label%3Aaccepted) are scoped, free to take, and nobody is on them.
Comment **"claiming this"** — no permission needed — and it is yours for 7 days.
New here? Start with [`good first issue`](https://github.com/tonydzi/whatsapp-mcp-kit/issues?q=is%3Aissue+is%3Aopen+label%3A%22good+first+issue%22).

**You keep the copyright to your code.** No CLA, no assignment, ever — your contribution goes
in under this repo's existing license, the same terms as ours. We answer every issue and PR
within 48 hours, including "no, and here is why"; our silence is our bug, so ping the thread.

Full deal: [CONTRIBUTING.md](https://github.com/tonydzi/.github/blob/main/CONTRIBUTING.md)

<!--we-ask:end-->

---

<!--ecosystem-map:start-->

## 🧩 One piece of a working system

This repository is one piece lifted out of a live operation: one engineer running a fleet of
machines, built with Claude as implementation collaborator; the machines reach consensus with
each other and wake the human only for money or the irreversible. It was extracted after it
survived production, not written as a demo — and it runs on its own: nothing here phones home
to the rest.

**See how the whole thing fits together → [SYSTEM.md](https://github.com/tonydzi/tonydzi/blob/main/SYSTEM.md)**

Its closest neighbours in the **connectors** layer: [`mcp-daemon-diet`](https://github.com/tonydzi/mcp-daemon-diet) · [`telegram-mcp-kit`](https://github.com/tonydzi/telegram-mcp-kit)

<!--ecosystem-map:end-->

<!-- READ-WITH-AI:START (generated by read_with_ai.py - do not hand-edit) -->

### READ THIS WITH AI

One click and an agent reads the repo, pulls out the patterns and helps you apply them to your own work.

<a href="https://chatgpt.com/codex?prompt=Read%20this%20repo%3A%20https%3A%2F%2Fgithub.com%2Ftonydzi%2Fwhatsapp-mcp-kit%20%28%E2%80%9Cwhatsapp-mcp-kit%E2%80%9D%20-%20Link%20WhatsApp%20to%20Claude%20%28or%20any%20MCP%20client%29%20in%20~20%20minutes%3A%20a%20live%20self-refreshing%20QR%20page%20that%20makes%20pairing%20actually%20work%2C%20production%20patches%2C%20and%2012%20field%20gotchas.%20On%20top%20of%20%40sjawhar%2Fwhatsapp-mcp%29.%20Work%20out%20what%20problem%20it%20actually%20solves%2C%20pull%20out%20the%20reusable%20patterns%20and%20help%20me%20apply%20them%20to%20my%20own%20setup.%20Start%20by%20asking%20what%20I%20am%20working%20on."><img alt="Codex - open" src="https://img.shields.io/badge/Codex-open-000000?style=for-the-badge&logo=openai&logoColor=white"></a> <a href="https://chatgpt.com/?q=Read%20this%20repo%3A%20https%3A%2F%2Fgithub.com%2Ftonydzi%2Fwhatsapp-mcp-kit%20%28%E2%80%9Cwhatsapp-mcp-kit%E2%80%9D%20-%20Link%20WhatsApp%20to%20Claude%20%28or%20any%20MCP%20client%29%20in%20~20%20minutes%3A%20a%20live%20self-refreshing%20QR%20page%20that%20makes%20pairing%20actually%20work%2C%20production%20patches%2C%20and%2012%20field%20gotchas.%20On%20top%20of%20%40sjawhar%2Fwhatsapp-mcp%29.%20Work%20out%20what%20problem%20it%20actually%20solves%2C%20pull%20out%20the%20reusable%20patterns%20and%20help%20me%20apply%20them%20to%20my%20own%20setup.%20Start%20by%20asking%20what%20I%20am%20working%20on."><img alt="ChatGPT - open" src="https://img.shields.io/badge/ChatGPT-open-10a37f?style=for-the-badge&logo=openai&logoColor=white"></a> <a href="https://claude.ai/new?q=Read%20this%20repo%3A%20https%3A%2F%2Fgithub.com%2Ftonydzi%2Fwhatsapp-mcp-kit%20%28%E2%80%9Cwhatsapp-mcp-kit%E2%80%9D%20-%20Link%20WhatsApp%20to%20Claude%20%28or%20any%20MCP%20client%29%20in%20~20%20minutes%3A%20a%20live%20self-refreshing%20QR%20page%20that%20makes%20pairing%20actually%20work%2C%20production%20patches%2C%20and%2012%20field%20gotchas.%20On%20top%20of%20%40sjawhar%2Fwhatsapp-mcp%29.%20Work%20out%20what%20problem%20it%20actually%20solves%2C%20pull%20out%20the%20reusable%20patterns%20and%20help%20me%20apply%20them%20to%20my%20own%20setup.%20Start%20by%20asking%20what%20I%20am%20working%20on."><img alt="Claude - open" src="https://img.shields.io/badge/Claude-open-d97757?style=for-the-badge&logo=anthropic&logoColor=white"></a>

<details>
<summary>Copy the prompt (works in any agent: Gemini, Grok, a local model, your own CLI)</summary>

```text
Read this repo: https://github.com/tonydzi/whatsapp-mcp-kit (“whatsapp-mcp-kit” - Link WhatsApp to Claude (or any MCP client) in ~20 minutes: a live self-refreshing QR page that makes pairing actually work, production patches, and 12 field gotchas. On top of @sjawhar/whatsapp-mcp). Work out what problem it actually solves, pull out the reusable patterns and help me apply them to my own setup. Start by asking what I am working on.
```

</details>

<sub>— TonyDzi, Palo Alto AI Research Lab · second brain, agent coordination, persistent memory: github.com/tonydzi</sub>

<!-- READ-WITH-AI:END -->
