> ## Documentation Index
> Fetch the complete documentation index at: https://speshu.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Список задач медиа

> Получение истории задач генерации медиа

Эндпоинт возвращает задачи текущего пользователя с пагинацией и фильтрами.

## Query параметры

| Параметр | Тип     | По умолчанию | Описание                                                       |
| -------- | ------- | ------------ | -------------------------------------------------------------- |
| `limit`  | integer | `20`         | Количество задач. Максимум `100`.                              |
| `offset` | integer | `0`          | Смещение для пагинации.                                        |
| `status` | string  | -            | Фильтр по статусу: `waiting`, `processing`, `success`, `fail`. |
| `model`  | string  | -            | Фильтр по ID модели.                                           |
| `order`  | string  | `desc`       | Сортировка: `asc` или `desc`.                                  |

## Пример

```bash theme={null} theme={null}
curl "https://speshu.ai/api/v1/async/media/tasks?limit=10&status=success" \
  -H "Authorization: Bearer <SPESHU_AI_API_KEY>"
```

## Ответ

```json theme={null} theme={null}
{
  "code": 200,
  "msg": "success",
  "data": {
    "items": [
      {
        "taskId": "018f3b...",
        "model": "flux-2/pro-text-to-image",
        "state": "success",
        "resultJson": "{\"resultUrls\":[\"https://...\"]}",
        "failCode": null,
        "failMsg": null,
        "createTime": 1715000000000
      }
    ],
    "total": 42
  }
}
```

Объекты в `items` имеют тот же формат, что и ответ `GET /async/media/tasks/{task_id}`.


## OpenAPI

````yaml GET /v1/async/media/tasks
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
    get:
      tags:
        - Медиа
      summary: Получить список media tasks
      operationId: MediaTasksController_list
      parameters:
        - name: limit
          in: query
          required: false
          schema:
            type: integer
            default: 20
            maximum: 100
        - name: offset
          in: query
          required: false
          schema:
            type: integer
            default: 0
        - name: status
          in: query
          required: false
          schema:
            type: string
            enum:
              - waiting
              - processing
              - success
              - fail
        - name: model
          in: query
          required: false
          schema:
            type: string
        - name: order
          in: query
          required: false
          schema:
            type: string
            enum:
              - asc
              - desc
            default: desc
      responses:
        '200':
          description: Список задач
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MediaTaskListResponse'
        '401':
          description: Ошибка авторизации. Проверьте ключ доступа
        '500':
          description: Ошибка сервера. Обратитесь к поставщику услуг
      security:
        - bearer: []
components:
  schemas:
    MediaTaskListResponse:
      type: object
      properties:
        code:
          type: integer
          example: 200
        msg:
          type: string
          example: success
        data:
          $ref: '#/components/schemas/MediaTaskListData'
      required:
        - code
        - msg
        - data
    MediaTaskListData:
      type: object
      properties:
        items:
          type: array
          items:
            $ref: '#/components/schemas/MediaTaskData'
        total:
          type: integer
          example: 42
      required:
        - items
        - total
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