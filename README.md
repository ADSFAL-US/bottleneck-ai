# BottleNeck AI

> **README in English / Русский** — Scroll down for Russian version / Прокрутите вниз для русской версии.

---

## English

### BottleNeck AI — Advanced AI Assistant for Windows

BottleNeck AI is a modular virtual AI assistant that runs locally and is invoked by long‑pressing the Win (System) key.

The project architecture allows you to easily scale it: add custom tools, inject additional system instructions, and flexibly configure agent behaviour for your tasks.

### 🚀 Key Advantages & Features

- **Full privacy and autonomy:** By default, the assistant does not send data to the network — everything is processed locally. However, you can always connect any external LLM provider.
- **Dynamic context management (token saving):** We do not stuff the local model’s context with tons of instructions for every possible scenario. The model only knows the base system prompt. If it needs specific information (e.g., the current time), it requests the needed tool instruction in one step, executes the tool, and returns the answer.
- **Maximum quality on small LLMs:** We use standard tool‑calling formats that the model already knows out‑of‑the‑box. No reinventing the wheel — this prevents loss of answer quality and keeps the prompt lean.

### 💻 System Requirements

Hardware requirements depend directly on the model you choose.

- **Default model:** `zai-org/glm-4.6v-flash`
- **VRAM:** Consumes about 8 GB for weights + a small overhead for KV‑cache.
- **Recommendation:** If you have less than 12 GB of VRAM, it is recommended to manually configure model layer offloading so that the operating system keeps a few gigabytes of free video memory.
- **Important:** The smaller the portion of model weights that fit into GPU (and the more goes into regular RAM), the slower the generation speed.

### 🛠 Quickstart

#### Prerequisites

Make sure you have the following installed:

- Git
- LM Studio (or another local backend)
- Python 3.11+

#### Installation

1. Open a terminal and navigate to the directory where you want to install the agent:
   ```bash
   cd C:/path/to/your/folder
   ```
2. Clone the repository:
   ```bash
   git clone https://github.com/ADSFAL-US/bottleneck-ai.git
   ```
3. Enter the project folder:
   ```bash
   cd ./bottleneck-ai
   ```
4. Run the project:
   ```bash
   py startup.py
   ```
   If the above command fails, try the alternative:
   ```bash
   python startup.py
   ```

### 🔍 Troubleshooting

If you encounter an error, bug, or have configuration questions:

- Check the existing Issues on GitHub — the problem may already be solved.
- If you cannot find a solution, feel free to open a new Issue. Any feedback and reports help make the project better!

---

## Русский

### BottleNeck AI — Продвинутый AI-ассистент для Windows

BottleNeck AI — это модульный виртуальный AI-ассистент, работающий локально и вызываемый длинным нажатием клавиши Win (System).

Архитектура проекта построена таким образом, что вы можете легко масштабировать его: добавлять кастомные инструменты (tools), внедрять дополнительные системные инструкции и гибко настраивать поведение агента под свои задачи.

### 🚀 Ключевые преимущества и особенности

- **Полная приватность и автономность:** По умолчанию ассистент не отправляет данные в сеть — всё обрабатывается локально. При этом вы всегда можете подключить любого внешнего LLM-провайдера.
- **Динамическое управление контекстом (Экономия токенов):** Мы не забиваем контекст локальной модели тоннами инструкций на все случаи жизни. Модель знает только базовый системный промпт. Если ей нужна специфическая информация (например, узнать время), она за один шаг запрашивает нужную инструкцию для тула, выполняет его и выдает ответ.
- **Максимальное качество на малых LLM:** Мы используем стандартные форматы вызова инструментов (Tool Calling), которые модель уже знает «из коробки». Никаких велосипедов — это предотвращает потерю качества ответов и не раздувает промпт.

### 💻 Системные требования

Требования к железу напрямую зависят от выбранной вами модели.

- **Модель по умолчанию:** `zai-org/glm-4.6v-flash`
- **VRAM (Видеопамять):** Потребляет около 8 ГБ под веса + небольшой запас под KV-кэш.
- **Рекомендация:** Если у вас меньше 12 ГБ VRAM, рекомендуется вручную настроить распределение слоев модели (offload), чтобы у операционной системы оставалось несколько гигабайт свободной видеопамяти.
- **Важно:** Чем меньший объем весов модели помещается в GPU (и уходит в обычную RAM), тем медленнее будет скорость генерации.

### 🛠 Быстрый старт (Quickstart)

#### Предварительные требования

Убедитесь, что у вас установлены:

- Git
- LM Studio (или другой локальный бэкенд)
- Python 3.11+

#### Инструкция по установке

1. Откройте терминал (консоль) и перейдите в директорию, куда хотите установить агента:
   ```bash
   cd C:/путь/до/вашей/папки
   ```
2. Склонируйте репозиторий:
   ```bash
   git clone https://github.com/ADSFAL-US/bottleneck-ai.git
   ```
3. Перейдите в папку проекта:
   ```bash
   cd ./bottleneck-ai
   ```
4. Запустите проект:
   ```bash
   py startup.py
   ```
   Если команда выше выдает ошибку, попробуйте альтернативный вариант:
   ```bash
   python startup.py
   ```

### 🔍 Решение проблем (Troubleshooting)

Если вы столкнулись с ошибкой, багом или у вас появились вопросы по настройке:

- Загляните в уже существующие Issues на GitHub — возможно, проблема уже решена.
- Если решения нет, смело открывайте новый Issue. Любая обратная связь и репорты помогают сделать проект лучше!
