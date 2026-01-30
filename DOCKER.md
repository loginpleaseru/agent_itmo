# Запуск через Docker Compose

## Требования

- Docker и Docker Compose установлены на машине
- Файл `.env` в корне проекта с переменной `OPEN_AI_API_KEY` (иначе контейнер поднимется, но запросы к OpenAI будут падать)

Пример `.env`:

```
OPEN_AI_API_KEY=sk-your-openai-api-key
```

Если `.env` нет — создайте его в папке с `docker-compose.yml` и добавьте туда ключ.

## Запуск

Из корня проекта (где лежат `docker-compose.yml` и `Dockerfile`):

```bash
# Сборка и запуск в фоне
docker compose up -d --build

# Или без фона (логи в консоль)
docker compose up --build
```

Сервис будет доступен по адресу: **http://localhost:8000**

- Документация API: http://localhost:8000/docs  
- Корневой маршрут: http://localhost:8000/

## Остановка

```bash
docker compose down
```

## Не подключается к localhost:8000 (curl: Failed to connect)

**1. Проверьте, что контейнер действительно запущен:**

```bash
docker compose ps
```

Должен быть контейнер `agent_itmo` в статусе `Up`. Если статус `Exit` или контейнера нет — приложение внутри падает при старте.

**2. Посмотрите логи запуска (здесь видна ошибка):**

```bash
docker compose logs app
```

Частые причины:
- нет файла `.env` или в нём нет `OPEN_AI_API_KEY`;
- ошибка импорта (нет зависимостей, неверная версия Python);
- приложение упало при инициализации (например, из-за ключа API).

**3. Запустите без фона, чтобы сразу видеть вывод в консоли:**

```bash
docker compose down
docker compose up --build
```

Не нажимайте Ctrl+C — смотрите, что выводится при старте. После строки `Uvicorn running on http://0.0.0.0:8000` можно в другом терминале выполнить `curl http://localhost:8000/`.

**4. Проверьте порт:**

```bash
# Порт 8000 не занят другим процессом
lsof -i :8000
# или на Windows: netstat -ano | findstr :8000
```

**5. На Mac с Docker Desktop** иногда срабатывает не сразу — подождите 5–10 секунд после `docker compose up -d` и повторите `curl http://127.0.0.1:8000/`.

## Логи

**Почему не видно логов после остановки?**  
Логи живут в контейнере. Команда `docker compose down` удаляет контейнер — вместе с ним пропадают и логи.

**Как сохранить логи перед остановкой:**

```bash
# Создать папку для логов (если ещё нет)
mkdir -p logs

# Сохранить логи в файл (сделать до docker compose down)
docker compose logs app > logs/interview_$(date +%Y%m%d_%H%M%S).log

# Или просто в logs/container.log
docker compose logs app > logs/container.log
```

После этого файлы будут в папке **`./logs/`** в корне проекта.

**Смотреть логи пока контейнер запущен:**

```bash
# В реальном времени
docker compose logs -f app

# Последние 200 строк
docker compose logs --tail 200 app
```

**Остановить без удаления контейнера** (логи останутся доступны через `docker compose logs`):

```bash
docker compose stop
# Позже снова посмотреть логи:
docker compose logs app
# Запустить снова:
docker compose start
```

Если потом понадобится полностью убрать контейнеры и тома — тогда выполните `docker compose down`.

## Полезные команды

```bash
# Логи контейнера (пока он есть)
docker compose logs -f app

# Сохранить логи в файл перед down
docker compose logs app > logs/container.log

# Пересборка после изменения кода
docker compose up -d --build

# Статус сервисов
docker compose ps
```

## Проверка работы

```bash
# Старт интервью
curl -X POST http://localhost:8000/start \
  -H "Content-Type: application/json" \
  -d '{"name":"Иван","position":"Python Dev","grade":"Junior","experience":"3 месяца"}'

# Ответ на вопрос (подставьте свой session_id из ответа /start)
curl -X POST http://localhost:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<session_id>","answer":"мой ответ"}'
```
