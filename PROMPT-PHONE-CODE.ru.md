# Промпт: привязка по номеру вместо QR

Этот комплект не поставляет готовый phone-code CLI. Промпт не обещает, что выбранный MCP-сервер уже умеет этот режим.

```text
Мне неудобен QR. Проверь существующую установку WhatsApp MCP и документацию её
точной версии. Нужен поддерживаемый способ linked-device pairing code.

Сначала read-only: версия, entrypoint, отдельный data root, текущий owner/lock,
поддерживаемые команды. Не стартуй второй socket и не удаляй state.
Baileys имеет requestPairingCode; это НЕ флаг --phone у @sjawhar/whatsapp-mcp.
Если в выбранном продукте есть готовый onboarding flow, используй именно его.
Если нет, верни PHONE_CODE_NOT_IMPLEMENTED_IN_THIS_KIT и предложи штатный QR.
Не пиши и не запускай новый Baileys-клиент без отдельного согласования scope.

В поддерживаемом flow номер передаётся приватно в международном формате цифрами
без +. Код выводится только владельцу, не попадает в общий лог/чат/Git. Владелец
вводит его на телефоне в linked devices. Для запроса дождись нужного состояния
соединения, обрабатывай creds.update, logout и restartRequired по версии API.
Непустой creds или получение pairing code до ввода не означают paired.

После ввода и передачи state единственному owner докажи свежее чтение нового
nonce. Не обещай успех по registered или наличию файла. Никаких отправок,
переавторизации соседних аккаунтов или копирования credentials между машинами.
```

Источники: [Baileys pairing code](https://github.com/WhiskeySockets/Baileys/blob/master/README.md#starting-socket-with-pairing-code) и [сервер](https://github.com/sjawhar/whatsapp-mcp-2.0).
