> ## Documentation Index
> Fetch the complete documentation index at: https://speshu.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Медиа модели

> Каталог моделей генерации медиа и схемы входных параметров

Эндпоинт возвращает доступные модели для изображений, видео, музыки и аудио. У каждой модели есть `input_schema`. Используйте её как источник правды для поля `input`.

## Пример

```bash theme={null} theme={null}
curl "https://speshu.ai/api/v1/media/models" \
  -H "Authorization: Bearer <SPESHU_AI_API_KEY>"
```

## Ответ

```json theme={null} theme={null}
{
  "object": "list",
  "data": [
    {
      "id": "flux-2/pro-text-to-image",
      "object": "model",
      "owned_by": "speshu",
      "media_type": "image",
      "pricing": {
        "currency": "RUB",
        "type": "tiered",
        "tiers": [
          { "params": { "resolution": "1K" }, "price": "15.00" }
        ]
      },
      "input_schema": {
        "type": "object",
        "properties": {
          "prompt": { "type": "string" },
          "aspect_ratio": { "type": "string" },
          "resolution": { "type": "string" }
        },
        "required": ["prompt", "aspect_ratio", "resolution"]
      }
    }
  ]
}
```

## Поля модели

| Поле           | Описание                                          |
| -------------- | ------------------------------------------------- |
| `id`           | ID модели для `POST /async/media/tasks`.          |
| `owned_by`     | Провайдер или владелец модели.                    |
| `media_type`   | Тип медиа: `image`, `video`, `music` или `audio`. |
| `pricing`      | Информация о стоимости.                           |
| `input_schema` | JSON Schema для поля `input`.                     |

## Категории

<CardGroup cols={3}>
  <Card title="Изображения" icon="image" href="/docs/api-reference/media/image-models">
    Text-to-image, image-to-image, редактирование, апскейл и фон.
  </Card>

  <Card title="Видео" icon="video" href="/docs/api-reference/media/video-models">
    Text-to-video, image-to-video, motion control, extend и upscale.
  </Card>

  <Card title="Музыка и аудио" icon="music" href="/docs/api-reference/media/audio-models">
    TTS, STT, sound effects и генерация музыки.
  </Card>
</CardGroup>


## OpenAPI

````yaml GET /v1/media/models
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
  /v1/media/models:
    get:
      tags:
        - Медиа
      summary: Получить список media models
      operationId: MediaModelsController_list
      responses:
        '200':
          description: Каталог моделей
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MediaModelListResponse'
        '401':
          description: Ошибка авторизации. Проверьте ключ доступа
        '500':
          description: Ошибка сервера. Обратитесь к поставщику услуг
      security:
        - bearer: []
components:
  schemas:
    MediaModelListResponse:
      type: object
      properties:
        object:
          type: string
          example: list
        data:
          type: array
          items:
            $ref: '#/components/schemas/MediaModel'
      required:
        - object
        - data
    MediaModel:
      type: object
      properties:
        id:
          type: string
          example: flux-2/pro-text-to-image
        object:
          type: string
          example: model
        owned_by:
          type: string
          example: kie
        media_type:
          type: string
          enum:
            - image
            - video
            - music
            - audio
          example: image
        pricing:
          $ref: '#/components/schemas/MediaModelPricing'
        input_schema:
          type: object
          additionalProperties: true
          description: JSON Schema для input
      required:
        - id
        - object
        - media_type
        - input_schema
    MediaModelPricing:
      type: object
      additionalProperties: true
      properties:
        currency:
          type: string
          example: RUB
        type:
          type: string
          example: tiered
  securitySchemes:
    bearer:
      scheme: bearer
      bearerFormat: API Key
      type: http
      description: >-
        API ключ передаётся в заголовке: Authorization: Bearer
        <SPESHU_AI_API_KEY>

````