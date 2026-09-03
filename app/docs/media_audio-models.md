> ## Documentation Index
> Fetch the complete documentation index at: https://speshu.ai/docs/llms.txt
> Use this file to discover all available pages before exploring further.

# Модели музыки и аудио

> Параметры моделей для TTS, STT, sound effects и генерации музыки

Здесь собраны модели музыки и аудио. Используйте ID модели в поле `model`.

<Note>
  Передавайте параметры модели в поле `input` при создании задачи через `POST /async/media/tasks`. Актуальную схему можно получить через `GET /media/models`.
</Note>

## Модели

### `elevenlabs/audio-isolation`

| Поле        | Тип    | Обязательное |
| ----------- | ------ | ------------ |
| `audio_url` | string | да           |

### `elevenlabs/sound-effect-v2`

| Поле               | Тип     | Обязательное |
| ------------------ | ------- | ------------ |
| `text`             | string  | да           |
| `loop`             | boolean | нет          |
| `duration_seconds` | number  | нет          |
| `prompt_influence` | number  | нет          |
| `output_format`    | string  | нет          |

### `elevenlabs/speech-to-text`

| Поле               | Тип     | Обязательное |
| ------------------ | ------- | ------------ |
| `audio_url`        | string  | да           |
| `language_code`    | string  | нет          |
| `tag_audio_events` | boolean | нет          |
| `diarize`          | boolean | нет          |

### `elevenlabs/text-to-dialogue-v3`

| Поле            | Тип    | Обязательное |
| --------------- | ------ | ------------ |
| `dialogue`      | array  | да           |
| `stability`     | number | нет          |
| `language_code` | string | нет          |

### `elevenlabs/text-to-speech-multilingual-v2`

| Поле               | Тип     | Обязательное |
| ------------------ | ------- | ------------ |
| `text`             | string  | да           |
| `voice`            | string  | да           |
| `stability`        | number  | нет          |
| `similarity_boost` | number  | нет          |
| `style`            | number  | нет          |
| `speed`            | number  | нет          |
| `timestamps`       | boolean | нет          |
| `previous_text`    | string  | нет          |
| `next_text`        | string  | нет          |
| `language_code`    | string  | нет          |

### `elevenlabs/text-to-speech-turbo-2-5`

| Поле               | Тип     | Обязательное |
| ------------------ | ------- | ------------ |
| `text`             | string  | да           |
| `voice`            | string  | нет          |
| `stability`        | number  | нет          |
| `similarity_boost` | number  | нет          |
| `style`            | number  | нет          |
| `speed`            | number  | нет          |
| `timestamps`       | boolean | нет          |
| `previous_text`    | string  | нет          |
| `next_text`        | string  | нет          |
| `language_code`    | string  | нет          |

### `suno/add-instrumental`

| Поле                  | Тип    | Обязательное |
| --------------------- | ------ | ------------ |
| `uploadUrl`           | string | да           |
| `model`               | string | нет          |
| `title`               | string | да           |
| `negativeTags`        | string | да           |
| `tags`                | string | да           |
| `callBackUrl`         | string | да           |
| `vocalGender`         | string | нет          |
| `styleWeight`         | number | нет          |
| `weirdnessConstraint` | number | нет          |
| `audioWeight`         | number | нет          |

### `suno/add-vocals`

| Поле                  | Тип    | Обязательное |
| --------------------- | ------ | ------------ |
| `prompt`              | string | да           |
| `model`               | string | нет          |
| `title`               | string | да           |
| `negativeTags`        | string | да           |
| `style`               | string | да           |
| `vocalGender`         | string | нет          |
| `styleWeight`         | number | нет          |
| `weirdnessConstraint` | number | нет          |
| `audioWeight`         | number | нет          |
| `uploadUrl`           | string | да           |
| `callBackUrl`         | string | да           |

### `suno/boost-music-style`

| Поле      | Тип    | Обязательное |
| --------- | ------ | ------------ |
| `content` | string | да           |

### `suno/convert-to-wav`

| Поле          | Тип    | Обязательное |
| ------------- | ------ | ------------ |
| `taskId`      | string | да           |
| `audioId`     | string | да           |
| `callBackUrl` | string | да           |

### `suno/create-music-video`

| Поле          | Тип    | Обязательное |
| ------------- | ------ | ------------ |
| `taskId`      | string | да           |
| `audioId`     | string | да           |
| `callBackUrl` | string | да           |
| `author`      | string | нет          |
| `domainName`  | string | нет          |

### `suno/extend-music`

| Поле                  | Тип     | Обязательное |
| --------------------- | ------- | ------------ |
| `defaultParamFlag`    | boolean | да           |
| `audioId`             | string  | да           |
| `prompt`              | string  | да           |
| `style`               | string  | нет          |
| `title`               | string  | нет          |
| `continueAt`          | number  | нет          |
| `model`               | string  | да           |
| `callBackUrl`         | string  | да           |
| `negativeTags`        | string  | нет          |
| `vocalGender`         | string  | нет          |
| `styleWeight`         | number  | нет          |
| `weirdnessConstraint` | number  | нет          |
| `audioWeight`         | number  | нет          |
| `personaId`           | string  | нет          |

### `suno/generate-cover`

| Поле          | Тип    | Обязательное |
| ------------- | ------ | ------------ |
| `taskId`      | string | да           |
| `callBackUrl` | string | да           |

### `suno/generate-lyrics`

| Поле          | Тип    | Обязательное |
| ------------- | ------ | ------------ |
| `prompt`      | string | да           |
| `callBackUrl` | string | да           |

### `suno/generate-mashup`

| Поле                  | Тип     | Обязательное |
| --------------------- | ------- | ------------ |
| `uploadUrlList`       | array   | да           |
| `prompt`              | string  | нет          |
| `style`               | string  | нет          |
| `title`               | string  | нет          |
| `customMode`          | boolean | да           |
| `instrumental`        | boolean | нет          |
| `model`               | string  | да           |
| `callBackUrl`         | string  | да           |
| `vocalGender`         | string  | нет          |
| `styleWeight`         | number  | нет          |
| `weirdnessConstraint` | number  | нет          |
| `audioWeight`         | number  | нет          |

### `suno/generate-midi`

| Поле          | Тип    | Обязательное |
| ------------- | ------ | ------------ |
| `taskId`      | string | да           |
| `callBackUrl` | string | да           |
| `audioId`     | string | нет          |

### `suno/generate-music`

| Поле                  | Тип     | Обязательное |
| --------------------- | ------- | ------------ |
| `prompt`              | string  | да           |
| `style`               | string  | нет          |
| `title`               | string  | нет          |
| `customMode`          | boolean | да           |
| `instrumental`        | boolean | да           |
| `model`               | string  | да           |
| `callBackUrl`         | string  | да           |
| `negativeTags`        | string  | нет          |
| `vocalGender`         | string  | нет          |
| `styleWeight`         | number  | нет          |
| `weirdnessConstraint` | number  | нет          |
| `audioWeight`         | number  | нет          |
| `personaId`           | string  | нет          |

### `suno/generate-persona`

| Поле          | Тип    | Обязательное |
| ------------- | ------ | ------------ |
| `taskId`      | string | да           |
| `audioId`     | string | да           |
| `name`        | string | да           |
| `description` | string | да           |
| `vocalStart`  | number | нет          |
| `vocalEnd`    | number | нет          |
| `style`       | string | нет          |

### `suno/generate-sounds`

| Поле          | Тип     | Обязательное |
| ------------- | ------- | ------------ |
| `prompt`      | string  | да           |
| `model`       | string  | нет          |
| `soundLoop`   | boolean | нет          |
| `soundTempo`  | number  | нет          |
| `soundKey`    | string  | нет          |
| `grabLyrics`  | boolean | нет          |
| `callBackUrl` | string  | нет          |

### `suno/replace-section`

| Поле           | Тип    | Обязательное |
| -------------- | ------ | ------------ |
| `taskId`       | string | да           |
| `audioId`      | string | да           |
| `prompt`       | string | да           |
| `tags`         | string | да           |
| `title`        | string | да           |
| `negativeTags` | string | нет          |
| `infillStartS` | number | да           |
| `infillEndS`   | number | да           |
| `fullLyrics`   | string | нет          |
| `callBackUrl`  | string | нет          |

### `suno/separate-vocals`

| Поле          | Тип    | Обязательное |
| ------------- | ------ | ------------ |
| `taskId`      | string | да           |
| `audioId`     | string | да           |
| `type`        | string | нет          |
| `callBackUrl` | string | да           |

### `suno/upload-and-cover-audio`

| Поле                  | Тип     | Обязательное |
| --------------------- | ------- | ------------ |
| `uploadUrl`           | string  | да           |
| `prompt`              | string  | да           |
| `style`               | string  | нет          |
| `title`               | string  | нет          |
| `customMode`          | boolean | да           |
| `instrumental`        | boolean | да           |
| `model`               | string  | да           |
| `negativeTags`        | string  | нет          |
| `callBackUrl`         | string  | да           |
| `vocalGender`         | string  | нет          |
| `styleWeight`         | number  | нет          |
| `weirdnessConstraint` | number  | нет          |
| `audioWeight`         | number  | нет          |
| `personaId`           | string  | нет          |

### `suno/upload-and-extend-audio`

| Поле                  | Тип     | Обязательное |
| --------------------- | ------- | ------------ |
| `uploadUrl`           | string  | да           |
| `defaultParamFlag`    | boolean | да           |
| `instrumental`        | boolean | да           |
| `prompt`              | string  | нет          |
| `style`               | string  | нет          |
| `title`               | string  | нет          |
| `continueAt`          | number  | да           |
| `model`               | string  | да           |
| `negativeTags`        | string  | нет          |
| `callBackUrl`         | string  | да           |
| `vocalGender`         | string  | нет          |
| `styleWeight`         | number  | нет          |
| `weirdnessConstraint` | number  | нет          |
| `audioWeight`         | number  | нет          |
| `personaId`           | string  | нет          |
