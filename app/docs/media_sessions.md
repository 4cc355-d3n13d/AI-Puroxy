> ## Documentation Index
> Fetch the complete documentation index at: https://speshu.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Создать медиа сессию

> Группировка связанных задач медиа в одну сессию

Сессия помогает объединять связанные задачи. Например, один проект с несколькими изображениями, видео и аудио.

## Тело запроса

| Поле    | Тип    | Обязательное | Описание         |
| ------- | ------ | ------------ | ---------------- |
| `title` | string | Нет          | Название сессии. |

## Пример

```bash theme={null} theme={null}
curl -X POST "https://speshu.ai/api/v1/media/sessions" \
  -H "Authorization: Bearer <SPESHU_AI_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Запуск кампании"
  }'
```

## Ответ

```json theme={null} theme={null}
{
  "code": 200,
  "msg": "success",
  "data": {
    "sessionId": "018f3a...",
    "title": "Запуск кампании"
  }
}
```

Передайте `sessionId` в `POST /async/media/tasks`, чтобы привязать задачу к сессии.


## OpenAPI

````yaml POST /v1/media/sessions
openapi: 3.0.0
info:
  title: SpeShu.AI API
  description: AI агрегатор — унифицированный доступ к сотням AI моделей
  version: '1.0'
  contact: {}
servers:
  - url: https://speshu.ai/api
    description: Production
security:
  - bearer: []
tags: []
paths:
  /v1/media/sessions:
    post:
      tags:
        - Медиа
      summary: Создать media session
      operationId: MediaSessionsController_create
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MediaSessionCreateRequest'
      responses:
        '200':
          description: Сессия создана
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MediaSessionResponse'
        '401':
          description: Ошибка авторизации. Проверьте ключ доступа
        '500':
          description: Ошибка сервера. Обратитесь к поставщику услуг
      security:
        - bearer: []
components:
  schemas:
    MediaSessionCreateRequest:
      type: object
      properties:
        title:
          type: string
          description: Название сессии
          example: My Project
    MediaSessionResponse:
      type: object
      properties:
        code:
          type: integer
          example: 200
        msg:
          type: string
          example: success
        data:
          $ref: '#/components/schemas/MediaSessionData'
      required:
        - code
        - msg
        - data
    MediaSessionData:
      type: object
      properties:
        sessionId:
          type: string
          description: ID сессии
          example: 018f3a...
        title:
          type: string
          description: Название сессии
          example: My Project
      required:
        - sessionId
  securitySchemes:
    bearer:
      scheme: bearer
      bearerFormat: API Key
      type: http
      description: >-
        API ключ передаётся в заголовке: Authorization: Bearer
        <SPESHU_AI_API_KEY>

````