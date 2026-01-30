# Запуск через Docker Compose

## Требования

- Docker и Docker Compose установлены на компе/ноуте
- Файл `.env` в корне проекта с переменной `OPEN_AI_API_KEY` 
  Как выглядит `.env`:

```
OPEN_AI_API_KEY=sk-your-openai-api-key
```


Если `.env` отсутствует - нужно создать его в папке с docker-compose

## Запуск

Из корня проекта (где лежат `docker-compose.yml` и `Dockerfile`):

```bash

docker compose up -d --build

# Или если хотите видеть логи в консоли, то
docker compose up --build
```

Сервис будет доступен по адресу: **http://localhost:8000**

- Документация API: http://localhost:8000/docs  
- Корневой маршрут: http://localhost:8000/

## Остановка

```bash
docker compose down
```

## Проверка работы

```bash
# Старт интервью. Первый запрос должен выглядеть вот так:
curl -X POST http://localhost:8000/start \
  -H "Content-Type: application/json" \
  -d '{"name":"Иван","position":"Python Dev","grade":"Junior","experience":"3 месяца"}'

# Ответ на вопрос (подставьте свой session_id из ответа, который получили после отправки первого запроса!!!) Все ваши ответы в интервью будут выглядеть именно так:
curl -X POST http://localhost:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<session_id>","answer":"мой ответ"}'
```

##Финальный файл сохраняется в interview_logs/
