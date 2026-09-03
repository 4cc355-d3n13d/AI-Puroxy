# Внутренний API интерфейса (`/_api/*`)

Эндпоинты, которыми пользуются страницы. Префикс `/_api` выбран так, чтобы не
пересекаться с проксируемыми путями (`/v1/…`, `/api/v1/…`). Авторизации нет —
сервис рассчитан на локальный запуск.

Все даты и время сериализуются строками: `YYYY-MM-DD` и `YYYY-MM-DD HH:MM:SS`.
Деньги — числа в рублях, `null` означает «неизвестно».

---

## `GET /_api/overview`

Сводка для карточек и чипа баланса в шапке.

```json
{
  "requests": 22, "cost": 0.003723, "tokens": 615, "errors": 1, "models": 4,
  "today_requests": 22, "today_cost": 0.003723,
  "balance": 1851.73, "balance_checked_at": "2026-08-15 08:35:04",
  "balance_threshold": 0.0, "configured": true, "low_balance": false
}
```

Если баланс ещё не известен и прокси настроен — делается запрос к апстриму.

## `GET /_api/requests`

Постраничный лог.

| Параметр                | Описание                                      |
| ----------------------- | --------------------------------------------- |
| `model`, `endpoint`     | Точное совпадение                             |
| `status`                | `ok` (< 400) или `error` (≥ 400 либо есть `error`) |
| `q`                     | Подстрока в теле запроса/ответа, модели или пути (`ILIKE`) |
| `date_from`, `date_to`  | Границы по `day`, включительно                |
| `page`, `page_size`     | Страница с 1, размер до 200                   |

```json
{"items": [...], "total": 22, "page": 1, "page_size": 50, "pages": 1}
```

Тела запроса и ответа в списке **не отдаются** — только их размеры
(`request_size`, `response_size`), чтобы список оставался лёгким.

## `GET /_api/requests/{id}`

Полная запись, включая `request_body` и `response_body`. `404`, если записи нет.

Для стриминга `response_body` — это JSON:

```json
{"stream": true, "text": "собранный текст ответа", "events": 42, "raw": "последние события SSE"}
```

## `GET /_api/filters`

Значения для выпадающих списков с количествами:
`{"models": [{"model": "...", "n": 9}], "endpoints": [{"endpoint": "...", "n": 12}]}`.

## `GET /_api/chart`

Данные графика. Параметры: `days` (по умолчанию 30), `model` (необязательный фильтр).

```json
{"series": [{"day": "2026-08-15", "total": 22, "models": {"google/gemma-3n-e4b-it": 9}}],
 "models": ["google/gemma-3n-e4b-it", "прочие"], "days": 30}
```

В `models` — до восьми самых частых за период; остальные схлопываются в `прочие`.
Дни без запросов присутствуют в `series` с нулями, чтобы шкала не «сжималась».
Запросы без модели (баланс, каталоги, статусы задач) идут под ключом `—`.

## `GET /_api/models`

Рейтинг моделей за всё время, отсортирован по числу запросов:
`model, requests, errors, prompt_tokens, completion_tokens, cost, avg_duration_ms,
first_used, last_used`.

## `GET /_api/balance/calendar`

Календарь трат. Параметр `month` в формате `YYYY-MM`, по умолчанию — текущий.

```json
{
  "month": "2026-08", "first_day": "2026-08-01", "last_day": "2026-08-31",
  "weekday_offset": 5,
  "days": [{"day": "2026-08-01", "cost": 0.0, "requests": 0,
            "balance_start": null, "balance_end": null}],
  "total_cost": 0.0037, "total_requests": 22,
  "prev_month": "2026-07", "next_month": "2026-09",
  "balance": 1851.73, "balance_checked_at": "2026-08-15 08:35:04"
}
```

`weekday_offset` — сколько пустых ячеек нарисовать перед первым числом (неделя с понедельника).

## `GET /_api/balance/day/{day}`

Детализация за день (`YYYY-MM-DD`): разбивка по моделям и эндпоинтам плюс сверка
с фактическим балансом.

```json
{
  "day": "2026-08-15",
  "models": [{"model": "google/gemma-3n-e4b-it", "requests": 9, "cost": 0.0016,
              "prompt_tokens": 178, "completion_tokens": 55, "estimated": 2}],
  "endpoints": [{"endpoint": "v1/chat/completions", "requests": 12, "cost": 0.0035}],
  "total_cost": 0.003723, "total_requests": 22,
  "balance_delta": 0.0038, "balance_start": 1851.74, "balance_end": 1851.73
}
```

* `estimated` — сколько запросов в группе посчитаны по прайсу, а не по ответу API.
* `balance_delta` — `balance_start - balance_end`, то есть положительное значение
  означает траты. `null`, если за день меньше двух снимков баланса.

## `POST /_api/balance/refresh`

Принудительно запрашивает баланс у апстрима и пишет снимок.
Отвечает `{"balance": 1851.73, "checked_at": "2026-08-15"}`.

---

## Страницы и их параметры в URL

| Страница   | Параметры                                                    |
| ---------- | ------------------------------------------------------------ |
| `/monitor` | `model`, `endpoint`, `status`, `q`, `day` — подставляются в фильтры и синхронизируются обратно в адресную строку |
| `/balance` | `month` (`YYYY-MM`), `day` (`YYYY-MM-DD`) — выбранный день в календаре |
| `/docs`    | Редирект на первую страницу; `/docs/{slug}` — конкретная      |
| `/settings`| `saved=1` — показать подтверждение сохранения                 |

Переходы между страницами построены на этих параметрах: клик по модели на `/models`
ведёт в `/monitor?model=…`, клик по столбцу графика проставляет фильтр по дню,
ссылка «лог за день» на `/balance` — в `/monitor?day=…`.
