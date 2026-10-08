# Task 2 — Telegram-бот с локальной LLM

Telegram-бот на Python и aiogram 3.x с локальной GGUF-моделью. Бот отвечает на обычные сообщения, поддерживает разговорный тон и предоставляет команды `/start`, `/help`, `/roast` и `/clear`.

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

История переписки хранится ботом в SQLite в отдельном Docker volume `bot-history` и переживает перезапуск или пересборку контейнера. База хранится локально без шифрования. В prompt модели включается только последний завершённый обмен с ограничением объёма. OpenCode-сессии не используются как долговременная память. Команда `/clear` удаляет сохранённую историю текущего пользователя в текущем чате.

По умолчанию заданы 8 потоков генерации, 8 потоков обработки prompt, контекст 3072 токена и максимум 128 генерируемых токенов. Для OpenCode настроен отдельный агент без инструментов, а инструменты отключаются и в запросе бота. Параметры можно изменить в `.env`; фактическая скорость зависит от процессора и нагрузки.

## Модель

По умолчанию проект настроен на [Qwen2.5-3B-Instruct Q4_K_M в формате GGUF](https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF). Файл модели занимает около 2,1 ГБ и не копируется в Docker image. Поддержка русского языка не гарантирует точность или стабильное качество ответов.

Скачайте `qwen2.5-3b-instruct-q4_k_m.gguf` из репозитория модели и положите его сюда:

```text
llama/models/qwen2.5-3b-instruct-q4_k_m.gguf
```

Если выбрали другой GGUF-файл, задайте его имя в `.env` через `LLAMA_MODEL_FILE`. Используйте инструктивную чат-модель, совместимую с llama.cpp. Для 4 ГБ RAM запуск может быть тесным; для более комфортной работы рекомендуется 6–8 ГБ. GPU не требуется.

> **Ограничение качества:** в текущей конфигурации ранее наблюдались ответы не по теме и бессвязная генерация при проверке тестовым вопросом. Поэтому модель пока нельзя считать проверенной на качество; перед реальным использованием проверьте её на своих запросах. Увеличение лимита токенов или скорости само по себе не исправляет качество модели.

## Требования

- Docker Engine или Docker Desktop с Docker Compose V2.
- Токен Telegram-бота, созданный через [@BotFather](https://t.me/BotFather).
- GGUF-модель в `llama/models/` (по умолчанию файл Q4_K_M, около 2,1 ГБ свободного места).
- Доступ к Docker Hub/GHCR при первом скачивании образов и к Telegram API для polling.

## Установка и запуск

Все команды ниже выполняются из каталога `task_2,3` (имя каталога в текущем репозитории).

**PowerShell**

```powershell
Set-Location ".\task_2,3"
```

**Linux/macOS**

```sh
cd "task_2,3"
```

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

   Compose сам соберёт образы бота и inference-сервера, скачает образ OpenCode и запустит сервисы. При первом запуске загрузка модели в память может занять время. Отдельно запускать компоненты не нужно.

5. Проверьте состояние контейнеров и дождитесь, пока llama.cpp закончит загрузку модели:

   ```sh
   docker compose ps
   docker compose logs --tail 50 llama
   ```

   В логе llama.cpp должно появиться сообщение `model loaded`. Только после этого отправляйте боту сообщения.

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

Длинные ответы автоматически делятся на сообщения, не превышающие лимит Telegram. Если OpenCode или локальная модель недоступны, бот записывает ошибку в `logging` и отвечает пользователю сообщением об ошибке; polling-процесс при этом продолжает работу. Время ожидания запроса ограничено `LLM_TIMEOUT_SECONDS`.

## Настройки `.env`

| Переменная | По умолчанию | Назначение |
| --- | --- | --- |
| `BOT_TOKEN` | обязательно задать | Токен Telegram-бота |
| `LLAMA_MODEL_FILE` | `qwen2.5-3b-instruct-q4_k_m.gguf` | Имя модели в `llama/models/` |
| `LLAMA_CONTEXT_SIZE` | `3072` | Размер контекста llama.cpp; слишком малый контекст приводит к отказу на длинных запросах |
| `LLAMA_THREADS` | `8` | Потоки CPU llama.cpp при генерации |
| `LLAMA_THREADS_BATCH` | `8` | Потоки CPU для обработки prompt; влияет на время до начала генерации |
| `LLAMA_N_PREDICT` | `128` | Верхняя граница генерируемых токенов; увеличение может увеличить задержку ответа |
| `LLM_TIMEOUT_SECONDS` | `310` | Таймаут ответа OpenCode для бота; внутренний provider timeout OpenCode — 300 секунд |

Имя модели llama.cpp (`qwen2.5-3b-instruct`) согласовано с моделью по умолчанию в `opencode/opencode.json`. Если меняете ID модели или provider, обновите обе конфигурации. Не задавайте API-ключи облачных LLM: проект их не использует.

## Структура проекта

```text
task_2,3/
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

При разработке использовался AI-помощник (Copilot SDK в VS Code) для исследования архитектуры, подготовки кода и документации. Контейнеры и конфигурация запуска проверялись локально; качество ответов модели не подтверждено и требует отдельного тестирования.
