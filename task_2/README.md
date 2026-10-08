# Task 2 — студенческий Telegram-ассистент с локальной LLM

Telegram-бот на Python и aiogram 3.x с локальной LLM. Он отвечает на обычные вопросы и поддерживает непринуждённый разговорный тон с уместным юмором и лёгким сарказмом. Команда `/roast` генерирует короткую прожарку.

Генерация не использует OpenAI, Gemini, Groq, Ollama или платный облачный inference API: GGUF-модель запускается локально на CPU через llama.cpp. Telegram Bot API, разумеется, требует доступа в интернет.

## Архитектура

```text
Пользователь в Telegram
          │
          ▼
bot — Python, aiogram 3.x
          │  POST /session/:id/message
          ▼
opencode — OpenCode Server, локальный provider llama
          │  OpenAI-compatible API
          ▼
llama — llama.cpp server, CPU
          │
          ▼
llama/models/*.gguf
```

OpenCode Server — именно слой взаимодействия с моделью: бот создаёт OpenCode-сессию и отправляет ей сообщения через официальный session API. Конфигурация provider в `opencode/opencode.json` направляет запросы на `http://llama:8080/v1`. Все три сервиса находятся в одной Docker bridge-сети, а их порты не публикуются на хост. Межсервисные адреса используют имена Compose-сервисов, не `localhost`.

Для работы polling-боту нужен исходящий доступ в интернет к Telegram. Ответы и история чата обрабатываются локальными сервисами; OpenCode настроен без доступных модели инструментов, в том числе web search и shell.

История переписки хранится ботом в SQLite в отдельном Docker volume `bot-history` и переживает перезапуск или пересборку контейнера. База хранится локально без шифрования. В prompt модели включается только последний завершённый обмен с ограничением объёма, чтобы не раздувать запросы. OpenCode-сессии не используются как долговременная память. Команда `/clear` удаляет сохранённую историю текущего чата и пользователя.

Для этой конфигурации CPU используются 8 потоков генерации и 8 потоков обработки prompt, контекст 3072 токена и максимум 128 генерируемых токенов. Для чата в OpenCode выбран отдельный компактный агент без инструментов, а в каждом запросе инструменты отключены явно — это уменьшает накладной prompt. Ответы остаются короткими, но лимита хватает, чтобы закончить объяснение; значения можно менять в `.env`.

## Модель

По умолчанию проект ожидает [Qwen2.5-3B-Instruct Q4_K_M в формате GGUF](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF). Это instruction-модель с поддержкой русского и других языков; выбранный квантованный файл занимает около 2,1 ГБ. Веса не копируются в Docker image.

Скачайте `qwen2.5-3b-instruct-q4_k_m.gguf` из репозитория модели и положите его сюда:

```text
llama/models/qwen2.5-3b-instruct-q4_k_m.gguf
```

Если выбрали другой GGUF-файл, задайте его имя в `.env` через `LLAMA_MODEL_FILE`. Используйте инструктивную чат-модель, совместимую с llama.cpp. Для 4 ГБ RAM запуск может быть тесным: доступная память зависит от ОС, размера контекста и других контейнеров; для более комфортной работы рекомендуется 6–8 ГБ. GPU не требуется. Время генерации зависит от числа CPU-ядер и конкретного VPS.

## Требования

- Docker Engine или Docker Desktop с Docker Compose V2.
- Токен Telegram-бота, созданный через [@BotFather](https://t.me/BotFather).
- GGUF-модель в `llama/models/` (по умолчанию файл Q4_K_M, около 2,1 ГБ свободного места).
- Доступ к Docker Hub/GHCR при первом скачивании образов и к Telegram API для polling.

## Установка и запуск

Все команды ниже выполняются из каталога `task_2`.

1. Создайте файл `.env` из шаблона:

   **PowerShell**

   ```powershell
   Copy-Item .env.example .env
   ```

   **Linux/macOS**

   ```sh
   cp .env.example .env
   ```

2. Откройте `.env` и укажите токен в `BOT_TOKEN`. Не публикуйте этот файл и не добавляйте его в Git.
3. Скачайте GGUF-файл, описанный в разделе «Модель», и сохраните его в `llama/models/`. Если изменили имя файла, синхронно измените `LLAMA_MODEL_FILE` в `.env`.
4. Запустите весь проект одной командой:

   ```sh
   docker compose up -d
   ```

   Compose сам соберёт образ бота и inference-сервера, скачает образ OpenCode и запустит сервисы. Первое скачивание образов и загрузка модели могут занять время. После этого отдельных ручных запусков компонентов не требуется.

## Проверка, логи и остановка

Проверить контейнеры:

```sh
docker compose ps
```

Посмотреть логи всех сервисов:

```sh
docker compose logs -f
```

Логи конкретного сервиса:

```sh
docker compose logs -f bot
docker compose logs -f opencode
docker compose logs -f llama
```

Остановить контейнеры, сохранив именованный том данных OpenCode:

```sh
docker compose down
```

Удалить также сохранённые Docker volumes:

```sh
docker compose down -v
```

Команда с `-v` удаляет Docker volumes, включая историю чатов бота (`bot-history`) и данные OpenCode. История восстановлению не подлежит. Каталог `llama/models/` хранится в проекте и этой командой не удаляется.

## Telegram-команды

- `/start` — приветствие.
- `/help` — список команд.
- `/roast` — сгенерировать короткий roast.
- `/clear` — удалить сохранённую историю переписки текущего пользователя в этом чате.
- Любое текстовое сообщение — получить короткий ответ локальной LLM. История хранится целиком в SQLite, но модели передаётся только последний завершённый обмен.

Длинные ответы автоматически делятся на сообщения, не превышающие лимит Telegram. Если OpenCode или локальная модель недоступны, бот записывает ошибку в `logging` и отвечает пользователю понятным сообщением, не завершая polling-процесс. Время ожидания запроса ограничено `LLM_TIMEOUT_SECONDS`.

## Настройки `.env`

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `BOT_TOKEN` | обязательно задать | Токен Telegram-бота |
| `LLAMA_MODEL_FILE` | `qwen2.5-3b-instruct-q4_k_m.gguf` | Имя модели в `llama/models/` |
| `LLAMA_CONTEXT_SIZE` | `3072` | Размер контекста llama.cpp; слишком малый контекст приводит к отказу на длинных запросах |
| `LLAMA_THREADS` | `8` | Потоки CPU llama.cpp при генерации |
| `LLAMA_THREADS_BATCH` | `8` | Потоки CPU для обработки prompt; влияет на время до начала генерации |
| `LLAMA_N_PREDICT` | `128` | Верхняя граница генерируемых токенов; длинные ответы могут занять больше времени |
| `LLM_TIMEOUT_SECONDS` | `310` | Таймаут ответа OpenCode для бота; внутренний provider timeout OpenCode — 300 секунд |

Имя модели llama.cpp (`qwen2.5-3b-instruct`) согласовано с моделью по умолчанию в `opencode/opencode.json`. Если меняете ID модели или provider, обновите обе конфигурации. Не задавайте API-ключи облачных LLM: проект их не использует.

## Структура проекта

```text
task_2/
├── bot/
│   ├── bot.py
│   ├── requirements.txt
│   └── Dockerfile
├── opencode/
│   └── opencode.json
├── llama/
│   ├── Dockerfile
│   └── models/
├── docker-compose.yml
├── .env.example
└── README.md
```

Каталог модели исключён из Git через `.gitignore`; `.env` также игнорируется.

## Технологии и источники

- [Python](https://www.python.org/) и [aiogram 3](https://docs.aiogram.dev/en/latest/) — Telegram-бот.
- [OpenCode Server](https://opencode.ai/docs/server/) — HTTP session API и слой локального model provider.
- [OpenCode providers](https://opencode.ai/docs/providers/) и [конфигурация](https://opencode.ai/docs/config/) — подключение OpenAI-compatible API без облачной модели.
- [llama.cpp server](https://github.com/ggml-org/llama.cpp/tree/master/tools/server) — локальный CPU inference и OpenAI-compatible API.
- [Docker Compose](https://docs.docker.com/compose/) — запуск и внутренняя сеть сервисов.
- [Qwen2.5-3B-Instruct GGUF](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF) и [описание серии Qwen2.5](https://qwenlm.github.io/blog/qwen2.5/).

При разработке использовался AI-помощник (Copilot SDK в VS Code) для исследования архитектуры, подготовки кода и документации. Итоговая конфигурация и исходный код проверялись в рамках проекта.
