# Промпт для Codex

```text
Настрой WhatsApp MCP для Codex и Claude Code на этой машине. Основной runbook:
https://github.com/tonydzi/whatsapp-mcp-kit/blob/main/README.ru.md.
Сначала прочитай его и skills/whatsapp-connect/SKILL.md целиком.

Проведи RECALL локальной существующей установки и read-only инвентаризацию обоих
MCP clients, процессов/owner, data root и версий. Определи точный установленный
@sjawhar/whatsapp-mcp и различие upstream/local patched runtime. Никаких новых
socket для диагностики уже живого owner. Не печатай .env/auth/token/chat content.

Сначала спроси выбор аккаунта и принятие риска неофициального клиента, только
если это ещё не указано. Не переноси чужой auth state. Подготовь изолированный
setup и приватные каталоги. Сохрани существующие настройки и покажи минимальный
diff. Соблюдай sandbox и разрешения; не заявляй выполненным то, что заблокировано.

Один owner на аккаунт, native HTTP MCP у обоих harness. HTTP npm 2.4.0 не берёт
stdio lock: один supervisor и никаких ручных дублей, preflight не снимает гонку.
В Codex URL и
bearer_token_env_var, token из env процесса Codex. Сверь `codex mcp add --help`.
Не клади ${VAR} как якобы автоматически раскрываемое значение TOML, не передавай
token в argv или Git. В Claude используй его собственный JSON/HTTP schema.
Проверь exact CLI/envkeys npm baseline, не предполагай auto-proxy патч.

Спаривание QR только одним временным клиентом после проверки lock и наличия
исправления paired() в helper. Для phone-code смотри отдельный prompt:
поддержка requestPairingCode у Baileys не означает наличие серверного CLI флага.
QR/код являются секретами. Не отправляй их в отчёт/репозиторий.

Нужен свежий входящий nonce после начала теста и чтение через Claude и Codex.
Старый профиль, список чатов, порт или непустой creds.json не дают GREEN.
Исходящее: сначала черновик и разрешение на конкретный тест. При timeout помечай
UNKNOWN и ищи message ID/nonce до повтора. Без массовых отправок и удаления чатов.

Приёмку другой harness проверяет независимо: второй writer реализации не нужен.
Финал: installed, configured, paired, live read, live send, recipient ACK раздельно;
команды/exit codes, версии и границы покрытия, без секретов. Укажи переносимость,
перезапуск именно своего owner и возврат собственного config из backup.
```
