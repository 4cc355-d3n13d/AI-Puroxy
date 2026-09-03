> ## Documentation Index
> Fetch the complete documentation index at: https://speshu.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Список моделей

> Получение списка доступных моделей

Этот эндпоинт не требует аутентификации и доступен всем пользователям.

## Параметры запроса

| Параметр            | Тип     | Описание                                             |
| ------------------- | ------- | ---------------------------------------------------- |
| `type`              | string  | Фильтр по типу: chat, image, embedding, video, audio |
| `include_providers` | boolean | Включить массив провайдеров для каждой модели        |

## Примеры

```bash theme={null}
curl "https://speshu.ai/api/v1/models"
```

```bash theme={null}
curl "https://speshu.ai/api/v1/models?type=chat"
```

```bash theme={null}
curl "https://speshu.ai/api/v1/models?type=chat&include_providers=true"
```

```python theme={null}
from openai import OpenAI

client = OpenAI(
    base_url="https://speshu.ai/api/v1",
    api_key="YOUR_API_KEY"
)

models = client.models.list()
for model in models.data:
    print(model.id)
```

## Поля модели

### Основные

| Поле             | Описание                               |
| ---------------- | -------------------------------------- |
| `id`             | Уникальный идентификатор для API       |
| `name`           | Человекочитаемое название              |
| `context_length` | Максимальная длина контекста в токенах |
| `created`        | Unix timestamp создания                |

### Архитектура

| Поле                | Описание                                               |
| ------------------- | ------------------------------------------------------ |
| `input_modalities`  | Поддерживаемые входные типы: text, image, audio, video |
| `output_modalities` | Поддерживаемые выходные типы: text, image, audio       |
| `tokenizer`         | Используемый токенизатор                               |
| `instruct_type`     | Тип инструкций                                         |

### Ценообразование (в рублях за токен)

| Поле                 | Описание              |
| -------------------- | --------------------- |
| `prompt`             | Входные токены        |
| `completion`         | Выходные токены       |
| `image`              | Обработка изображений |
| `internal_reasoning` | Reasoning токены      |
| `input_cache_read`   | Чтение из кеша        |
| `input_cache_write`  | Запись в кеш          |

## Примеры фильтрации

### Мультимодальные модели

```python theme={null}
multimodal = [
    m for m in models
    if 'image' in m.get('architecture', {}).get('input_modalities', [])
]
```

### Модели с большим контекстом

```python theme={null}
large_context = [
    m for m in models
    if m.get('context_length', 0) > 100000
]
```

### Модели конкретного провайдера

```python theme={null}
anthropic = [m for m in models if m['id'].startswith('anthropic/')]
google = [m for m in models if m['id'].startswith('google/')]
meta = [m for m in models if m['id'].startswith('meta-llama/')]
```

## Использование ID моделей

ID модели напрямую используется в запросах:

```python theme={null}
response = client.chat.completions.create(
    model="anthropic/claude-3-5-sonnet",
    messages=[{"role": "user", "content": "Привет!"}]
)
```


## OpenAPI

````yaml GET /v1/models
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
  /v1/models:
    get:
      tags:
        - Модели
      summary: Получить список доступных моделей
      operationId: ModelsController_getModels[1]
      parameters:
        - name: type
          required: false
          in: query
          description: Фильтр по типу модели (chat, image, embedding и т.д.)
          schema:
            type: string
        - name: include_providers
          required: false
          in: query
          description: Включить массив провайдеров в ответ
          schema:
            type: boolean
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ModelListPresenter'
        '401':
          description: Ошибка авторизации. Проверьте ключ доступа
        '403':
          description: Ошибка доступа. Проверьте права доступа ключа
        '500':
          description: Ошибка сервера. Обратитесь к поставщику услуг
      security: []
components:
  schemas:
    ModelListPresenter:
      type: object
      properties:
        data:
          description: Список моделей
          type: array
          items:
            $ref: '#/components/schemas/PublicModelPresenter'
      required:
        - data
    PublicModelPresenter:
      type: object
      properties:
        id:
          type: string
          description: ID модели (slug)
          example: deepseek-r1
        name:
          type: string
          description: Название модели
          example: DeepSeek R1
        type:
          type: string
          description: Тип модели
          example: chat
          enum:
            - chat
            - embedding
            - image
            - audio
            - video
            - moderation
            - stt
            - tts
            - document
        short_description:
          type: object
          description: Краткое описание модели
          example: Мощная модель для генерации текста
        created:
          type: number
          description: Timestamp создания
          example: 1765987078
        architecture:
          description: Архитектура модели
          allOf:
            - $ref: '#/components/schemas/ModelArchitecturePresenter'
        top_provider:
          description: Информация о топ провайдере
          allOf:
            - $ref: '#/components/schemas/TopProviderPresenter'
        providers:
          description: Список провайдеров
          type: array
          items:
            $ref: '#/components/schemas/ModelProviderPresenter'
        endpoints:
          description: Поддерживаемые endpoints
          example:
            - /v1/chat/completions
          type: array
          items:
            type: string
        parameters:
          description: Параметры модели (для медиа)
          allOf:
            - $ref: '#/components/schemas/ModelParametersPresenter'
        operations:
          description: Операции над результатом (для медиа)
          type: array
          items:
            $ref: '#/components/schemas/ModelOperationPresenter'
      required:
        - id
        - name
        - type
        - created
        - architecture
        - top_provider
        - endpoints
    ModelArchitecturePresenter:
      type: object
      properties:
        modality:
          type: object
          description: Основная модальность
          example: text+image->text
        input_modalities:
          description: Входные модальности
          example:
            - text
            - image
          type: array
          items:
            type: string
        output_modalities:
          description: Выходные модальности
          example:
            - text
          type: array
          items:
            type: string
        tokenizer:
          type: object
          description: Токенизатор
          example: GPT
        instruct_type:
          type: object
          description: Тип инструкций
          example: chatml
      required:
        - input_modalities
        - output_modalities
    TopProviderPresenter:
      type: object
      properties:
        is_moderated:
          type: boolean
          description: Модерируется ли контент
        context_length:
          type: object
          description: Длина контекста от провайдера
        max_completion_tokens:
          type: object
          description: Максимум токенов completion от провайдера
        pricing:
          description: Ценообразование
          allOf:
            - $ref: '#/components/schemas/ModelPricingPresenter'
        supported_parameters:
          description: Поддерживаемые параметры
          type: array
          items:
            type: string
        default_parameters:
          description: Параметры по умолчанию
          allOf:
            - $ref: '#/components/schemas/DefaultParametersPresenter'
        per_request_limits:
          description: Лимиты на запрос
          allOf:
            - $ref: '#/components/schemas/PerRequestLimitsPresenter'
        parameters:
          description: Параметры медиа-модели
          allOf:
            - $ref: '#/components/schemas/ModelParametersPresenter'
      required:
        - is_moderated
        - pricing
    ModelProviderPresenter:
      type: object
      properties:
        name:
          type: string
          description: Название провайдера
          example: OpenRouter
        context_length:
          type: object
          description: Длина контекста от провайдера
        max_completion_tokens:
          type: object
          description: Максимум токенов completion от провайдера
        is_moderated:
          type: boolean
          description: Модерируется ли контент
        pricing:
          description: Ценообразование
          allOf:
            - $ref: '#/components/schemas/ModelPricingPresenter'
        supported_parameters:
          description: Поддерживаемые параметры
          type: array
          items:
            type: string
        default_parameters:
          description: Параметры по умолчанию
          allOf:
            - $ref: '#/components/schemas/DefaultParametersPresenter'
        per_request_limits:
          description: Лимиты на запрос
          allOf:
            - $ref: '#/components/schemas/PerRequestLimitsPresenter'
        parameters:
          description: Параметры медиа-модели
          allOf:
            - $ref: '#/components/schemas/ModelParametersPresenter'
      required:
        - name
        - is_moderated
        - pricing
    ModelParametersPresenter:
      type: object
      properties:
        prompt:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        aspect_ratio:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        resolution:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        image_resolution:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        duration:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        output_format:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        seeds:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        watermark:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        images:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        videos:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        quality:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        voice:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        speed:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        stability:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        similarity_boost:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        style:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        timestamps:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        previous_text:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        next_text:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
        language_code:
          $ref: '#/components/schemas/ModelParameterConstraintPresenter'
    ModelOperationPresenter:
      type: object
      properties:
        id:
          type: string
          description: ID операции
          example: extend
        name:
          type: string
          description: Название операции
          example: Продление видео
        description:
          type: string
          description: Описание операции
        async:
          type: boolean
          description: Асинхронная операция (требует polling)
        pricing:
          description: Стоимость операции
          allOf:
            - $ref: '#/components/schemas/ModelPricingPresenter'
        parameters:
          description: Параметры операции
          allOf:
            - $ref: '#/components/schemas/ModelParametersPresenter'
      required:
        - id
        - name
        - async
    ModelPricingPresenter:
      type: object
      properties:
        prompt_per_million:
          type: object
          description: Цена за 1M prompt токенов (RUB)
          example: '15.50'
        completion_per_million:
          type: object
          description: Цена за 1M completion токенов (RUB)
          example: '62.00'
        request_per_thousand:
          type: object
          description: Цена за 1K запросов (RUB)
        image_input_per_million:
          type: object
          description: Цена за 1M входных изображений (RUB)
        image_output_per_million:
          type: object
          description: Цена за 1M токенов сгенерированного изображения (RUB)
        audio_per_million:
          type: object
          description: Цена за 1M токенов аудио (RUB)
        web_search_per_thousand:
          type: object
          description: Цена за 1K web search запросов (RUB)
        internal_reasoning_per_million:
          type: object
          description: Цена за 1M reasoning токенов (RUB)
        input_cache_read_per_million:
          type: object
          description: Цена за 1M токенов чтения из кэша (RUB)
        input_cache_write_per_million:
          type: object
          description: Цена за 1M токенов записи в кэш (RUB)
        input_audio_cache_per_million:
          type: object
          description: Цена за 1M токенов кэшированного аудио (RUB)
        stt_per_minute:
          type: object
          description: Цена за 1 минуту Speech-to-Text (RUB)
        tts_per_million_characters:
          type: object
          description: Цена за 1M символов Text-to-Speech (RUB)
          example: '1800.00000000'
        video_per_second:
          type: object
          description: Цена за 1 секунду видео (RUB)
        per_request:
          type: object
          description: Цена за 1 запрос (RUB)
        tiers:
          description: Уровни цен для моделей с динамическим ценообразованием
          type: array
          items:
            $ref: '#/components/schemas/ClientTierPresenter'
        unitParam:
          type: object
          description: >-
            Параметр-множитель для tiers (например, duration). Если задан,
            cost_rub в tiers — ставка за единицу этого параметра
          example: duration
        currency:
          type: string
          description: Валюта цен
          example: RUB
      required:
        - currency
    DefaultParametersPresenter:
      type: object
      properties:
        temperature:
          type: object
          description: Temperature по умолчанию (0-2)
        top_p:
          type: object
          description: Top P по умолчанию (0-1)
        frequency_penalty:
          type: object
          description: Frequency penalty по умолчанию (-2-2)
    PerRequestLimitsPresenter:
      type: object
      properties:
        prompt_tokens:
          type: object
          description: Максимум prompt токенов на запрос
        completion_tokens:
          type: object
          description: Максимум completion токенов на запрос
    ModelParameterConstraintPresenter:
      type: object
      properties:
        required:
          type: boolean
          description: Обязательный параметр
        description:
          type: string
          description: Описание параметра
        max_length:
          type: number
          description: Максимальная длина строки
        min:
          type: number
          description: Минимальное значение
        max:
          type: number
          description: Максимальное значение
        default:
          type: object
          description: Значение по умолчанию
        values:
          description: Допустимые значения
          type: array
          items:
            type: string
    ClientTierPresenter:
      type: object
      properties:
        conditions:
          description: Условия применения уровня цены
          example:
            - image_resolution=4K
          type: array
          items:
            type: string
        cost_rub:
          type: string
          description: Цена для клиента в RUB
          example: '8.25'
      required:
        - conditions
        - cost_rub
  securitySchemes:
    bearer:
      scheme: bearer
      bearerFormat: API Key
      type: http
      description: >-
        API ключ передаётся в заголовке: Authorization: Bearer
        <SPESHU_AI_API_KEY>

````