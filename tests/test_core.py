"""Проверка ключевой логики без обращения к внешнему API: python3 tests/test_core.py"""
from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["AI_PROXY_DATA_DIR"] = tempfile.mkdtemp(prefix="ai-proxy-test-")

from app import config, db, docsrc, inspect, media, proxy, stats, usage  # noqa: E402

checks = 0


def check(condition: bool, label: str) -> None:
    global checks
    checks += 1
    if not condition:
        raise AssertionError(f"провалено: {label}")
    print(f"  ✓ {label}")


print("usage.extract_usage")
live_chat = {"usage": {"prompt_tokens": 19, "completion_tokens": 6, "total_tokens": 25, "cost": {"total_cost": 0.000174}}}
parsed = usage.extract_usage(live_chat)
check(parsed["total_tokens"] == 25 and parsed["cost"] == 0.000174 and parsed["cost_source"] == "api",
      "живой формат chat/completions (usage.cost.total_cost)")

doc_chat = {"usage": {"prompt_tokens": 25, "completion_tokens": 150, "total_tokens": 175, "cost_rub": 0.04131306}}
check(usage.extract_usage(doc_chat)["cost"] == 0.04131306, "формат из документации (usage.cost_rub)")

anthropic = {"usage": {"input_tokens": 19, "output_tokens": 6, "cache_read_input_tokens": 4}}
parsed = usage.extract_usage(anthropic)
check(parsed["prompt_tokens"] == 23 and parsed["completion_tokens"] == 6 and parsed["cost"] is None,
      "формат /v1/messages — токены есть, стоимости нет")

check(usage.extract_usage({"choices": []})["cost"] is None, "ответ без usage не ломает разбор")

print("usage.parse_balance")
check(usage.parse_balance('{"RUB":"1851.73"}') == 1851.73, "живой формат баланса {RUB}")
check(usage.parse_balance({"amount": "9.28591714"}) == 9.28591714, "формат баланса из документации {amount}")
check(usage.parse_balance({"data": {"amount": 5}}) == 5.0, "баланс во вложенном data")
check(usage.parse_balance("не json") is None, "мусор вместо баланса → None")

print("usage.estimate_cost — оценка по кэшу цен")
db.upsert_model_pricing([{"id": "test/model", "cost_context": "10", "cost_completion": "20", "currency": "RUB"}])
estimated = usage.estimate_cost("test/model", 1_000_000, 500_000)
check(abs(estimated - 20.0) < 1e-9, "цена за 1M токенов: 1M*10 + 0.5M*20 = 20 ₽")
check(usage.estimate_cost("unknown/model", 100, 100) is None, "нет цены — нет оценки")

entry = {"model": "test/model", "prompt_tokens": 1_000_000, "completion_tokens": 0, "cost": None}
usage.fill_cost(entry)
check(entry["cost"] == 10.0 and entry["cost_source"] == "estimated", "fill_cost подставляет оценку")
entry = {"model": "test/model", "prompt_tokens": 1, "completion_tokens": 1, "cost": 0.5}
usage.fill_cost(entry)
check(entry["cost"] == 0.5 and entry["cost_source"] == "api", "fill_cost не трогает цену от API")

print("db.apply_retention — хранение N дней")
now = datetime.now()
for age_days in (0, 3, 10):
    ts = now - timedelta(days=age_days)
    db.log_request({"ts": ts, "method": "POST", "path": "/v1/chat/completions",
                    "endpoint": "v1/chat/completions", "model": "test/model", "status_code": 200})
check(db.query("SELECT count(*) AS n FROM requests")[0]["n"] == 3, "записано 3 запроса разного возраста")
check(db.apply_retention(0) == 0, "retention_days=0 — не удаляем ничего")
removed = db.apply_retention(5)
check(removed == 1 and db.query("SELECT count(*) AS n FROM requests")[0]["n"] == 2,
      "retention_days=5 удаляет только запись 10-дневной давности")

print("docsrc.replace_domain")
sample = 'curl "https://speshu.ai/api/v1/balance"'
check(docsrc.replace_domain(sample, "localhost:8787") == 'curl "http://localhost:8787/api/v1/balance"',
      "локальный домен получает схему http")
check(docsrc.replace_domain(sample, "ai.example.com") == 'curl "https://ai.example.com/api/v1/balance"',
      "внешний домен остаётся на https")
check(docsrc.replace_domain(sample, "speshu.ai") == sample, "исходный домен не меняется")
balance_page = docsrc.page("balance", "localhost:8787")
check("speshu.ai" not in balance_page["html"],
      "на отрендеренной странице не осталось упоминаний исходного домена")
check(balance_page["ref"] == "/balance", "ярлык страницы баланса — /balance")
check("RUB" in balance_page["html"] and "amount" not in balance_page["html"],
      "документация баланса описывает реальный ответ API {RUB}, а не {amount}")
check(len(docsrc.pages()) == 12, "в сайдбаре все 12 страниц документации")
check([p["ref"] for p in docsrc.pages() if p["slug"].endswith("-models")] == ["", "", ""],
      "у страниц-каталогов ярлыка эндпоинта нет")

print("proxy — вставка предупреждения о балансе")
warning = "⚠️ мало денег\n\n"
chat = {"choices": [{"message": {"role": "assistant", "content": "Привет"}}]}
check(proxy._inject_into_payload(chat, warning, "v1/chat/completions")
      and chat["choices"][0]["message"]["content"].startswith(warning), "chat/completions: текст дополнен")
messages = {"content": [{"type": "text", "text": "Привет"}]}
check(proxy._inject_into_payload(messages, warning, "v1/messages")
      and messages["content"][0]["text"].startswith(warning), "messages: текст дополнен")
check(not proxy._inject_into_payload({"data": []}, warning, "v1/models"), "нетекстовые ответы не трогаем")

print("proxy._endpoint_label — нормализация путей")
check(proxy._endpoint_label("v1/async/media/tasks/018f3b-abc") == "v1/async/media/tasks/{task_id}",
      "id задачи заменяется на плейсхолдер")
check(proxy._endpoint_label("v1/async/media/tasks") == "v1/async/media/tasks", "список задач не меняется")
check(proxy._endpoint_label("v1/chat/completions") == "v1/chat/completions", "обычный путь без изменений")

print("inspect — разбор диалога, рассуждений и инструментов")
live_tool_response = {
    "choices": [{
        "finish_reason": "tool_calls",
        "message": {
            "role": "assistant",
            "reasoning": "Нужно вызвать get_weather с городом Москва.",
            "tool_calls": [{
                "index": 0, "type": "function", "id": "call_1",
                "function": {"name": "get_weather", "arguments": '{"city":"Москва"}'},
            }],
        },
    }],
    "usage": {
        "prompt_tokens": 134, "completion_tokens": 41, "total_tokens": 175,
        "prompt_tokens_details": {"cached_tokens": 64},
        "completion_tokens_details": {"reasoning_tokens": 21},
    },
}
request_with_tools = {
    "model": "openai/gpt-oss-20b", "temperature": 0.3, "max_tokens": 100,
    "messages": [
        {"role": "system", "content": "Ты помощник."},
        {"role": "user", "content": "Какая погода в Москве?"},
    ],
    "tools": [{"type": "function", "function": {"name": "get_weather", "description": "Погода"}}],
}
detail = inspect.summarize(request_with_tools, live_tool_response)
check(detail["request"]["system"] == "Ты помощник.", "системный промпт вынесен отдельно")
check([m["text"] for m in detail["request"]["messages"]] == ["Какая погода в Москве?"],
      "сообщения пользователя разобраны")
check([t["name"] for t in detail["request"]["tools_offered"]] == ["get_weather"],
      "предложенные инструменты видны")
check(detail["response"]["reasoning"].startswith("Нужно вызвать"), "текст рассуждений извлечён")
call = detail["response"]["tool_calls"][0]
check(call["name"] == "get_weather" and call["arguments"] == {"city": "Москва"},
      "вызов инструмента с разобранными аргументами")
check(detail["tokens"] == {"reasoning_tokens": 21, "cached_tokens": 64},
      "токены рассуждений и кэша посчитаны")

row = inspect.compact(request_with_tools, live_tool_response)
check(row["prompt_preview"] == "Какая погода в Москве?" and row["tools_called"] == "get_weather",
      "короткие поля для строки лога")
check(row["reasoning_tokens"] == 21 and row["finish_reason"] == "tool_calls",
      "в строке лога есть рассуждения и причина завершения")

multimodal = {"messages": [{"role": "user", "content": [
    {"type": "text", "text": "Что на картинке?"},
    {"type": "image_url", "image_url": {"url": "data:..."}},
]}]}
check(inspect.compact(multimodal, {})["images"] == 1, "изображения в запросе посчитаны")

anthropic_answer = {"type": "message", "stop_reason": "end_turn", "content": [
    {"type": "thinking", "thinking": "Подумаю…"},
    {"type": "text", "text": "Ответ"},
]}
parsed = inspect.summarize({}, anthropic_answer)
check(parsed["response"]["text"] == "Ответ" and parsed["response"]["reasoning"] == "Подумаю…",
      "формат /v1/messages: текст и размышления")

check(inspect.summarize(None, "не json")["response"]["text"] is None,
      "мусор вместо тела не ломает разбор")

print("proxy — склейка стрима")
acc = proxy._StreamAccumulator()
for chunk in (
    {"choices": [{"delta": {"reasoning": "Надо "}}]},
    {"choices": [{"delta": {"reasoning": "посчитать."}}]},
    {"choices": [{"delta": {"content": "Отв"}}]},
    {"choices": [{"delta": {"content": "ет"}}]},
    {"choices": [{"delta": {"tool_calls": [
        {"index": 0, "id": "t1", "function": {"name": "get_weather", "arguments": '{"ci'}}]}}]},
    {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": 'ty":"Париж"}'}}]}}]},
    {"choices": [{"finish_reason": "tool_calls", "delta": {}}]},
    {"usage": {"completion_tokens_details": {"reasoning_tokens": 7}}},
):
    acc.feed(chunk)
merged = acc.result()
check(merged["text"] == "Ответ" and merged["reasoning"] == "Надо посчитать.",
      "текст и рассуждения склеены из чанков")
check(merged["tool_calls"][0]["arguments"] == {"city": "Париж"},
      "аргументы инструмента собраны из фрагментов и разобраны")
check(merged["finish_reason"] == "tool_calls" and merged["usage"]["completion_tokens_details"]["reasoning_tokens"] == 7,
      "причина завершения и usage сохранены")
check(inspect.summarize({}, {"stream": True, **merged})["response"]["reasoning"] == "Надо посчитать.",
      "склеенный стрим разбирается как обычный ответ")

print("config — приведение типов и маскирование ключа")
saved = config.save({"api_key": "sk-abcdef123456789", "retention_days": "7", "balance_threshold": "100,5",
                     "base_url": "https://example.com/api/"})
check(saved["retention_days"] == 7 and saved["balance_threshold"] == 100.5, "строки приводятся к числам")
check(saved["base_url"] == "https://example.com/api", "завершающий слэш убирается")
check(config.masked_key("sk-abcdef123456789") == "sk-abcd…6789", "ключ маскируется")

print("config — источники")
config._cache = None
config.CONFIG_PATH.write_text('{"api_key": "sk-old", "base_url": "https://old.example/api/", "retention_days": 2}', "utf-8")
cfg = config.load()
check(len(cfg["sources"]) == 1 and cfg["sources"][0]["base_url"] == "https://old.example/api"
      and cfg["api_key"] == "sk-old" and cfg["source"] == "old-example",
      "ключ и URL из прежней конфигурации стали первым источником")
cfg = config.save({"sources": [
    {"id": "old-example", "name": "Старый", "base_url": "https://old.example/api", "api_key": "sk-old"},
    {"name": "Новый", "base_url": "https://new.example/api", "api_key": "sk-new", "active": True},
    {"name": "Новый", "base_url": "https://new.example/v2", "api_key": ""},
    {"name": "без адреса", "base_url": ""},
]})
check([s["id"] for s in cfg["sources"]] == ["old-example", "new-example", "new-example-2"],
      "id: существующий сохраняется, новый — по хосту, совпадения с суффиксом, пустой URL отброшен")
check(cfg["active_source"] == "new-example" and cfg["api_key"] == "sk-new" and cfg["base_url"] == "https://new.example/api",
      "api_key/base_url берутся из активного источника")
stored = json.loads(config.CONFIG_PATH.read_text("utf-8"))
check("api_key" not in stored and "base_url" not in stored, "производные поля в файл не пишутся")
cfg = config.save({"active_source": "нет-такого"})
check(cfg["active_source"] == "old-example", "несуществующий активный источник → первый")
cfg = config.save({"api_key": "sk-changed"})
check(cfg["sources"][0]["api_key"] == "sk-changed" and cfg["sources"][1]["api_key"] == "sk-new",
      "api_key без списка меняет только активный источник")
cfg = config.save({"port": "70000", "host": "", "cost_mode": "как-нибудь"})
check(cfg["port"] == 8787 and cfg["host"] == "127.0.0.1" and cfg["cost_mode"] == "auto",
      "неверные порт, адрес и режим стоимости → значения по умолчанию")
check(config.save({"port": "9000"})["port"] == 9000, "порт сохраняется числом")

print("config — префиксы источников")
parsed = config._coerce({"sources": [
    {"base_url": "https://a.example/api"},
    {"base_url": "https://b.example", "prefix": "Open Router"},
    {"base_url": "https://c.example", "prefix": "monitor"},
    {"base_url": "https://d.example", "prefix": "open-router"},
]})
check([s["prefix"] for s in parsed["sources"]] == ["a-example", "open-router", "monitor-2", "open-router-2"],
      "префикс: по умолчанию — id, приводится к slug, служебные и повторы получают суффикс")
check(config.find_by_prefix(parsed, "open-router")["base_url"] == "https://b.example"
      and config.find_by_prefix(parsed, "нет") is None, "поиск источника по префиксу")
routed = config.with_source(parsed, parsed["sources"][1])
check(routed["base_url"] == "https://b.example" and routed["source"] == "b-example",
      "конфигурация запроса берёт ключ и URL выбранного источника")

print("proxy — баланс по источникам")
proxy.observe_balance(50.0, upstream="src-low")
proxy.observe_balance(900.0, upstream="src-rich")
check(proxy.cached_balance("src-low") == 50.0 and proxy.cached_balance("src-rich") == 900.0,
      "у каждого источника свой кэш баланса")
low_cfg = {"balance_threshold": 100.0, "source": "src-low"}
check(proxy.balance_warning(low_cfg) is not None
      and proxy.balance_warning({**low_cfg, "source": "src-rich"}) is None,
      "предупреждение — по балансу того источника, куда ушёл запрос")
proxy._apply_local_cost(10.0, "src-rich")
check(proxy.cached_balance("src-rich") == 890.0 and proxy.cached_balance("src-low") == 50.0,
      "стоимость запроса списывается только с его источника")

print("usage.fill_cost — режимы расчёта")
db.upsert_model_pricing([{"id": "m/priced", "cost_context": 1, "cost_completion": 2}], "src-a")
base = {"model": "m/priced", "upstream": "src-a", "prompt_tokens": 1_000_000, "completion_tokens": 1_000_000}
entry = {**base, "cost": 5.0}
usage.fill_cost(entry, "auto")
check(entry["cost"] == 5.0 and entry["cost_source"] == "api" and entry["cost_estimated"] == 3.0,
      "auto: цена API, оценка по прайсу сохранена рядом")
entry = {**base, "cost": 5.0}
usage.fill_cost(entry, "pricelist")
check(entry["cost"] == 3.0 and entry["cost_source"] == "estimated" and entry["cost_api"] == 5.0,
      "pricelist: оценка по прайсу, цена API сохранена рядом")
entry = {**base, "cost": None}
usage.fill_cost(entry, "api")
check(entry["cost"] is None and entry["cost_source"] is None and entry["cost_estimated"] == 3.0,
      "api: без цены в ответе стоимости нет")
entry = {**base, "upstream": "src-b", "cost": None}
usage.fill_cost(entry, "auto")
check(entry["cost"] is None, "прайс другого источника не применяется")

print("db.recompute_costs — смена режима пересчитывает историю")
rid = db.log_request({**base, "method": "POST", "path": "/v1/chat/completions", "status_code": 200,
                      "cost": 5.0, "cost_source": "api", "cost_api": 5.0, "cost_estimated": 3.0})
cost_of = lambda: db.query("SELECT cost, cost_source FROM requests WHERE id = ?", [rid])[0]
db.recompute_costs("pricelist")
check(cost_of() == {"cost": 3.0, "cost_source": "estimated"}, "pricelist → оценка")
db.recompute_costs("api")
check(cost_of() == {"cost": 5.0, "cost_source": "api"}, "api → цена из ответа")

print("db.migrate — записи прежних версий")
db.execute("INSERT INTO requests (ts, day, model, prompt_tokens, completion_tokens, cost, cost_source) "
           "VALUES (now(), current_date, 'm/priced', 1000000, 0, 7.0, 'api')")
db.execute("INSERT INTO balance_snapshots (ts, day, amount, source) VALUES (now(), current_date, 10, 'poll')")
db.execute("INSERT INTO model_pricing VALUES ('m/legacy', 4, 4, 'RUB', now())")
db.migrate("src-a")
legacy = db.query("SELECT upstream, cost_api, cost_estimated FROM requests WHERE cost = 7.0")[0]
check(legacy == {"upstream": "src-a", "cost_api": 7.0, "cost_estimated": 1.0},
      "источник проставлен, цена API перенесена, оценка по прайсу досчитана")
check(db.latest_balance("src-a")["amount"] == 10.0 and db.latest_balance("другой") is None,
      "снимки баланса привязаны к источнику")
check(db.model_pricing("m/legacy", "src-a") is not None, "прайс из старой таблицы перенесён в источник")

print("media — картинки из тел")
png = base64.b64encode(b"\x89PNG\r\n\x1a\n" + bytes(range(256)) * 4).decode()
chat = {"model": "v/vision", "messages": [{"role": "user", "content": [
    {"type": "text", "text": "Что на картинке?"},
    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{png}"}},
    {"type": "image_url", "image_url": {"url": "https://cdn.example/cat.jpg"}},
]}]}
rewritten, found = media.extract_request(chat)
ref = rewritten["messages"][0]["content"][1]["image_url"]["url"]
check(ref.startswith("media://") and ref.endswith(".png") and (config.MEDIA_DIR / ref[8:]).is_file(),
      "data:-картинка сохранена файлом, в теле — ссылка media://")
check(chat["messages"][0]["content"][1]["image_url"]["url"].startswith("data:"),
      "исходный запрос (уходит в апстрим) не изменён")
check([i["url"] or i["file"] for i in found.items] == [ref[8:], "https://cdn.example/cat.jpg"],
      "учтены и файл, и внешняя ссылка")
_, again = media.extract_request(chat)
check(again.items[0]["file"] == found.items[0]["file"], "одинаковая картинка → тот же файл (имя — хэш)")

anthropic_req = {"messages": [{"role": "user", "content": [
    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": png}}]}]}
rewritten, found = media.extract_request(anthropic_req)
check(rewritten["messages"][0]["content"][0]["source"]["data"].endswith(".jpg") and found.items[0]["mime"] == "image/jpeg",
      "/v1/messages: source.data сохранён с типом из media_type")

task = {"model": "q/edit", "input": {"prompt": "улучши", "image_url": "https://i.example/a.png",
                                     "reference_image_urls": ["https://i.example/b.png"], "aspect_ratio": "1:1"}}
_, found = media.extract_request(task)
check([i["url"] for i in found.items] == ["https://i.example/a.png", "https://i.example/b.png"] and found.prompt == "улучши",
      "медиа-задача: входные картинки по ключам *image*, промпт для подписи")

status = {"data": {"state": "success", "prompt": "кот",
                   "inputParams": {"image_url": "https://i.example/input.png"},
                   "resultJson": '{"resultUrls":["https://r.example/out.webp","https://r.example/out.mp4"]}'}}
_, found = media.extract_response(status)
check([(i["url"], i["kind"]) for i in found.items] == [("https://r.example/out.webp", "image"), ("https://r.example/out.mp4", "video")],
      "статус задачи: результаты из resultUrls, входные параметры результатом не считаются")
generated = {"created": 1, "data": [{"b64_json": png}]}
rewritten, found = media.extract_response(generated)
check(rewritten["data"][0]["b64_json"].startswith("media://") and found.items[0]["direction"] == "output",
      "images/generations: b64_json сохранён файлом")
check(media.extract_response({"object": "list", "data": [{"id": "x", "url": "https://docs.example"}]})[1].items == [],
      "каталоги с data-списком картинками не считаются")
check(media.rewrite_body('{"a": 1}', {"a": 1}, {"a": 1}, media.Collector("input")) == '{"a": 1}',
      "без встроенных данных тело в логе остаётся исходным текстом")

print("inspect — картинки в карточке")
body = json.dumps(media.extract_request(chat)[0])
detail = inspect.summarize(body, json.dumps(status))
message = detail["request"]["messages"][0]
check(message["images"] == 2 and message["media"][0].startswith("/_media/") and message["media"][1] == "https://cdn.example/cat.jpg",
      "картинки сообщения — ссылки для браузера")
check(detail["response"]["media"]["urls"][0] == "https://r.example/out.webp", "результаты задачи в карточке")
check(inspect.compact(body, json.dumps(status))["media_out"] == 2, "в строке лога посчитаны медиа в ответе")
task_detail = inspect.summarize(task, {})
check(task_detail["request"]["messages"][0]["media"] == ["https://i.example/a.png", "https://i.example/b.png"]
      and task_detail["request"]["params"] == {"aspect_ratio": "1:1"},
      "карточка медиа-задачи: промпт, входные картинки, параметры")
check(inspect.summarize({}, generated)["response"]["images"] == [], "b64 без сохранения в карточку не тащим")
check(inspect.summarize({}, media.extract_response(generated)[0])["response"]["images"][0].startswith("/_media/"),
      "сгенерированная картинка в карточке — ссылка на файл")

print("db — галерея и ретеншен файлов")
_, inputs = media.extract_request(chat)
old_ts = datetime.now() - timedelta(days=30)
first = db.log_request({"ts": old_ts, "method": "POST", "path": "/v1/chat/completions", "model": "v/vision",
                        "upstream": "src-a", "request_body": json.dumps(chat), "media": inputs.items})
second = db.log_request({"ts": old_ts + timedelta(days=1), "method": "POST", "model": "v/vision",
                         "upstream": "src-a", "media": inputs.items})
row = db.query("SELECT request_id, last_request_id, uses, prompt FROM media WHERE key = ?", [inputs.items[0]["key"]])[0]
check(row["request_id"] == first and row["last_request_id"] == second and row["uses"] == 2
      and row["prompt"] == "Что на картинке?", "повтор картинки не дублирует её, а обновляет последнее упоминание")
page = stats.media_page({"direction": "input"})
check(page["total"] == 2 and page["items"][0]["src"].startswith(("/_media/", "https://")), "страница галереи")
saved = config.MEDIA_DIR / inputs.items[0]["file"]
db.apply_retention(7)
check(not saved.exists() and not db.query("SELECT 1 FROM media"), "ретеншен удаляет старые медиа и их файлы")

print("галерея — полный промпт в подписи")
long_prompt = "Опиши картинку подробно. " * 40
long_chat = {"messages": [{"role": "user", "content": [
    {"type": "text", "text": long_prompt},
    {"type": "image_url", "image_url": {"url": "https://cdn.example/long.jpg"}}]}]}
_, found = media.extract_request(long_chat)
db.log_request({"method": "POST", "path": "/v1/chat/completions", "model": "v/long",
                "request_body": json.dumps(long_chat), "media": found.items})
caption = db.query("SELECT prompt FROM media WHERE url = 'https://cdn.example/long.jpg'")[0]["prompt"]
check(caption == long_prompt, "подпись — полный промпт, а не превью в 400 символов")
db.execute("UPDATE media SET prompt = ?, prompt_full = FALSE WHERE url = 'https://cdn.example/long.jpg'",
           [long_prompt[:400]])
check(db.refresh_media_prompts() >= 1
      and db.query("SELECT prompt FROM media WHERE url = 'https://cdn.example/long.jpg'")[0]["prompt"] == long_prompt,
      "старые обрезанные подписи пересобираются из тела запроса")
check(db.refresh_media_prompts() == 0, "повторный проход ничего не делает")

print("stats.request_page — страница записи для ссылки")
ids = [db.log_request({"method": "GET", "path": "/v1/models", "endpoint": "v1/models", "model": "page/test"})
       for _ in range(5)]
check(stats.request_page(ids[-1], {"model": "page/test"}, 2) == 1
      and stats.request_page(ids[0], {"model": "page/test"}, 2) == 3,
      "свежая запись — на первой странице, старая — дальше")
check(stats.request_page(ids[0], {"model": "другая"}, 2) is None and stats.request_page(10**9, {}, 2) is None,
      "не проходит фильтры или не существует → None")

print("db.backfill_media — картинки из старых записей")
db.execute("INSERT INTO requests (ts, day, model, request_body, media_scanned) VALUES (now(), current_date, 'v/old', ?, FALSE)",
           [json.dumps(chat)])
check(db.backfill_media() >= 1 and db.query("SELECT count(*) AS n FROM media WHERE model = 'v/old'")[0]["n"] == 2,
      "в старых записях найдены и сохранены картинки")
check(db.backfill_media() == 0, "повторный проход ничего не делает")

db.close()
print(f"\nВсе проверки пройдены: {checks}")
