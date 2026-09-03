> ## Documentation Index
> Fetch the complete documentation index at: https://speshu.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Anthropic Messages API

> Anthropic-совместимый endpoint для сообщений и streaming

SpeShu.AI поддерживает Anthropic-compatible `POST /v1/messages`. Если ваш клиент уже работает с Anthropic Messages API, замените `base_url` и используйте API-ключ SpeShu.AI.

## Базовый URL

`https://speshu.ai/api/v1`

## Авторизация

Поддерживаются оба варианта:

`x-api-key: <SPESHU_AI_API_KEY>`

`Authorization: Bearer <SPESHU_AI_API_KEY>`

Также передавайте версию API:

`anthropic-version: 2023-06-01`

## Синхронный запрос

```bash theme={null} theme={null}
curl "https://speshu.ai/api/v1/messages" \
  -H "x-api-key: <SPESHU_AI_API_KEY>" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic/claude-sonnet-4.6",
    "max_tokens": 1024,
    "messages": [
      { "role": "user", "content": "Привет!" }
    ]
  }'
```

## Ответ `200`

```json theme={null} theme={null}
{
  "id": "msg_abc123",
  "type": "message",
  "role": "assistant",
  "content": [
    {
      "type": "text",
      "text": "Привет! Чем помочь?"
    }
  ],
  "model": "anthropic/claude-sonnet-4.6",
  "stop_reason": "end_turn",
  "stop_sequence": null,
  "usage": {
    "input_tokens": 10,
    "output_tokens": 8
  }
}
```

## Streaming

Установите `stream: true`, чтобы получать ответ через Server-Sent Events.

```bash theme={null} theme={null}
curl "https://speshu.ai/api/v1/messages" \
  -H "x-api-key: <SPESHU_AI_API_KEY>" \
  -H "anthropic-version: 2023-06-01" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic/claude-sonnet-4.6",
    "max_tokens": 1024,
    "stream": true,
    "messages": [
      { "role": "user", "content": "Посчитай до 3" }
    ]
  }'
```

Ответ приходит как `text/event-stream`:

```text theme={null} theme={null}
event: message_start
data: {"type":"message_start","message":{"id":"msg_abc","type":"message","role":"assistant","content":[],"model":"anthropic/claude-sonnet-4.6","stop_reason":null,"stop_sequence":null,"usage":{"input_tokens":8,"output_tokens":1}}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"1, 2, 3"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn","stop_sequence":null},"usage":{"output_tokens":5}}

event: message_stop
data: {"type":"message_stop"}
```

Клиент должен корректно обрабатывать неизвестные event-типы. Anthropic может добавлять новые события без изменения основного контракта.

## Параметры

| Параметр         | Тип              | Обязательный | Описание                                                |
| ---------------- | ---------------- | ------------ | ------------------------------------------------------- |
| `model`          | string           | Да           | ID модели. Например, `anthropic/claude-sonnet-4.6`.     |
| `messages`       | array            | Да           | История сообщений с `role` и `content`.                 |
| `max_tokens`     | integer          | Да           | Максимум токенов в ответе.                              |
| `stream`         | boolean          | Нет          | Включает SSE streaming. По умолчанию `false`.           |
| `temperature`    | number           | Нет          | Температура генерации.                                  |
| `top_p`          | number           | Нет          | Nucleus sampling.                                       |
| `top_k`          | integer          | Нет          | Top-K sampling.                                         |
| `stop_sequences` | array            | Нет          | Пользовательские stop sequences.                        |
| `system`         | string или array | Нет          | Системная инструкция.                                   |
| `thinking`       | object           | Нет          | Настройки thinking. Например, `{ "type": "adaptive" }`. |
| `tools`          | array            | Нет          | Описание инструментов для tool use.                     |
| `tool_choice`    | object           | Нет          | Стратегия выбора инструмента.                           |

## Python SDK

```python theme={null} theme={null}
from anthropic import Anthropic

client = Anthropic(
    api_key="<SPESHU_AI_API_KEY>",
    base_url="https://speshu.ai/api/v1",
)

message = client.messages.create(
    model="anthropic/claude-sonnet-4.6",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Привет!"}],
)

print(message.content[0].text)
```

## Ошибки

Ошибки возвращаются в Anthropic-style формате:

```json theme={null} theme={null}
{
  "error": {
    "type": "api_error",
    "message": "model is required"
  }
}
```

| HTTP status | Описание                                |
| ----------- | --------------------------------------- |
| `400`       | Неверный JSON или параметры запроса.    |
| `401`       | API-ключ не передан или недействителен. |
| `402`       | Недостаточно средств на балансе.        |
| `429`       | Превышен лимит запросов.                |
| `500`       | Внутренняя ошибка сервера.              |
| `502`       | Провайдер временно недоступен.          |


## OpenAPI

````yaml POST /v1/messages
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
  /v1/messages:
    post:
      tags:
        - Текстовая генерация
      summary: Создать сообщение Anthropic Messages API
      operationId: AnthropicMessagesController_create
      parameters:
        - name: anthropic-version
          in: header
          required: true
          schema:
            type: string
            example: '2023-06-01'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/AnthropicMessagesRequest'
      responses:
        '200':
          description: >-
            Сообщение создано. При stream=true ответ приходит как
            text/event-stream.
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AnthropicMessagesResponse'
            text/event-stream:
              schema:
                type: string
        '400':
          description: Неверный запрос
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AnthropicErrorResponse'
        '401':
          description: Ошибка авторизации
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AnthropicErrorResponse'
        '402':
          description: Недостаточно средств на балансе
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AnthropicErrorResponse'
        '429':
          description: Превышен лимит запросов
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AnthropicErrorResponse'
        '500':
          description: Внутренняя ошибка сервера
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AnthropicErrorResponse'
        '502':
          description: Провайдер временно недоступен
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/AnthropicErrorResponse'
      security:
        - bearer: []
        - xApiKey: []
components:
  schemas:
    AnthropicMessagesRequest:
      type: object
      additionalProperties: true
      properties:
        model:
          type: string
          example: anthropic/claude-sonnet-4.6
        messages:
          type: array
          items:
            $ref: '#/components/schemas/AnthropicMessageParam'
        max_tokens:
          type: integer
          example: 1024
        stream:
          type: boolean
          default: false
        temperature:
          type: number
          example: 1
        top_p:
          type: number
          example: 1
        top_k:
          type: integer
          example: 40
        stop_sequences:
          type: array
          items:
            type: string
        system:
          oneOf:
            - type: string
              example: You are a helpful assistant.
            - type: array
              items:
                $ref: '#/components/schemas/AnthropicContentBlock'
        thinking:
          type: object
          additionalProperties: true
          example:
            type: adaptive
        tools:
          type: array
          items:
            type: object
            additionalProperties: true
        tool_choice:
          type: object
          additionalProperties: true
      required:
        - model
        - messages
        - max_tokens
    AnthropicMessagesResponse:
      type: object
      properties:
        id:
          type: string
          example: msg_abc123
        type:
          type: string
          example: message
        role:
          type: string
          example: assistant
        content:
          type: array
          items:
            $ref: '#/components/schemas/AnthropicContentBlock'
        model:
          type: string
          example: anthropic/claude-sonnet-4.6
        stop_reason:
          type: string
          nullable: true
          example: end_turn
        stop_sequence:
          type: string
          nullable: true
        usage:
          type: object
          properties:
            input_tokens:
              type: integer
              example: 10
            output_tokens:
              type: integer
              example: 8
      required:
        - id
        - type
        - role
        - content
        - model
    AnthropicErrorResponse:
      type: object
      properties:
        error:
          type: object
          properties:
            type:
              type: string
              example: api_error
            message:
              type: string
              example: model is required
          required:
            - type
            - message
      required:
        - error
    AnthropicMessageParam:
      type: object
      additionalProperties: true
      properties:
        role:
          type: string
          enum:
            - user
            - assistant
          example: user
        content:
          oneOf:
            - type: string
              example: Привет!
            - type: array
              items:
                $ref: '#/components/schemas/AnthropicContentBlock'
      required:
        - role
        - content
    AnthropicContentBlock:
      type: object
      additionalProperties: true
      properties:
        type:
          type: string
          example: text
        text:
          type: string
          example: Привет! Чем помочь?
  securitySchemes:
    bearer:
      scheme: bearer
      bearerFormat: API Key
      type: http
      description: >-
        API ключ передаётся в заголовке: Authorization: Bearer
        <SPESHU_AI_API_KEY>
    xApiKey:
      type: apiKey
      in: header
      name: x-api-key
      description: API ключ SpeShu.AI для Anthropic-compatible клиентов

````