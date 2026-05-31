# Security Policy / Политика безопасности

---

## English

### Supported Versions

BottleNeck AI is under active development. Security updates are provided for the **latest stable release** only.

| Version       | Supported          |
| ------------- | ------------------ |
| Latest stable | :white_check_mark: |
| Older releases| :x:                |

> **Note:** As a local‑first AI assistant, most security issues depend on the user’s environment. We focus on preventing code injection, privilege escalation, and unauthorised tool execution.

### Reporting a Vulnerability

Please report vulnerabilities by **opening a GitHub Issue**.

**How to report**  
1. Go to: [https://github.com/ADSFAL-US/bottleneck-ai/issues/new](https://github.com/ADSFAL-US/bottleneck-ai/issues/new)  
2. Use the title prefix `[SECURITY]` so we can prioritise it.  
3. Include:
   - Clear description of the vulnerability  
   - Steps to reproduce (proof of concept)  
   - Potential impact  
   - Your GitHub username (for credit)

**What to expect**  
- Acknowledgment within **48 hours**  
- Updates every **5–7 days** in the issue comments  
- If accepted: patch → credit → public advisory (the issue will be locked after fix)  
- If declined: explanation + mitigation recommendations

**Scope**  
Vulnerabilities in **custom tools** added by users are out of scope. Built‑in tool calling, prompt injection leading to system compromise, and sandbox bypasses are in scope.

---

## Русский

### Поддерживаемые версии

BottleNeck AI активно развивается. Обновления безопасности выпускаются только для **последней стабильной версии**.

| Версия            | Поддержка          |
| ----------------- | ------------------ |
| Последняя стабильная | :white_check_mark: |
| Старые версии     | :x:                |

> **Примечание:** Ассистент работает локально, поэтому большинство проблем безопасности зависят от окружения пользователя. Мы фокусируемся на предотвращении инъекций кода, повышения привилегий и несанкционированного вызова инструментов.

### Сообщение об уязвимости

Пожалуйста, сообщайте об уязвимостях, **открывая GitHub Issue**.

**Как сообщить**  
1. Перейдите по ссылке: [https://github.com/ADSFAL-US/bottleneck-ai/issues/new](https://github.com/ADSFAL-US/bottleneck-ai/issues/new)  
2. Добавьте в заголовок префикс `[SECURITY]` – так мы быстрее обработаем.  
3. Включите в описание:
   - Чёткое описание уязвимости  
   - Шаги для воспроизведения (proof of concept)  
   - Потенциальное влияние  
   - Ваш username на GitHub (для благодарности)

**Что вас ожидает**  
- Подтверждение в течение **48 часов**  
- Обновления каждые **5–7 дней** в комментариях к issue  
- Если уязвимость принята: исправление → благодарность → публичный advisory (issue будет закрыт и залочен после выхода патча)  
- Если отклонена: объяснение причины + рекомендации по смягчению

**Область действия**  
Уязвимости в **пользовательских инструментах** не входят в область ответственности проекта. Встроенный механизм вызова инструментов, инъекции промптов, ведущие к компрометации системы, и обходы локальной песочницы — входят.

---

*Thank you for helping keep BottleNeck AI secure / Спасибо, что помогаете делать BottleNeck AI безопаснее.*
