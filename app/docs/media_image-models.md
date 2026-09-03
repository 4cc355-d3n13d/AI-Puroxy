> ## Documentation Index
> Fetch the complete documentation index at: https://speshu.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Модели изображений

> Параметры моделей для генерации и редактирования изображений

Здесь собраны модели изображений и их входные параметры. Используйте ID модели в поле `model`.

<Note>
  Передавайте параметры модели в поле `input` при создании задачи через `POST /async/media/tasks`. Актуальную схему можно получить через `GET /media/models`.
</Note>

## Модели

### `bytedance/seedream`

| Поле             | Тип    | Обязательное |
| ---------------- | ------ | ------------ |
| `prompt`         | string | да           |
| `image_size`     | string | нет          |
| `guidance_scale` | number | нет          |
| `seed`           | number | нет          |

### `bytedance/seedream-v4-edit`

| Поле               | Тип     | Обязательное |
| ------------------ | ------- | ------------ |
| `prompt`           | string  | да           |
| `image_urls`       | array   | да           |
| `image_size`       | string  | нет          |
| `image_resolution` | string  | нет          |
| `max_images`       | number  | нет          |
| `seed`             | number  | нет          |
| `nsfw_checker`     | boolean | нет          |

### `bytedance/seedream-v4-text-to-image`

| Поле               | Тип     | Обязательное |
| ------------------ | ------- | ------------ |
| `prompt`           | string  | да           |
| `image_size`       | string  | нет          |
| `image_resolution` | string  | нет          |
| `max_images`       | number  | нет          |
| `seed`             | number  | нет          |
| `nsfw_checker`     | boolean | нет          |

### `flux-2/flex-image-to-image`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `input_urls`   | array   | да           |
| `prompt`       | string  | да           |
| `aspect_ratio` | string  | да           |
| `resolution`   | string  | да           |
| `nsfw_checker` | boolean | нет          |

### `flux-2/flex-text-to-image`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `aspect_ratio` | string  | да           |
| `resolution`   | string  | да           |
| `nsfw_checker` | boolean | нет          |

### `flux-2/pro-image-to-image`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `input_urls`   | array   | да           |
| `prompt`       | string  | да           |
| `aspect_ratio` | string  | да           |
| `resolution`   | string  | да           |
| `nsfw_checker` | boolean | нет          |

### `flux-2/pro-text-to-image`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `aspect_ratio` | string  | да           |
| `resolution`   | string  | да           |
| `nsfw_checker` | boolean | нет          |

### `flux-kontext-max`

| Поле                | Тип     | Обязательное |
| ------------------- | ------- | ------------ |
| `prompt`            | string  | да           |
| `enableTranslation` | boolean | нет          |
| `uploadCn`          | boolean | нет          |
| `inputImage`        | string  | нет          |
| `aspectRatio`       | string  | нет          |
| `outputFormat`      | string  | нет          |
| `promptUpsampling`  | boolean | нет          |
| `safetyTolerance`   | number  | нет          |
| `watermark`         | string  | нет          |

### `flux-kontext-pro`

| Поле                | Тип     | Обязательное |
| ------------------- | ------- | ------------ |
| `prompt`            | string  | да           |
| `enableTranslation` | boolean | нет          |
| `uploadCn`          | boolean | нет          |
| `inputImage`        | string  | нет          |
| `aspectRatio`       | string  | нет          |
| `outputFormat`      | string  | нет          |
| `promptUpsampling`  | boolean | нет          |
| `safetyTolerance`   | number  | нет          |
| `watermark`         | string  | нет          |

### `google/imagen4`

| Поле              | Тип    | Обязательное |
| ----------------- | ------ | ------------ |
| `prompt`          | string | да           |
| `negative_prompt` | string | нет          |
| `aspect_ratio`    | string | нет          |
| `seed`            | string | нет          |

### `google/imagen4-fast`

| Поле              | Тип    | Обязательное |
| ----------------- | ------ | ------------ |
| `prompt`          | string | да           |
| `negative_prompt` | string | нет          |
| `aspect_ratio`    | string | нет          |
| `num_images`      | string | нет          |
| `seed`            | number | нет          |

### `google/imagen4-ultra`

| Поле              | Тип    | Обязательное |
| ----------------- | ------ | ------------ |
| `prompt`          | string | да           |
| `negative_prompt` | string | нет          |
| `aspect_ratio`    | string | нет          |
| `seed`            | string | нет          |

### `google/nano-banana`

| Поле            | Тип    | Обязательное |
| --------------- | ------ | ------------ |
| `prompt`        | string | да           |
| `output_format` | string | нет          |
| `image_size`    | string | нет          |

### `google/nano-banana-edit`

| Поле            | Тип    | Обязательное |
| --------------- | ------ | ------------ |
| `prompt`        | string | да           |
| `image_urls`    | array  | да           |
| `output_format` | string | нет          |
| `image_size`    | string | нет          |

### `gpt-4o-image`

| Поле             | Тип     | Обязательное |
| ---------------- | ------- | ------------ |
| `prompt`         | string  | нет          |
| `filesUrl`       | array   | нет          |
| `size`           | string  | да           |
| `maskUrl`        | string  | нет          |
| `isEnhance`      | boolean | нет          |
| `uploadCn`       | boolean | нет          |
| `enableFallback` | boolean | нет          |
| `fallbackModel`  | string  | нет          |

### `gpt-image-2-image-to-image`

| Поле           | Тип    | Обязательное |
| -------------- | ------ | ------------ |
| `input_urls`   | array  | да           |
| `prompt`       | string | да           |
| `aspect_ratio` | string | нет          |
| `resolution`   | string | нет          |

### `gpt-image-2-text-to-image`

| Поле           | Тип    | Обязательное |
| -------------- | ------ | ------------ |
| `prompt`       | string | да           |
| `aspect_ratio` | string | нет          |
| `resolution`   | string | нет          |

### `gpt-image/1.5-image-to-image`

| Поле           | Тип    | Обязательное |
| -------------- | ------ | ------------ |
| `input_urls`   | array  | да           |
| `prompt`       | string | да           |
| `aspect_ratio` | string | да           |
| `quality`      | string | да           |

### `gpt-image/1.5-text-to-image`

| Поле           | Тип    | Обязательное |
| -------------- | ------ | ------------ |
| `prompt`       | string | да           |
| `aspect_ratio` | string | да           |
| `quality`      | string | да           |

### `grok-imagine/image-to-image`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | нет          |
| `image_urls`   | array   | да           |
| `nsfw_checker` | boolean | нет          |

### `grok-imagine/text-to-image`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `aspect_ratio` | string  | нет          |
| `nsfw_checker` | boolean | нет          |
| `enable_pro`   | boolean | нет          |

### `ideogram/character`

| Поле                   | Тип     | Обязательное |
| ---------------------- | ------- | ------------ |
| `prompt`               | string  | да           |
| `reference_image_urls` | array   | да           |
| `rendering_speed`      | string  | нет          |
| `style`                | string  | нет          |
| `expand_prompt`        | boolean | нет          |
| `num_images`           | string  | нет          |
| `image_size`           | string  | нет          |
| `seed`                 | number  | нет          |
| `negative_prompt`      | string  | нет          |

### `ideogram/character-edit`

| Поле                   | Тип     | Обязательное |
| ---------------------- | ------- | ------------ |
| `prompt`               | string  | да           |
| `image_url`            | string  | да           |
| `mask_url`             | string  | да           |
| `reference_image_urls` | array   | да           |
| `rendering_speed`      | string  | нет          |
| `style`                | string  | нет          |
| `expand_prompt`        | boolean | нет          |
| `num_images`           | string  | нет          |
| `seed`                 | number  | нет          |

### `ideogram/character-remix`

| Поле                   | Тип     | Обязательное |
| ---------------------- | ------- | ------------ |
| `prompt`               | string  | да           |
| `image_url`            | string  | да           |
| `reference_image_urls` | array   | да           |
| `rendering_speed`      | string  | нет          |
| `style`                | string  | нет          |
| `expand_prompt`        | boolean | нет          |
| `image_size`           | string  | нет          |
| `num_images`           | string  | нет          |
| `seed`                 | number  | нет          |
| `strength`             | number  | нет          |
| `negative_prompt`      | string  | нет          |
| `image_urls`           | array   | нет          |
| `reference_mask_urls`  | string  | нет          |

### `ideogram/v3-edit`

| Поле              | Тип     | Обязательное |
| ----------------- | ------- | ------------ |
| `prompt`          | string  | да           |
| `image_url`       | string  | да           |
| `mask_url`        | string  | да           |
| `rendering_speed` | string  | нет          |
| `expand_prompt`   | boolean | нет          |
| `seed`            | number  | нет          |

### `ideogram/v3-remix`

| Поле              | Тип     | Обязательное |
| ----------------- | ------- | ------------ |
| `prompt`          | string  | да           |
| `image_url`       | string  | да           |
| `rendering_speed` | string  | нет          |
| `style`           | string  | нет          |
| `expand_prompt`   | boolean | нет          |
| `image_size`      | string  | нет          |
| `num_images`      | string  | нет          |
| `seed`            | number  | нет          |
| `strength`        | number  | нет          |
| `negative_prompt` | string  | нет          |

### `ideogram/v3-text-to-image`

| Поле              | Тип     | Обязательное |
| ----------------- | ------- | ------------ |
| `prompt`          | string  | да           |
| `rendering_speed` | string  | нет          |
| `style`           | string  | нет          |
| `expand_prompt`   | boolean | нет          |
| `image_size`      | string  | нет          |
| `seed`            | number  | нет          |
| `negative_prompt` | string  | нет          |

### `nano-banana-2`

| Поле            | Тип    | Обязательное |
| --------------- | ------ | ------------ |
| `prompt`        | string | да           |
| `image_input`   | array  | нет          |
| `aspect_ratio`  | string | нет          |
| `resolution`    | string | нет          |
| `output_format` | string | нет          |

### `nano-banana-pro`

| Поле            | Тип    | Обязательное |
| --------------- | ------ | ------------ |
| `prompt`        | string | да           |
| `image_input`   | array  | нет          |
| `aspect_ratio`  | string | нет          |
| `resolution`    | string | нет          |
| `output_format` | string | нет          |

### `qwen/image-edit`

| Поле                    | Тип     | Обязательное |
| ----------------------- | ------- | ------------ |
| `prompt`                | string  | да           |
| `image_url`             | string  | да           |
| `acceleration`          | string  | нет          |
| `image_size`            | string  | нет          |
| `num_inference_steps`   | number  | нет          |
| `seed`                  | number  | нет          |
| `guidance_scale`        | number  | нет          |
| `sync_mode`             | boolean | нет          |
| `num_images`            | string  | нет          |
| `enable_safety_checker` | boolean | нет          |
| `output_format`         | string  | нет          |
| `negative_prompt`       | string  | нет          |
| `nsfw_checker`          | boolean | нет          |

### `qwen/image-to-image`

| Поле                    | Тип     | Обязательное |
| ----------------------- | ------- | ------------ |
| `prompt`                | string  | да           |
| `image_url`             | string  | да           |
| `strength`              | number  | нет          |
| `output_format`         | string  | нет          |
| `acceleration`          | string  | нет          |
| `negative_prompt`       | string  | нет          |
| `seed`                  | number  | нет          |
| `num_inference_steps`   | number  | нет          |
| `guidance_scale`        | number  | нет          |
| `enable_safety_checker` | boolean | нет          |
| `nsfw_checker`          | boolean | нет          |

### `qwen/text-to-image`

| Поле                    | Тип     | Обязательное |
| ----------------------- | ------- | ------------ |
| `prompt`                | string  | да           |
| `image_size`            | string  | нет          |
| `num_inference_steps`   | number  | нет          |
| `seed`                  | number  | нет          |
| `guidance_scale`        | number  | нет          |
| `enable_safety_checker` | boolean | нет          |
| `output_format`         | string  | нет          |
| `negative_prompt`       | string  | нет          |
| `acceleration`          | string  | нет          |
| `nsfw_checker`          | boolean | нет          |

### `qwen2/image-edit`

| Поле            | Тип     | Обязательное |
| --------------- | ------- | ------------ |
| `prompt`        | string  | да           |
| `image_url`     | string  | да           |
| `image_size`    | string  | нет          |
| `seed`          | number  | нет          |
| `output_format` | string  | нет          |
| `nsfw_checker`  | boolean | нет          |

### `qwen2/text-to-image`

| Поле            | Тип     | Обязательное |
| --------------- | ------- | ------------ |
| `prompt`        | string  | да           |
| `image_size`    | string  | нет          |
| `seed`          | number  | нет          |
| `output_format` | string  | нет          |
| `nsfw_checker`  | boolean | нет          |

### `recraft/crisp-upscale`

| Поле    | Тип    | Обязательное |
| ------- | ------ | ------------ |
| `image` | string | да           |

### `recraft/remove-background`

| Поле    | Тип    | Обязательное |
| ------- | ------ | ------------ |
| `image` | string | да           |

### `seedream/4.5-edit`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `image_urls`   | array   | да           |
| `aspect_ratio` | string  | да           |
| `quality`      | string  | да           |
| `nsfw_checker` | boolean | нет          |

### `seedream/4.5-text-to-image`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `aspect_ratio` | string  | да           |
| `quality`      | string  | да           |
| `nsfw_checker` | boolean | нет          |

### `seedream/5-lite-image-to-image`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `image_urls`   | array   | да           |
| `aspect_ratio` | string  | да           |
| `quality`      | string  | да           |
| `nsfw_checker` | boolean | нет          |

### `seedream/5-lite-text-to-image`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `aspect_ratio` | string  | да           |
| `quality`      | string  | да           |
| `nsfw_checker` | boolean | нет          |

### `topaz/image-upscale`

| Поле             | Тип    | Обязательное |
| ---------------- | ------ | ------------ |
| `image_url`      | string | да           |
| `upscale_factor` | string | да           |

### `wan/2-7-image`

| Поле                | Тип     | Обязательное |
| ------------------- | ------- | ------------ |
| `prompt`            | string  | да           |
| `input_urls`        | array   | нет          |
| `aspect_ratio`      | string  | нет          |
| `enable_sequential` | boolean | нет          |
| `n`                 | number  | нет          |
| `resolution`        | string  | нет          |
| `thinking_mode`     | boolean | нет          |
| `color_palette`     | string  | нет          |
| `bbox_list`         | string  | нет          |
| `watermark`         | boolean | нет          |
| `seed`              | number  | нет          |

### `wan/2-7-image-pro`

| Поле                | Тип     | Обязательное |
| ------------------- | ------- | ------------ |
| `prompt`            | string  | да           |
| `input_urls`        | array   | нет          |
| `aspect_ratio`      | string  | нет          |
| `enable_sequential` | boolean | нет          |
| `n`                 | number  | нет          |
| `resolution`        | string  | нет          |
| `thinking_mode`     | boolean | нет          |
| `color_palette`     | string  | нет          |
| `bbox_list`         | string  | нет          |
| `watermark`         | boolean | нет          |
| `seed`              | number  | нет          |

### `z-image`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `aspect_ratio` | string  | да           |
| `nsfw_checker` | boolean | нет          |
