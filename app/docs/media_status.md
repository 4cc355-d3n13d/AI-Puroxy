> ## Documentation Index
> Fetch the complete documentation index at: https://speshu.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Статус задачи медиа

> Проверка состояния задачи и получение результата

Используйте этот эндпоинт, чтобы проверить задачу по `taskId`.

## Polling

Проверяйте статус с разумным интервалом:

| Тип задачи     | Интервал    |
| -------------- | ----------- |
| Изображения    | 3-5 секунд  |
| Видео          | 5-10 секунд |
| Музыка и аудио | 5-10 секунд |

## Статусы

| Статус       | Описание                    |
| ------------ | --------------------------- |
| `waiting`    | Задача ожидает обработки.   |
| `processing` | Генерация выполняется.      |
| `success`    | Результат готов.            |
| `fail`       | Задача завершилась ошибкой. |

## Пример запроса

```bash theme={null} theme={null}
curl "https://speshu.ai/api/v1/async/media/tasks/018f3b..." \
  -H "Authorization: Bearer <SPESHU_AI_API_KEY>"
```

## Ответ `success`

```json theme={null} theme={null}
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "018f3b...",
    "model": "flux-2/pro-text-to-image",
    "state": "success",
    "resultJson": "{\"resultUrls\":[\"https://...\"]}",
    "failCode": null,
    "failMsg": null,
    "createTime": 1715000000000
  }
}
```

## Поля ответа

| Поле         | Тип             | Описание                                                     |
| ------------ | --------------- | ------------------------------------------------------------ |
| `taskId`     | string          | ID задачи.                                                   |
| `model`      | string          | Модель, которая выполняла задачу.                            |
| `state`      | string          | `waiting`, `processing`, `success` или `fail`.               |
| `resultJson` | string          | JSON-строка с URL результатов. Обычно содержит `resultUrls`. |
| `failCode`   | string или null | Код ошибки при `fail`.                                       |
| `failMsg`    | string или null | Текст ошибки при `fail`.                                     |
| `createTime` | integer         | Время создания задачи в Unix milliseconds.                   |

## Пример polling

```javascript theme={null} theme={null}
async function waitForTask(taskId, apiKey) {
  while (true) {
    const response = await fetch(
      `https://speshu.ai/api/v1/async/media/tasks/${taskId}`,
      { headers: { Authorization: `Bearer ${apiKey}` } }
    );
    const body = await response.json();
    const task = body.data;

    if (task.state === 'success') {
      return JSON.parse(task.resultJson || '{}');
    }

    if (task.state === 'fail') {
      throw new Error(task.failMsg || 'Задача медиа завершилась ошибкой');
    }

    await new Promise((resolve) => setTimeout(resolve, 5000));
  }
}
```

## Ошибки

| Код   | Описание                                                    |
| ----- | ----------------------------------------------------------- |
| `401` | API-ключ не передан или недействителен.                     |
| `404` | Задача не найдена или не принадлежит текущему пользователю. |
| `422` | Неверный `taskId`.                                          |


## OpenAPI

````yaml GET /v1/async/media/tasks/{task_id}
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
  /v1/async/media/tasks/{task_id}:
    get:
      tags:
        - Медиа
      summary: Получить статус media task
      operationId: MediaTasksController_get
      parameters:
        - name: task_id
          in: path
          required: true
          schema:
            type: string
          description: ID задачи
      responses:
        '200':
          description: Статус задачи
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MediaTaskResponse'
        '401':
          description: Ошибка авторизации. Проверьте ключ доступа
        '404':
          description: Задача не найдена
        '422':
          description: Ошибка в параметрах запроса
        '500':
          description: Ошибка сервера. Обратитесь к поставщику услуг
      security:
        - bearer: []
components:
  schemas:
    MediaTaskResponse:
      type: object
      properties:
        code:
          type: integer
          example: 200
        msg:
          type: string
          example: success
        data:
          $ref: '#/components/schemas/MediaTaskData'
      required:
        - code
        - msg
        - data
    MediaTaskData:
      type: object
      properties:
        taskId:
          type: string
          description: ID задачи
          example: 018f3b...
        model:
          type: string
          description: ID модели
          example: flux-2/pro-text-to-image
        state:
          type: string
          description: Статус задачи
          enum:
            - waiting
            - processing
            - success
            - fail
          example: success
        resultJson:
          type: string
          nullable: true
          description: JSON-строка с результатами
          example: '{"resultUrls":["https://..."]}'
        failCode:
          type: string
          nullable: true
          description: Код ошибки
        failMsg:
          type: string
          nullable: true
          description: Описание ошибки
        createTime:
          type: integer
          format: int64
          description: Unix time в миллисекундах
          example: 1715000000000
      required:
        - taskId
        - model
        - state
        - createTime
  securitySchemes:
    bearer:
      scheme: bearer
      bearerFormat: API Key
      type: http
      description: >-
        API ключ передаётся в заголовке: Authorization: Bearer
        <SPESHU_AI_API_KEY>

````