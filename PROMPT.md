# WhatsApp setup prompt for Claude Code or Codex

Use the maintained [Claude Code prompt](PROMPT-CLAUDE.ru.md) or [Codex prompt](PROMPT-CODEX.ru.md), together with the [full runbook](README.ru.md). They replace the historical per-session stdio quickstart.

```text
Set up my WhatsApp for Claude Code and Codex using https://github.com/tonydzi/whatsapp-mcp-kit. Read README.ru.md and the prompt for this harness from the same inspected revision. Inventory existing working installation first. Use one account-local managed HTTP owner, with both clients attached, private XDG data root and protected bearer environment. Clean v2.4.0 HTTP does not acquire an account lock: one supervisor and no parallel manual owner are operational requirements. Do not copy auth state, expose QR/code/keys, kill other clients, or blindly re-pair. Pair through the local QR helper; nonempty creds alone is not success. Verify a new incoming nonce from the phone in both clients and again after a controlled owned restart. External sends require specific approval; reconcile timeouts before retry. Report static, configured, persisted pairing, live read, live send and recipient ACK separately. No ready phone-code CLI is promised by this kit.
```

Source and credit: https://github.com/tonydzi
