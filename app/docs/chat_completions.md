> ## Documentation Index
> Fetch the complete documentation index at: https://speshu.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Запрос чату

> Основной эндпоинт для генерации текста и диалогов

Поддерживает текстовые диалоги, мультимодальные запросы (текст + изображения + аудио + видео + файлы), вызов функций и потоковую передачу.

## Возможности

* **Агрегация провайдеров** — автоматический выбор оптимального провайдера
* **Биллинг в рублях** — точный учет стоимости
* **Reasoning Tokens** — поддержка моделей с рассуждениями
* **Streaming** — потоковая передача через SSE
* **Tool Calling** — вызов внешних функций
* **Мультимодальность** — обработка текста, изображений, аудио, видео и файлов

## Параметры запроса

### Обязательные

| Параметр | Тип    | Описание                                                  |
| -------- | ------ | --------------------------------------------------------- |
| `model`  | string | ID модели из [списка моделей](/docs/api-reference/models/list) |

### Контент

| Параметр   | Тип    | Описание                                         |
| ---------- | ------ | ------------------------------------------------ |
| `messages` | array  | Массив сообщений диалога (рекомендуется)         |
| `prompt`   | string | Простой текстовый промпт (альтернатива messages) |

### Параметры генерации

| Параметр                | Тип           | По умолчанию | Описание                                        |
| ----------------------- | ------------- | ------------ | ----------------------------------------------- |
| `max_tokens`            | integer       | Без лимита   | Максимум токенов в ответе                       |
| `max_completion_tokens` | integer       | Без лимита   | Альтернатива max\_tokens                        |
| `temperature`           | float (0-2)   | 1.0          | Температура (0=детерминированный, 2=креативный) |
| `top_p`                 | float (0-1)   | 1.0          | Nucleus sampling                                |
| `top_k`                 | integer       | —            | Top-K sampling                                  |
| `frequency_penalty`     | float (-2..2) | 0            | Штраф за повторение слов                        |
| `presence_penalty`      | float (-2..2) | 0            | Штраф за повторение токенов                     |
| `stop`                  | string/array  | —            | Стоп-последовательности                         |
| `seed`                  | integer       | —            | Seed для воспроизводимости                      |

### Специальные возможности

| Параметр             | Тип           | Описание                                                 |
| -------------------- | ------------- | -------------------------------------------------------- |
| `stream`             | boolean       | Включить streaming (SSE)                                 |
| `reasoning`          | object        | Настройки reasoning tokens                               |
| `tools`              | array         | Доступные функции для вызова                             |
| `tool_choice`        | string/object | Выбор инструмента: "none", "auto", "required"            |
| `response_format`    | object        | Формат ответа: text, json\_object, json\_schema, grammar |
| `web_search_options` | object        | Встроенный веб-поиск                                     |
| `provider`           | object        | Конфигурация роутинга по провайдерам                     |
| `plugins`            | array         | Подключение плагинов                                     |
| `modalities`         | array         | Выходные модальности: "text", "image", "audio"           |
| `audio`              | object        | Конфигурация аудио-вывода (voice, format)                |
| `user`               | string        | Идентификатор конечного пользователя                     |

## Структура сообщений

### Базовый формат

```json theme={null} theme={null}
{
  "role": "user|assistant|system|developer|tool",
  "content": "Текст сообщения"
}
```

### Мультимодальные сообщения

```json theme={null} theme={null}
{
  "role": "user",
  "content": [
    {"type": "text", "text": "Что на этом изображении?"},
    {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
  ]
}
```

### Другие типы контента

```json theme={null} theme={null}
// Аудио вход
{"type": "input_audio", "input_audio": {"data": "base64...", "format": "mp3"}}

// Видео вход
{"type": "video_url", "video_url": {"url": "https://example.com/video.mp4"}}

// Файл
{"type": "file", "file": {"filename": "doc.pdf", "file_data": "data:application/pdf;base64,..."}}
```

### Системные сообщения с кешированием

```json theme={null} theme={null}
{
  "role": "system",
  "content": [
    {
      "type": "text",
      "text": "Длинная системная инструкция...",
      "cache_control": {"type": "ephemeral"}
    }
  ]
}
```

## Примеры

<CodeGroup>
  ```bash cURL theme={null} theme={null}
  curl -X POST "https://speshu.ai/api/v1/chat/completions" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
  "model": "openai/gpt-5.5",
  "messages": [{"role": "user", "content": "Привет!"}]
  }'
  ```

  ```python Python theme={null} theme={null}
  from openai import OpenAI

  client = OpenAI(
  base_url="https://speshu.ai/api/v1",
  api_key="YOUR_API_KEY"
  )

  response = client.chat.completions.create(
  model="anthropic/claude-sonnet-4.6",
  messages=[{"role": "user", "content": "Объясни квантовую механику"}]
  )

  print(response.choices[0].message.content)
  print(f"Стоимость: {response.usage.cost_rub} руб.")
  ```

  ```typescript TypeScript theme={null} theme={null}
  import OpenAI from 'openai';

  const client = new OpenAI({
  baseURL: 'https://speshu.ai/api/v1',
  apiKey: 'YOUR_API_KEY'
  });

  const response = await client.chat.completions.create({
  model: 'openai/gpt-5.5',
  messages: [{role: 'user', content: 'Напиши историю'}],
  stream: true
  });

  for await (const chunk of response) {
  process.stdout.write(chunk.choices[0]?.delta?.content || '');
  }
  ```
</CodeGroup>

## Ответ

### Успешный ответ (200)

```json theme={null} theme={null}
{
  "id": "gen_581761234567890123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "openai/gpt-5.5",
  "provider": "OpenAI",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Текст ответа"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 25,
    "completion_tokens": 150,
    "total_tokens": 175,
    "cost_rub": 0.04131306,
    "cost": 0.04131306,
    "prompt_tokens_details": {
      "cached_tokens": 0
    },
    "completion_tokens_details": {
      "reasoning_tokens": 0
    }
  }
}
```

### Streaming (SSE)

При `stream: true` ответ приходит в формате Server-Sent Events:

```
data: {"id":"gen_123","object":"chat.completion.chunk","created":1703001234,"model":"openai/gpt-5.5","choices":[{"index":0,"delta":{"role":"assistant","content":"Привет"}}]}

data: {"id":"gen_123","object":"chat.completion.chunk","created":1703001234,"model":"openai/gpt-5.5","choices":[{"index":0,"delta":{"content":" мир"}}]}

data: {"id":"gen_123","object":"chat.completion.chunk","created":1703001234,"model":"openai/gpt-5.5","choices":[],"usage":{"prompt_tokens":10,"completion_tokens":20,"total_tokens":30,"cost_rub":0.015,"cost":0.015}}

data: [DONE]
```

## Tool Calling

### Определение функций

```json theme={null} theme={null}
{
  "tools": [{
    "type": "function",
    "function": {
      "name": "get_weather",
      "description": "Получить текущую погоду",
      "parameters": {
        "type": "object",
        "properties": {
          "city": {"type": "string"}
        },
        "required": ["city"]
      }
    }
  }],
  "tool_choice": "auto"
}
```

### Ответ модели с вызовом функции

```json theme={null} theme={null}
{
  "tool_calls": [{
    "id": "call_123",
    "function": {"name": "get_weather", "arguments": "{\"city\": \"Москва\"}"}
  }]
}
```

## Response Format

### JSON Schema (структурированный вывод)

```json theme={null} theme={null}
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "my_schema",
      "schema": {
        "type": "object",
        "properties": {
          "answer": {"type": "string"},
          "confidence": {"type": "number"}
        }
      },
      "strict": true
    }
  }
}
```

Поддерживаемые типы: `text`, `json_object`, `json_schema`, `grammar` (GBNF).

## Reasoning Tokens

Для моделей с рассуждениями (o1, o3, DeepSeek-R1 и другие):

```json theme={null} theme={null}
{
  "model": "openai/o1-preview",
  "messages": [{"role": "user", "content": "Реши: 2x + 5 = 13"}],
  "reasoning": {
    "effort": "high",
    "max_tokens": 1000
  }
}
```

### Параметры reasoning

| Параметр     | Тип     | Описание                                                |
| ------------ | ------- | ------------------------------------------------------- |
| `effort`     | string  | Уровень усилий: xhigh, high, medium, low, minimal, none |
| `max_tokens` | integer | Максимум токенов на рассуждения                         |
| `summary`    | string  | Детализация: auto, concise, detailed                    |
| `enabled`    | boolean | Включить/выключить рассуждения                          |
| `exclude`    | boolean | Скрыть рассуждения из ответа                            |


## OpenAPI

````yaml /openapi.json POST /v1/chat/completions
openapi: 3.0.0
info:
  title: SpeShu.AI API
  description: AI агрегатор — унифицированный доступ к сотням AI моделей
  version: '1.0'
  contact: {}
servers:
  - url: https://speshu.ai/api/v1
    description: Production API
security:
  - bearer: []
tags: []
paths:
  /v1/chat/completions:
    post:
      tags:
        - Чат
      summary: Создать chat completion
      operationId: ChatController_createChatCompletion[1]
      parameters: []
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/ChatCompletionRequestDto'
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ChatCompletionPresenter'
        '401':
          description: Ошибка авторизации. Проверьте ключ доступа
        '403':
          description: Ошибка доступа. Проверьте права доступа ключа
        '500':
          description: Ошибка сервера. Обратитесь к поставщику услуг
      security:
        - bearer: []
components:
  schemas:
    ChatCompletionRequestDto:
      type: object
      properties:
        model:
          type: string
          description: Идентификатор модели для использования
          example: openai/gpt-4o
        prompt:
          type: string
          description: >-
            Текстовый промпт (альтернатива messages). Если указан, будет
            преобразован в messages с role=user
          example: Напиши стихотворение про кота
        messages:
          description: >-
            Массив сообщений для отправки модели (обязателен если не указан
            prompt)
          example:
            - role: system
              content: Ты полезный ассистент
            - role: user
              content: Привет! Как дела?
          type: array
          items:
            $ref: '#/components/schemas/MessageDto'
        max_tokens:
          type: number
          description: Максимальное количество токенов для генерации
          example: 1000
          minimum: 1
        max_completion_tokens:
          type: number
          description: >-
            Максимальное количество токенов для completion (альтернатива
            max_tokens)
          example: 1000
          minimum: 1
        temperature:
          type: number
          description: >-
            Температура сэмплинга (0-2). Более высокие значения делают вывод
            более случайным
          example: 1
          minimum: 0
          maximum: 2
        top_p:
          type: number
          description: 'Nucleus sampling: вероятностная масса для рассмотрения (0-1)'
          example: 1
          minimum: 0
          maximum: 1
        frequency_penalty:
          type: number
          description: Штраф за частоту использования токенов (-2 до 2)
          example: 0
          minimum: -2
          maximum: 2
        presence_penalty:
          type: number
          description: Штраф за присутствие токенов (-2 до 2)
          example: 0
          minimum: -2
          maximum: 2
        response_format:
          type: object
          description: Формат ответа модели
        provider:
          description: Настройки провайдера для роутинга и фильтрации
          allOf:
            - $ref: '#/components/schemas/ProviderDto'
        tools:
          description: Определения инструментов (tools) для function calling
          type: array
          items:
            $ref: '#/components/schemas/ToolDefinitionDto'
        tool_choice:
          type: object
          description: 'Выбор инструмента: none, auto, required или named function'
          example: auto
        reasoning:
          description: Настройки reasoning для reasoning моделей
          allOf:
            - $ref: '#/components/schemas/ReasoningDto'
        plugins:
          type: array
          description: Плагины для расширения функциональности
        web_search_options:
          description: Настройки встроенного веб-поиска (для моделей с нативной поддержкой)
          allOf:
            - $ref: '#/components/schemas/WebSearchOptionsDto'
        user:
          type: string
          description: >-
            Уникальный идентификатор конечного пользователя для отслеживания и
            предотвращения злоупотреблений
          example: user-123
        stop:
          description: Последовательности, при которых модель прекращает генерацию
          example:
            - |+

          oneOf:
            - type: string
            - type: array
              items:
                type: string
        seed:
          type: number
          description: Seed для детерминированной генерации (best-effort)
          example: 42
        'n':
          type: number
          description: Количество вариантов ответа (1-10)
          example: 1
          minimum: 1
          maximum: 10
        stream:
          type: boolean
          description: Включить потоковую передачу ответа
          example: false
        logprobs:
          type: boolean
          description: Возвращать log probabilities для output токенов
          example: false
        top_logprobs:
          type: number
          description: >-
            Количество наиболее вероятных токенов для возврата (0-20). Требует
            logprobs: true
          example: 5
          minimum: 0
          maximum: 20
        logit_bias:
          type: object
          description: Смещение вероятностей токенов по их ID (-100 до 100)
          example:
            '50256': -100
        parallel_tool_calls:
          type: boolean
          description: Разрешить параллельный вызов нескольких tools
          example: true
        image_config:
          type: object
          description: Настройки обработки изображений
          example:
            quality: high
            size: 512
        modalities:
          type: array
          description: Типы вывода модели
          example:
            - text
            - audio
          items:
            type: string
            enum:
              - text
              - image
              - audio
        audio:
          type: object
          description: >-
            Настройки аудио выхода для моделей с поддержкой аудио (gpt-audio и
            др.)
          properties:
            voice:
              type: string
              example: alloy
              description: Голос для генерации аудио
            format:
              type: string
              example: pcm16
              description: Формат аудио
      required:
        - model
        - messages
    ChatCompletionPresenter:
      type: object
      properties:
        id:
          type: string
          description: Уникальный идентификатор генерации
          example: gen_581761234567890123
        object:
          type: string
          description: Тип объекта
          example: chat.completion
        created:
          type: number
          description: Временная метка создания (Unix timestamp)
          example: 1703001234
        model:
          type: string
          description: ID модели, которая сгенерировала ответ
          example: openai/gpt-4o
        choices:
          description: Массив вариантов ответа
          type: array
          items:
            $ref: '#/components/schemas/ChoicePresenter'
        system_fingerprint:
          type: string
          description: System fingerprint от провайдера
          example: fp_29330a9688
        usage:
          description: Информация об использовании токенов
          allOf:
            - $ref: '#/components/schemas/UsagePresenter'
      required:
        - id
        - object
        - created
        - model
        - choices
    MessageDto:
      type: object
      properties:
        role:
          type: string
          description: Роль отправителя сообщения
          enum:
            - user
            - assistant
            - system
            - developer
            - tool
          example: user
        content:
          type: object
          description: >-
            Содержимое сообщения (строка, массив частей контента или null для
            assistant с tool_calls)
          example: Привет, как дела?
          nullable: true
        name:
          type: string
          description: Имя отправителя (опционально)
          example: Иван
        tool_call_id:
          type: string
          description: ID вызова инструмента (только для role=tool)
          example: call_abc123
        tool_calls:
          description: Массив вызовов инструментов (только для role=assistant)
          type: array
          items:
            $ref: '#/components/schemas/ToolCallDto'
        refusal:
          type: object
          description: >-
            Текст отказа модели от выполнения запроса (только для
            role=assistant)
          example: Я не могу помочь с этим запросом
          nullable: true
        reasoning:
          type: object
          description: Reasoning текст для моделей с reasoning (только для role=assistant)
          example: Для решения этой задачи мне нужно...
          nullable: true
        annotations:
          type: array
          description: >-
            Аннотации из ответа провайдера (для кэширования парсинга PDF и
            других документов)
          items:
            type: object
      required:
        - role
        - content
    ProviderDto:
      type: object
      properties:
        allow_fallbacks:
          type: boolean
          description: Разрешить использование резервных провайдеров
          example: true
        order:
          description: Упорядоченный список slug провайдеров для использования
          example:
            - OpenAI
            - Anthropic
          type: array
          items:
            type: string
        only:
          description: Список разрешенных slug провайдеров
          example:
            - OpenAI
            - Google
          type: array
          items:
            type: string
        ignore:
          description: Список игнорируемых slug провайдеров
          example:
            - DeepInfra
          type: array
          items:
            type: string
        sort:
          type: string
          description: Критерий сортировки провайдеров
          enum:
            - price
            - throughput
            - latency
          example: price
        max_price:
          description: Максимальные цены для запроса
          allOf:
            - $ref: '#/components/schemas/ProviderMaxPriceDto'
    ToolDefinitionDto:
      type: object
      properties:
        type:
          type: string
          description: Тип инструмента
          example: function
          enum:
            - function
        function:
          description: Определение функции
          allOf:
            - $ref: '#/components/schemas/ToolFunctionDto'
      required:
        - type
        - function
    ReasoningDto:
      type: object
      properties:
        effort:
          type: string
          description: Уровень усилий reasoning модели
          enum:
            - xhigh
            - high
            - medium
            - low
            - minimal
            - none
          example: medium
        summary:
          type: string
          description: Уровень детализации резюме reasoning
          enum:
            - auto
            - concise
            - detailed
            - none
          example: auto
        enabled:
          type: boolean
          description: >-
            Включить/выключить reasoning. По умолчанию определяется из effort
            или max_tokens
          example: true
        max_tokens:
          type: number
          description: Максимальное количество токенов для reasoning (стиль Anthropic)
          example: 2000
        exclude:
          type: boolean
          description: >-
            Скрыть reasoning из ответа (модель будет использовать reasoning, но
            не вернёт его)
          example: false
    WebSearchOptionsDto:
      type: object
      properties:
        search_context_size:
          type: string
          description: Размер контекста поиска для моделей со встроенным веб-поиском
          enum:
            - low
            - medium
            - high
          example: medium
    ChoicePresenter:
      type: object
      properties:
        index:
          type: number
          description: Индекс выбора в массиве choices
          example: 0
        message:
          description: Сообщение от модели
          allOf:
            - $ref: '#/components/schemas/MessagePresenter'
        finish_reason:
          type: string
          description: Причина завершения генерации
          example: stop
          enum:
            - stop
            - length
            - content_filter
            - error
            - tool_calls
          nullable: true
        reasoning_details:
          type: array
          description: Детали reasoning процесса (для reasoning моделей)
        logprobs:
          description: Log probabilities для токенов
          nullable: true
          allOf:
            - $ref: '#/components/schemas/ChatMessageTokenLogprobsPresenter'
      required:
        - index
        - message
        - finish_reason
    UsagePresenter:
      type: object
      properties:
        prompt_tokens:
          type: number
          description: Количество токенов в промпте
          example: 10
        completion_tokens:
          type: number
          description: Количество токенов в ответе
          example: 50
        total_tokens:
          type: number
          description: Общее количество токенов (prompt + completion)
          example: 60
        completion_tokens_details:
          description: Детализация токенов completion
          nullable: true
          allOf:
            - $ref: '#/components/schemas/CompletionTokensDetailsPresenter'
        prompt_tokens_details:
          description: Детализация токенов промпта
          nullable: true
          allOf:
            - $ref: '#/components/schemas/PromptTokensDetailsPresenter'
        server_tool_use:
          description: Использование серверных инструментов (web search)
          nullable: true
          allOf:
            - $ref: '#/components/schemas/ServerToolUsePresenter'
        cost_rub:
          type: object
          description: Стоимость запроса в рублях (списано с баланса клиента)
          example: 0.04131306
          nullable: true
        cost:
          type: object
          description: Стоимость запроса в рублях (alias для cost_rub)
          example: 0.04131306
          nullable: true
        plugins:
          type: object
          description: Детализация серверных плагинов
          example:
            masker:
              operations:
                - operation: mask
                  latency_ms: 15
                  cost_rub: 0.001
                - operation: unmask
                  latency_ms: 8
                  cost_rub: 0
              total_cost_rub: 0.001
          nullable: true
        plugin_post_process_error:
          type: boolean
          description: >-
            Ошибка post-process плагинов (ответ возвращён в замаскированном
            виде)
          example: true
      required:
        - prompt_tokens
        - completion_tokens
        - total_tokens
    ToolCallDto:
      type: object
      properties:
        id:
          type: string
          description: Уникальный идентификатор вызова инструмента
          example: call_abc123xyz
        type:
          type: string
          description: Тип вызова инструмента
          enum:
            - function
          example: function
        function:
          description: Информация о вызываемой функции
          allOf:
            - $ref: '#/components/schemas/ToolCallFunctionDto'
      required:
        - id
        - type
        - function
    ProviderMaxPriceDto:
      type: object
      properties:
        prompt:
          type: number
          description: Максимальная цена за промпт токены (RUB за миллион токенов)
          example: 10
        completion:
          type: number
          description: Максимальная цена за completion токены (RUB за миллион токенов)
          example: 20
        image:
          type: number
          description: Максимальная цена за изображение (RUB за штуку)
          example: 5
        audio:
          type: number
          description: Максимальная цена за аудио (RUB за миллион токенов)
          example: 15
        request:
          type: number
          description: Максимальная цена за запрос (RUB за запрос)
          example: 1
    ToolFunctionDto:
      type: object
      properties:
        name:
          type: string
          description: Название функции
          example: get_weather
        description:
          type: string
          description: Описание функции
          example: Получить текущую погоду для указанного местоположения
        parameters:
          type: object
          description: JSON Schema параметров функции
          example:
            type: object
            properties:
              location:
                type: string
                description: Название города
              unit:
                type: string
                enum:
                  - celsius
                  - fahrenheit
            required:
              - location
        strict:
          type: boolean
          description: Строгое соответствие схеме
          example: false
      required:
        - name
    MessagePresenter:
      type: object
      properties:
        role:
          type: string
          description: Роль отправителя сообщения
          example: assistant
        content:
          type: object
          description: Содержимое сообщения
          example: Привет! Я хорошо, спасибо что спросили. Чем могу помочь?
          nullable: true
        name:
          type: object
          description: Имя отправителя
          example: Ассистент
          nullable: true
        tool_calls:
          description: Вызовы инструментов (tool calls)
          type: array
          items:
            $ref: '#/components/schemas/ToolCallPresenter'
        refusal:
          type: object
          description: Отказ модели от выполнения запроса
          example: null
          nullable: true
        reasoning:
          type: object
          description: Reasoning текст (для reasoning моделей)
          example: null
          nullable: true
        audio:
          type: object
          description: Аудио данные (для моделей с audio output)
          properties:
            id:
              type: string
              description: ID аудио
            data:
              type: string
              description: Base64-encoded аудио данные
            transcript:
              type: string
              description: Текстовая расшифровка
            expires_at:
              type: number
              description: Unix timestamp истечения
        annotations:
          type: array
          description: Аннотации (ссылки на источники от web search)
          items:
            type: object
      required:
        - role
        - content
    ChatMessageTokenLogprobsPresenter:
      type: object
      properties:
        content:
          description: Log probabilities для контента
          nullable: true
          type: array
          items:
            $ref: '#/components/schemas/ChatMessageTokenLogprobPresenter'
        refusal:
          description: Log probabilities для refusal
          nullable: true
          type: array
          items:
            $ref: '#/components/schemas/ChatMessageTokenLogprobPresenter'
      required:
        - content
        - refusal
    CompletionTokensDetailsPresenter:
      type: object
      properties:
        reasoning_tokens:
          type: object
          description: Токены reasoning (для reasoning моделей)
          example: 100
          nullable: true
        audio_tokens:
          type: object
          description: Аудио токены в ответе
          example: 0
          nullable: true
        image_tokens:
          type: object
          description: Токены изображений в ответе
          example: 0
          nullable: true
        accepted_prediction_tokens:
          type: object
          description: Принятые токены предсказаний
          example: 0
          nullable: true
        rejected_prediction_tokens:
          type: object
          description: Отклоненные токены предсказаний
          example: 0
          nullable: true
    PromptTokensDetailsPresenter:
      type: object
      properties:
        cached_tokens:
          type: number
          description: Кэшированные токены
          example: 0
        audio_tokens:
          type: number
          description: Аудио токены в промпте
          example: 0
        video_tokens:
          type: number
          description: Видео токены в промпте
          example: 0
    ServerToolUsePresenter:
      type: object
      properties:
        web_search_requests:
          type: number
          description: Количество вызовов веб-поиска
          example: 1
    ToolCallFunctionDto:
      type: object
      properties:
        name:
          type: string
          description: Имя вызываемой функции
          example: get_weather
        arguments:
          type: string
          description: JSON-строка с аргументами функции
          example: '{"location": "Moscow", "unit": "celsius"}'
      required:
        - name
        - arguments
    ToolCallPresenter:
      type: object
      properties:
        id:
          type: string
          description: ID вызова функции
          example: call_abc123
        type:
          type: string
          description: Тип вызова
          example: function
        function:
          description: Информация о функции
          allOf:
            - $ref: '#/components/schemas/ToolCallFunctionPresenter'
      required:
        - id
        - type
        - function
    ChatMessageTokenLogprobPresenter:
      type: object
      properties:
        token:
          type: string
          description: Токен
          example: hello
        logprob:
          type: number
          description: Log probability токена
          example: -0.5
        bytes:
          type: object
          description: Байты токена
          example:
            - 104
            - 101
            - 108
            - 108
            - 111
          nullable: true
        top_logprobs:
          description: Топ наиболее вероятных токенов с их вероятностями
          type: array
          items:
            $ref: '#/components/schemas/ChatMessageTokenLogprobTopItemPresenter'
      required:
        - token
        - logprob
        - bytes
        - top_logprobs
    ToolCallFunctionPresenter:
      type: object
      properties:
        name:
          type: string
          description: Название функции
          example: get_weather
        arguments:
          type: string
          description: Аргументы функции в JSON формате
          example: '{"location": "Moscow"}'
      required:
        - name
        - arguments
    ChatMessageTokenLogprobTopItemPresenter:
      type: object
      properties:
        token:
          type: string
          description: Токен
          example: hello
        logprob:
          type: number
          description: Log probability токена
          example: -0.5
        bytes:
          type: object
          description: Байты токена
          example:
            - 104
            - 101
            - 108
            - 108
            - 111
          nullable: true
      required:
        - token
        - logprob
        - bytes
  securitySchemes:
    bearer:
      scheme: bearer
      bearerFormat: API Key
      type: http
      description: >-
        API ключ передаётся в заголовке: Authorization: Bearer
        <SPESHU_AI_API_KEY>

````