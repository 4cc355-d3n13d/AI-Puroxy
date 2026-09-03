> ## Documentation Index
> Fetch the complete documentation index at: https://speshu.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Модели видео

> Параметры моделей для генерации, редактирования и улучшения видео

Здесь собраны модели видео и их входные параметры. Используйте ID модели в поле `model`.

<Note>
  Передавайте параметры модели в поле `input` при создании задачи через `POST /async/media/tasks`. Актуальную схему можно получить через `GET /media/models`.
</Note>

## Модели

### `bytedance/create-asset`

| Поле        | Тип    | Обязательное |
| ----------- | ------ | ------------ |
| `url`       | string | да           |
| `assetType` | string | да           |

### `bytedance/query-asset`

| Поле      | Тип    | Обязательное |
| --------- | ------ | ------------ |
| `assetId` | string | да           |

### `bytedance/seedance-1.5-pro`

| Поле             | Тип     | Обязательное |
| ---------------- | ------- | ------------ |
| `prompt`         | string  | да           |
| `input_urls`     | array   | нет          |
| `aspect_ratio`   | string  | да           |
| `resolution`     | string  | нет          |
| `duration`       | number  | нет          |
| `fixed_lens`     | boolean | нет          |
| `generate_audio` | boolean | нет          |
| `nsfw_checker`   | boolean | нет          |

### `bytedance/seedance-2`

| Поле                   | Тип     | Обязательное |
| ---------------------- | ------- | ------------ |
| `prompt`               | string  | нет          |
| `first_frame_url`      | string  | нет          |
| `last_frame_url`       | string  | нет          |
| `reference_image_urls` | array   | нет          |
| `reference_video_urls` | array   | нет          |
| `reference_audio_urls` | array   | нет          |
| `return_last_frame`    | boolean | нет          |
| `generate_audio`       | boolean | нет          |
| `resolution`           | string  | нет          |
| `aspect_ratio`         | string  | нет          |
| `duration`             | number  | нет          |
| `web_search`           | boolean | да           |

### `bytedance/seedance-2-fast`

| Поле                   | Тип     | Обязательное |
| ---------------------- | ------- | ------------ |
| `prompt`               | string  | нет          |
| `first_frame_url`      | string  | нет          |
| `last_frame_url`       | string  | нет          |
| `reference_image_urls` | array   | нет          |
| `reference_video_urls` | array   | нет          |
| `reference_audio_urls` | array   | нет          |
| `return_last_frame`    | boolean | нет          |
| `generate_audio`       | boolean | нет          |
| `resolution`           | string  | нет          |
| `aspect_ratio`         | string  | нет          |
| `duration`             | number  | нет          |
| `web_search`           | boolean | да           |

### `bytedance/seedance-2-fast-v2`

| Поле                   | Тип     | Обязательное |
| ---------------------- | ------- | ------------ |
| `prompt`               | string  | нет          |
| `first_frame_url`      | string  | нет          |
| `last_frame_url`       | string  | нет          |
| `reference_image_urls` | array   | нет          |
| `reference_video_urls` | array   | нет          |
| `reference_audio_urls` | array   | нет          |
| `return_last_frame`    | boolean | нет          |
| `generate_audio`       | boolean | нет          |
| `resolution`           | string  | нет          |
| `aspect_ratio`         | string  | нет          |
| `duration`             | number  | нет          |
| `web_search`           | boolean | нет          |
| `nsfw_checker`         | boolean | нет          |

### `bytedance/seedance-2-v2`

| Поле                   | Тип     | Обязательное |
| ---------------------- | ------- | ------------ |
| `prompt`               | string  | нет          |
| `first_frame_url`      | string  | нет          |
| `last_frame_url`       | string  | нет          |
| `reference_image_urls` | array   | нет          |
| `reference_video_urls` | array   | нет          |
| `reference_audio_urls` | array   | нет          |
| `return_last_frame`    | boolean | нет          |
| `generate_audio`       | boolean | нет          |
| `resolution`           | string  | нет          |
| `aspect_ratio`         | string  | нет          |
| `duration`             | number  | нет          |
| `web_search`           | boolean | нет          |
| `nsfw_checker`         | boolean | нет          |

### `bytedance/v1-lite-image-to-video`

| Поле                    | Тип     | Обязательное |
| ----------------------- | ------- | ------------ |
| `prompt`                | string  | да           |
| `image_url`             | string  | да           |
| `resolution`            | string  | нет          |
| `duration`              | string  | нет          |
| `camera_fixed`          | boolean | нет          |
| `seed`                  | number  | нет          |
| `enable_safety_checker` | boolean | нет          |
| `end_image_url`         | string  | нет          |
| `nsfw_checker`          | boolean | нет          |

### `bytedance/v1-lite-text-to-video`

| Поле                    | Тип     | Обязательное |
| ----------------------- | ------- | ------------ |
| `prompt`                | string  | да           |
| `aspect_ratio`          | string  | нет          |
| `resolution`            | string  | нет          |
| `duration`              | string  | нет          |
| `camera_fixed`          | boolean | нет          |
| `seed`                  | number  | нет          |
| `enable_safety_checker` | boolean | нет          |
| `nsfw_checker`          | boolean | нет          |

### `bytedance/v1-pro-fast-image-to-video`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `image_url`    | string  | да           |
| `resolution`   | string  | нет          |
| `duration`     | string  | нет          |
| `nsfw_checker` | boolean | нет          |

### `bytedance/v1-pro-image-to-video`

| Поле                    | Тип     | Обязательное |
| ----------------------- | ------- | ------------ |
| `prompt`                | string  | да           |
| `image_url`             | string  | да           |
| `resolution`            | string  | нет          |
| `duration`              | string  | нет          |
| `camera_fixed`          | boolean | нет          |
| `seed`                  | number  | нет          |
| `enable_safety_checker` | boolean | нет          |
| `nsfw_checker`          | boolean | нет          |

### `bytedance/v1-pro-text-to-video`

| Поле                    | Тип     | Обязательное |
| ----------------------- | ------- | ------------ |
| `prompt`                | string  | да           |
| `aspect_ratio`          | string  | нет          |
| `resolution`            | string  | нет          |
| `duration`              | string  | нет          |
| `camera_fixed`          | boolean | нет          |
| `seed`                  | number  | нет          |
| `enable_safety_checker` | boolean | нет          |
| `nsfw_checker`          | boolean | нет          |

### `grok-imagine/extend`

| Поле           | Тип    | Обязательное |
| -------------- | ------ | ------------ |
| `task_id`      | string | да           |
| `prompt`       | string | да           |
| `extend_at`    | string | да           |
| `extend_times` | string | да           |

### `grok-imagine/image-to-video`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `image_urls`   | array   | нет          |
| `task_id`      | string  | нет          |
| `index`        | number  | нет          |
| `prompt`       | string  | нет          |
| `mode`         | string  | нет          |
| `duration`     | string  | нет          |
| `resolution`   | string  | нет          |
| `aspect_ratio` | string  | нет          |
| `nsfw_checker` | boolean | нет          |

### `grok-imagine/text-to-video`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `aspect_ratio` | string  | нет          |
| `mode`         | string  | нет          |
| `duration`     | number  | нет          |
| `resolution`   | string  | нет          |
| `nsfw_checker` | boolean | нет          |

### `grok-imagine/upscale`

| Поле      | Тип    | Обязательное |
| --------- | ------ | ------------ |
| `task_id` | string | да           |

### `hailuo/02-image-to-video-pro`

| Поле               | Тип     | Обязательное |
| ------------------ | ------- | ------------ |
| `prompt`           | string  | да           |
| `image_url`        | string  | да           |
| `end_image_url`    | string  | нет          |
| `prompt_optimizer` | boolean | нет          |

### `hailuo/02-image-to-video-standard`

| Поле               | Тип     | Обязательное |
| ------------------ | ------- | ------------ |
| `prompt`           | string  | да           |
| `image_url`        | string  | да           |
| `end_image_url`    | string  | нет          |
| `duration`         | string  | нет          |
| `resolution`       | string  | нет          |
| `prompt_optimizer` | boolean | нет          |
| `nsfw_checker`     | boolean | нет          |

### `hailuo/02-text-to-video-pro`

| Поле               | Тип     | Обязательное |
| ------------------ | ------- | ------------ |
| `prompt`           | string  | да           |
| `prompt_optimizer` | boolean | нет          |

### `hailuo/02-text-to-video-standard`

| Поле               | Тип     | Обязательное |
| ------------------ | ------- | ------------ |
| `prompt`           | string  | да           |
| `duration`         | string  | нет          |
| `prompt_optimizer` | boolean | нет          |
| `nsfw_checker`     | boolean | нет          |

### `hailuo/2-3-image-to-video-pro`

| Поле         | Тип    | Обязательное |
| ------------ | ------ | ------------ |
| `prompt`     | string | да           |
| `image_url`  | string | да           |
| `duration`   | string | нет          |
| `resolution` | string | нет          |

### `hailuo/2-3-image-to-video-standard`

| Поле         | Тип    | Обязательное |
| ------------ | ------ | ------------ |
| `prompt`     | string | да           |
| `image_url`  | string | да           |
| `duration`   | string | нет          |
| `resolution` | string | нет          |

### HappyHorse

HappyHorse — одна модель с разными режимами генерации и редактирования видео.
В поле `model` передавайте ID нужного режима.

| Фича               | ID модели                       | Когда использовать                          |
| ------------------ | ------------------------------- | ------------------------------------------- |
| Image-to-video     | `happyhorse/image-to-video`     | Создать видео по изображению и промпту      |
| Reference-to-video | `happyhorse/reference-to-video` | Создать видео с референсными изображениями  |
| Text-to-video      | `happyhorse/text-to-video`      | Создать видео только по текстовому описанию |
| Video edit         | `happyhorse/video-edit`         | Отредактировать существующее видео          |

#### `happyhorse/image-to-video`

| Поле         | Тип    | Обязательное |
| ------------ | ------ | ------------ |
| `prompt`     | string | нет          |
| `image_urls` | array  | нет          |
| `resolution` | string | нет          |
| `duration`   | number | нет          |
| `seed`       | number | нет          |

#### `happyhorse/reference-to-video`

| Поле              | Тип    | Обязательное |
| ----------------- | ------ | ------------ |
| `prompt`          | string | да           |
| `reference_image` | array  | да           |
| `resolution`      | string | нет          |
| `aspect_ratio`    | string | нет          |
| `duration`        | number | нет          |
| `seed`            | number | нет          |

#### `happyhorse/text-to-video`

| Поле           | Тип    | Обязательное |
| -------------- | ------ | ------------ |
| `prompt`       | string | да           |
| `resolution`   | string | нет          |
| `aspect_ratio` | string | нет          |
| `duration`     | number | нет          |
| `seed`         | number | нет          |

#### `happyhorse/video-edit`

| Поле              | Тип    | Обязательное |
| ----------------- | ------ | ------------ |
| `prompt`          | string | да           |
| `video_url`       | string | да           |
| `reference_image` | array  | нет          |
| `resolution`      | string | нет          |
| `audio_setting`   | string | нет          |
| `seed`            | number | нет          |

### `infinitalk/from-audio`

| Поле         | Тип    | Обязательное |
| ------------ | ------ | ------------ |
| `image_url`  | string | да           |
| `audio_url`  | string | да           |
| `prompt`     | string | да           |
| `resolution` | string | нет          |
| `seed`       | number | нет          |

### `kling-2.6/image-to-video`

| Поле         | Тип     | Обязательное |
| ------------ | ------- | ------------ |
| `prompt`     | string  | да           |
| `image_urls` | array   | нет          |
| `sound`      | boolean | да           |
| `duration`   | string  | да           |

### `kling-2.6/motion-control`

| Поле                    | Тип    | Обязательное |
| ----------------------- | ------ | ------------ |
| `prompt`                | string | нет          |
| `input_urls`            | array  | да           |
| `video_urls`            | array  | да           |
| `character_orientation` | string | да           |
| `mode`                  | string | да           |

### `kling-2.6/text-to-video`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `sound`        | boolean | да           |
| `aspect_ratio` | string  | да           |
| `duration`     | string  | да           |

### `kling-3.0/motion-control`

| Поле                    | Тип    | Обязательное |
| ----------------------- | ------ | ------------ |
| `prompt`                | string | нет          |
| `input_urls`            | array  | да           |
| `video_urls`            | array  | да           |
| `mode`                  | string | нет          |
| `character_orientation` | string | нет          |
| `background_source`     | string | нет          |

### `kling-3.0/video`

| Поле             | Тип     | Обязательное |
| ---------------- | ------- | ------------ |
| `prompt`         | string  | да           |
| `image_urls`     | array   | нет          |
| `sound`          | boolean | да           |
| `duration`       | string  | да           |
| `aspect_ratio`   | string  | да           |
| `mode`           | string  | да           |
| `multi_shots`    | boolean | да           |
| `multi_prompt`   | array   | нет          |
| `kling_elements` | array   | нет          |

### `kling/ai-avatar-pro`

| Поле        | Тип    | Обязательное |
| ----------- | ------ | ------------ |
| `image_url` | string | да           |
| `audio_url` | string | да           |
| `prompt`    | string | да           |

### `kling/ai-avatar-standard`

| Поле        | Тип    | Обязательное |
| ----------- | ------ | ------------ |
| `image_url` | string | да           |
| `audio_url` | string | да           |
| `prompt`    | string | да           |

### `kling/v2-1-master-image-to-video`

| Поле              | Тип    | Обязательное |
| ----------------- | ------ | ------------ |
| `prompt`          | string | да           |
| `image_url`       | string | нет          |
| `duration`        | string | нет          |
| `negative_prompt` | string | нет          |
| `cfg_scale`       | number | нет          |

### `kling/v2-1-master-text-to-video`

| Поле              | Тип    | Обязательное |
| ----------------- | ------ | ------------ |
| `prompt`          | string | да           |
| `duration`        | string | нет          |
| `aspect_ratio`    | string | нет          |
| `negative_prompt` | string | нет          |
| `cfg_scale`       | number | нет          |

### `kling/v2-1-pro`

| Поле              | Тип    | Обязательное |
| ----------------- | ------ | ------------ |
| `prompt`          | string | да           |
| `image_url`       | string | нет          |
| `duration`        | string | нет          |
| `negative_prompt` | string | нет          |
| `cfg_scale`       | number | нет          |
| `tail_image_url`  | string | нет          |

### `kling/v2-1-standard`

| Поле              | Тип    | Обязательное |
| ----------------- | ------ | ------------ |
| `prompt`          | string | да           |
| `image_url`       | string | нет          |
| `duration`        | string | нет          |
| `negative_prompt` | string | нет          |
| `cfg_scale`       | number | нет          |

### `kling/v2-5-turbo-image-to-video-pro`

| Поле              | Тип    | Обязательное |
| ----------------- | ------ | ------------ |
| `prompt`          | string | да           |
| `image_url`       | string | нет          |
| `duration`        | string | нет          |
| `negative_prompt` | string | нет          |
| `cfg_scale`       | number | нет          |

### `kling/v2-5-turbo-text-to-video-pro`

| Поле              | Тип    | Обязательное |
| ----------------- | ------ | ------------ |
| `prompt`          | string | да           |
| `duration`        | string | нет          |
| `aspect_ratio`    | string | нет          |
| `negative_prompt` | string | нет          |
| `cfg_scale`       | number | нет          |

### `runway/aleph-generate`

| Поле             | Тип     | Обязательное |
| ---------------- | ------- | ------------ |
| `prompt`         | string  | да           |
| `videoUrl`       | string  | да           |
| `callBackUrl`    | string  | нет          |
| `waterMark`      | string  | нет          |
| `uploadCn`       | boolean | нет          |
| `aspectRatio`    | string  | нет          |
| `seed`           | number  | нет          |
| `referenceImage` | string  | нет          |

### `runway/extend`

| Поле          | Тип    | Обязательное |
| ------------- | ------ | ------------ |
| `taskId`      | string | да           |
| `prompt`      | string | да           |
| `quality`     | string | да           |
| `waterMark`   | string | нет          |
| `callBackUrl` | string | нет          |

### `runway/generate`

| Поле          | Тип    | Обязательное |
| ------------- | ------ | ------------ |
| `prompt`      | string | да           |
| `imageUrl`    | string | нет          |
| `duration`    | number | нет          |
| `quality`     | string | да           |
| `aspectRatio` | string | нет          |
| `waterMark`   | string | нет          |
| `callBackUrl` | string | нет          |

### `sora-2-characters`

| Поле                 | Тип    | Обязательное |
| -------------------- | ------ | ------------ |
| `character_file_url` | array  | да           |
| `character_prompt`   | string | нет          |
| `safety_instruction` | string | нет          |

### `sora-2-characters-pro`

| Поле                  | Тип    | Обязательное |
| --------------------- | ------ | ------------ |
| `origin_task_id`      | string | да           |
| `timestamps`          | string | да           |
| `character_user_name` | string | нет          |
| `character_prompt`    | string | да           |
| `safety_instruction`  | string | нет          |

### `sora-2-image-to-video`

| Поле                | Тип     | Обязательное |
| ------------------- | ------- | ------------ |
| `prompt`            | string  | да           |
| `image_urls`        | array   | да           |
| `aspect_ratio`      | string  | нет          |
| `n_frames`          | string  | нет          |
| `remove_watermark`  | boolean | нет          |
| `character_id_list` | array   | нет          |
| `upload_method`     | string  | да           |

### `sora-2-pro-image-to-video`

| Поле                | Тип     | Обязательное |
| ------------------- | ------- | ------------ |
| `prompt`            | string  | да           |
| `image_urls`        | array   | да           |
| `aspect_ratio`      | string  | нет          |
| `n_frames`          | string  | нет          |
| `size`              | string  | нет          |
| `remove_watermark`  | boolean | нет          |
| `character_id_list` | array   | нет          |
| `upload_method`     | string  | да           |

### `sora-2-pro-storyboard`

| Поле            | Тип    | Обязательное |
| --------------- | ------ | ------------ |
| `shots`         | array  | нет          |
| `n_frames`      | string | нет          |
| `image_urls`    | array  | нет          |
| `aspect_ratio`  | string | нет          |
| `upload_method` | string | да           |

### `sora-2-pro-text-to-video`

| Поле                | Тип     | Обязательное |
| ------------------- | ------- | ------------ |
| `prompt`            | string  | да           |
| `aspect_ratio`      | string  | нет          |
| `n_frames`          | string  | нет          |
| `size`              | string  | нет          |
| `remove_watermark`  | boolean | нет          |
| `character_id_list` | array   | нет          |
| `upload_method`     | string  | да           |

### `sora-2-text-to-video`

| Поле                | Тип     | Обязательное |
| ------------------- | ------- | ------------ |
| `prompt`            | string  | да           |
| `aspect_ratio`      | string  | нет          |
| `n_frames`          | string  | нет          |
| `remove_watermark`  | boolean | нет          |
| `character_id_list` | array   | нет          |
| `upload_method`     | string  | да           |

### `sora-watermark-remover`

| Поле            | Тип    | Обязательное |
| --------------- | ------ | ------------ |
| `video_url`     | string | да           |
| `upload_method` | string | да           |

### `topaz/video-upscale`

| Поле             | Тип    | Обязательное |
| ---------------- | ------ | ------------ |
| `video_url`      | string | да           |
| `upscale_factor` | string | нет          |

### `veo3/extend`

| Поле          | Тип    | Обязательное |
| ------------- | ------ | ------------ |
| `taskId`      | string | да           |
| `prompt`      | string | да           |
| `seeds`       | number | нет          |
| `model`       | string | нет          |
| `watermark`   | string | нет          |
| `callBackUrl` | string | нет          |

### `veo3/generate`

| Поле                | Тип     | Обязательное |
| ------------------- | ------- | ------------ |
| `prompt`            | string  | да           |
| `imageUrls`         | array   | нет          |
| `model`             | string  | нет          |
| `generationType`    | string  | нет          |
| `aspect_ratio`      | string  | нет          |
| `seeds`             | number  | нет          |
| `callBackUrl`       | string  | нет          |
| `enableFallback`    | boolean | нет          |
| `enableTranslation` | boolean | нет          |
| `watermark`         | string  | нет          |

### `veo3/get-1080p`

| Поле     | Тип    | Обязательное |
| -------- | ------ | ------------ |
| `taskId` | string | да           |
| `index`  | number | нет          |

### `veo3/get-4k`

| Поле          | Тип    | Обязательное |
| ------------- | ------ | ------------ |
| `taskId`      | string | да           |
| `index`       | number | нет          |
| `callBackUrl` | string | нет          |

### `wan/2-2-a14b-image-to-video-turbo`

| Поле                      | Тип     | Обязательное |
| ------------------------- | ------- | ------------ |
| `image_url`               | string  | да           |
| `prompt`                  | string  | да           |
| `resolution`              | string  | нет          |
| `enable_prompt_expansion` | boolean | нет          |
| `seed`                    | number  | нет          |
| `acceleration`            | string  | нет          |
| `nsfw_checker`            | boolean | нет          |

### `wan/2-2-a14b-speech-to-video-turbo`

| Поле                  | Тип    | Обязательное |
| --------------------- | ------ | ------------ |
| `prompt`              | string | да           |
| `image_url`           | string | да           |
| `audio_url`           | string | да           |
| `num_frames`          | number | нет          |
| `frames_per_second`   | number | нет          |
| `resolution`          | string | нет          |
| `negative_prompt`     | string | нет          |
| `seed`                | number | нет          |
| `num_inference_steps` | number | нет          |
| `guidance_scale`      | number | нет          |
| `shift`               | number | нет          |

### `wan/2-2-a14b-text-to-video-turbo`

| Поле                      | Тип     | Обязательное |
| ------------------------- | ------- | ------------ |
| `prompt`                  | string  | да           |
| `resolution`              | string  | нет          |
| `aspect_ratio`            | string  | нет          |
| `enable_prompt_expansion` | boolean | нет          |
| `seed`                    | number  | нет          |
| `acceleration`            | string  | нет          |
| `nsfw_checker`            | boolean | нет          |

### `wan/2-2-animate-move`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `video_url`    | string  | да           |
| `image_url`    | string  | да           |
| `resolution`   | string  | нет          |
| `nsfw_checker` | boolean | нет          |

### `wan/2-2-animate-replace`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `video_url`    | string  | да           |
| `image_url`    | string  | да           |
| `resolution`   | string  | нет          |
| `nsfw_checker` | boolean | нет          |

### `wan/2-5-image-to-video`

| Поле                      | Тип     | Обязательное |
| ------------------------- | ------- | ------------ |
| `prompt`                  | string  | да           |
| `image_url`               | string  | да           |
| `duration`                | string  | да           |
| `resolution`              | string  | нет          |
| `negative_prompt`         | string  | нет          |
| `enable_prompt_expansion` | boolean | нет          |
| `seed`                    | number  | нет          |
| `nsfw_checker`            | boolean | нет          |

### `wan/2-5-text-to-video`

| Поле                      | Тип     | Обязательное |
| ------------------------- | ------- | ------------ |
| `prompt`                  | string  | да           |
| `duration`                | string  | да           |
| `aspect_ratio`            | string  | нет          |
| `resolution`              | string  | нет          |
| `negative_prompt`         | string  | нет          |
| `enable_prompt_expansion` | boolean | нет          |
| `seed`                    | number  | нет          |
| `nsfw_checker`            | boolean | нет          |

### `wan/2-6-flash-image-to-video`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `image_urls`   | array   | да           |
| `audio`        | boolean | да           |
| `duration`     | string  | нет          |
| `resolution`   | string  | нет          |
| `multi_shots`  | boolean | нет          |
| `nsfw_checker` | boolean | нет          |

### `wan/2-6-flash-video-to-video`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `video_urls`   | array   | да           |
| `duration`     | string  | нет          |
| `resolution`   | string  | нет          |
| `audio`        | boolean | нет          |
| `multi_shots`  | boolean | нет          |
| `nsfw_checker` | boolean | нет          |

### `wan/2-6-image-to-video`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `image_urls`   | array   | да           |
| `duration`     | string  | нет          |
| `resolution`   | string  | нет          |
| `nsfw_checker` | boolean | нет          |

### `wan/2-6-text-to-video`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `duration`     | string  | нет          |
| `resolution`   | string  | нет          |
| `nsfw_checker` | boolean | нет          |

### `wan/2-6-video-to-video`

| Поле           | Тип     | Обязательное |
| -------------- | ------- | ------------ |
| `prompt`       | string  | да           |
| `video_urls`   | array   | да           |
| `duration`     | string  | нет          |
| `resolution`   | string  | нет          |
| `nsfw_checker` | boolean | нет          |

### `wan/2-7-image-to-video`

| Поле                | Тип     | Обязательное |
| ------------------- | ------- | ------------ |
| `prompt`            | string  | да           |
| `negative_prompt`   | string  | нет          |
| `first_frame_url`   | string  | нет          |
| `last_frame_url`    | string  | нет          |
| `first_clip_url`    | string  | нет          |
| `driving_audio_url` | string  | нет          |
| `resolution`        | string  | нет          |
| `duration`          | number  | нет          |
| `prompt_extend`     | boolean | нет          |
| `watermark`         | boolean | нет          |
| `seed`              | number  | нет          |
| `nsfw_checker`      | boolean | нет          |

### `wan/2-7-r2v`

| Поле              | Тип     | Обязательное |
| ----------------- | ------- | ------------ |
| `prompt`          | string  | да           |
| `negative_prompt` | string  | нет          |
| `reference_image` | array   | нет          |
| `reference_video` | array   | нет          |
| `first_frame`     | string  | нет          |
| `reference_voice` | string  | нет          |
| `resolution`      | string  | нет          |
| `aspect_ratio`    | string  | нет          |
| `duration`        | number  | нет          |
| `prompt_extend`   | boolean | нет          |
| `watermark`       | boolean | нет          |
| `seed`            | number  | нет          |
| `nsfw_checker`    | boolean | нет          |

### `wan/2-7-text-to-video`

| Поле              | Тип     | Обязательное |
| ----------------- | ------- | ------------ |
| `prompt`          | string  | да           |
| `negative_prompt` | string  | нет          |
| `audio_url`       | string  | нет          |
| `resolution`      | string  | нет          |
| `ratio`           | string  | нет          |
| `duration`        | number  | нет          |
| `prompt_extend`   | boolean | нет          |
| `watermark`       | boolean | нет          |
| `seed`            | number  | нет          |
| `nsfw_checker`    | boolean | нет          |

### `wan/2-7-videoedit`

| Поле              | Тип     | Обязательное |
| ----------------- | ------- | ------------ |
| `prompt`          | string  | нет          |
| `negative_prompt` | string  | нет          |
| `video_url`       | string  | да           |
| `reference_image` | string  | нет          |
| `resolution`      | string  | нет          |
| `aspect_ratio`    | string  | нет          |
| `duration`        | number  | нет          |
| `audio_setting`   | string  | нет          |
| `prompt_extend`   | boolean | нет          |
| `watermark`       | boolean | нет          |
| `seed`            | number  | нет          |
| `nsfw_checker`    | boolean | нет          |
