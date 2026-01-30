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


## Остановка

```bash
docker compose down
```

## Использование

### Через веб-интерфейс 

1. Откройте в браузере: **http://localhost:8000/**
2. Заполните форму:
   - ФИО кандидата
   - Позиция (например, "Python Developer")
   - Грейд (Junior/Middle/Senior)
   - Опыт работы
3. Нажмите "Начать интервью"
4. Отвечайте на вопросы агента в текстовом поле
5. После завершения интервью вы увидите финальный отчёт с подробным разбором интервью



## Финальный файл сохраняется в interview_logs/ , в данной директории уже есть примеры разных вариантов работы системы в зависимости от сценария









### Через curl. Оно в принципе не надо, оставил здесь просто чтобы указать, что так тоже можно. 

```bash
# Старт интервью
curl -X POST http://localhost:8000/start \
  -H "Content-Type: application/json" \
  -d '{"name":"Иван","position":"Python Dev","grade":"Junior","experience":"3 месяца"}'

# Ответ на вопрос (подставьте свой session_id из ответа первого запроса)
curl -X POST http://localhost:8000/answer \
  -H "Content-Type: application/json" \
  -d '{"session_id":"<session_id>","answer":"мой ответ"}'
```
