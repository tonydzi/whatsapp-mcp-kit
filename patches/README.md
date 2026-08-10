# patches/

Two patches against **`@sjawhar/whatsapp-mcp` npm v2.4.0**, applied to the installed package (`$(npm root -g)/@sjawhar/whatsapp-mcp`). Both touch one file, `dist/whatsapp.js`.

The install folder is not a git repository — `git apply` works there anyway, it patches the working tree:

```bash
cd "$(npm root -g)/@sjawhar/whatsapp-mcp"
git apply --check /path/to/whatsapp-mcp-kit/patches/0001-qr-raw-to-stderr.patch   # dry run first
git apply         /path/to/whatsapp-mcp-kit/patches/0001-qr-raw-to-stderr.patch
git apply         /path/to/whatsapp-mcp-kit/patches/0002-group-subject-resolve.patch
```

Order matters: 0002 is cut against the tree with 0001 already applied. Verify afterwards:

```bash
node --check dist/whatsapp.js
grep -c QR_RAW dist/whatsapp.js      # expect 1
grep -c isPlaceholder dist/whatsapp.js
```

## 0001-qr-raw-to-stderr.patch — REQUIRED for pairing

Prints the raw QR string as `QR_RAW_BEGIN<code>QR_RAW_END` on stderr, unconditionally. Upstream renders terminal ASCII art (unscannable in most Windows console fonts) and emits the raw string only in a `.catch()` fallback, so without this there is nothing to render a real PNG from. One added line, no behaviour removed — the ASCII art still prints.

## 0002-group-subject-resolve.patch — real group names

`db.getChat` always fills a placeholder name `"<digits> (group)"` via `fromJid()`, so `resolveChatName` (which calls `sock.groupMetadata().subject`) never fires and every group appears as a number. This forces resolution when the name still matches the placeholder regex. Costs one extra metadata call per group whose name is unresolved, and only for groups.

## Newer upstream versions

If `npm ls -g @sjawhar/whatsapp-mcp` reports something newer than 2.4.0, try `git apply -3` and read the conflicts rather than skipping. Both changes are small enough to re-apply by hand from the diff.

## They do not survive updates

`npm update` / reinstall replaces `dist/`, silently. After any update: pairing stops working (no `QR_RAW_BEGIN` in the log) and groups turn back into numbers. Re-apply, or run `python ../pair/wa_qr_live.py --heal-patch` for 0001.

## Provenance

Cut from a clean `npm pack @sjawhar/whatsapp-mcp@2.4.0` unpack against the exact files we run in production; `git apply --check` proven on a fresh unpack, and `node --check` passes on the result.
