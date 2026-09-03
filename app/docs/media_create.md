> ## Documentation Index
> Fetch the complete documentation index at: https://speshu.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Создать задачу медиа

> Запуск асинхронной генерации изображений, видео, музыки и аудио

## О Media API

Media API запускает генерацию через единый асинхронный контракт. Вы выбираете модель, передаёте параметры в `input` и получаете `taskId`.

Используйте `taskId`, чтобы проверить статус и забрать результат через `GET /async/media/tasks/{task_id}`.

## Базовый URL

`https://speshu.ai/api/v1`

## Авторизация

Передавайте API-ключ в заголовке:

`Authorization: Bearer <SPESHU_AI_API_KEY>`

## Тело запроса

| Поле          | Тип    | Обязательное | Описание                                                   |
| ------------- | ------ | ------------ | ---------------------------------------------------------- |
| `model`       | string | Да           | ID модели из каталога `GET /media/models`.                 |
| `input`       | object | Да           | Параметры генерации. Схема зависит от модели.              |
| `sessionId`   | string | Нет          | ID сессии из `POST /media/sessions`.                       |
| `callBackUrl` | string | Нет          | URL вебхука, который будет вызван после завершения задачи. |

## Пример

```bash theme={null} theme={null}
curl -X POST "https://speshu.ai/api/v1/async/media/tasks" \
  -H "Authorization: Bearer <SPESHU_AI_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "flux-2/pro-text-to-image",
    "input": {
      "prompt": "Фотореалистичный закат над горным озером",
      "aspect_ratio": "1:1",
      "resolution": "1K"
    }
  }'
```

## Пример с сессией и вебхуком

```json theme={null} theme={null}
{
  "model": "bytedance/seedance-1.5-pro",
  "input": {
    "prompt": "Камера медленно движется над ночным городом",
    "aspect_ratio": "16:9",
    "duration": 5
  },
  "sessionId": "018f3a...",
  "callBackUrl": "https://example.com/webhooks/speshu"
}
```

## Ответ

```json theme={null} theme={null}
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "018f3b..."
  }
}
```

## Ошибки

| Код   | Описание                                |
| ----- | --------------------------------------- |
| `401` | API-ключ не передан или недействителен. |
| `402` | Недостаточно средств на балансе.        |
| `422` | Неверная модель или параметры `input`.  |
| `500` | Внутренняя ошибка сервера.              |


## OpenAPI

````yaml POST /v1/async/media/tasks
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
  /v1/async/media/tasks:
    post:
      tags:
        - Медиа
      summary: Создать media task
      operationId: MediaTasksController_create
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/MediaTaskCreateRequest'
      responses:
        '200':
          description: Задача создана
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MediaTaskCreateResponse'
        '401':
          description: Ошибка авторизации. Проверьте ключ доступа
        '402':
          description: Недостаточно средств на балансе
        '422':
          description: Ошибка в параметрах запроса
        '500':
          description: Ошибка сервера. Обратитесь к поставщику услуг
      security:
        - bearer: []
components:
  schemas:
    MediaTaskCreateRequest:
      type: object
      properties:
        model:
          type: string
          description: ID модели
          example: flux-2/pro-text-to-image
        input:
          type: object
          additionalProperties: true
          description: Параметры генерации. Схема зависит от модели.
        sessionId:
          type: string
          description: ID сессии
          example: 018f3a...
        callBackUrl:
          type: string
          description: URL вебхука после завершения задачи
          example: https://example.com/webhook
      required:
        - model
        - input
    MediaTaskCreateResponse:
      type: object
      properties:
        code:
          type: integer
          example: 200
        msg:
          type: string
          example: success
        data:
          $ref: '#/components/schemas/MediaTaskCreateData'
      required:
        - code
        - msg
        - data
    MediaTaskCreateData:
      type: object
      properties:
        taskId:
          type: string
          description: ID задачи
          example: 018f3b...
      required:
        - taskId
  securitySchemes:
    bearer:
      scheme: bearer
      bearerFormat: API Key
      type: http
      description: >-
        API ключ передаётся в заголовке: Authorization: Bearer
        <SPESHU_AI_API_KEY>

````