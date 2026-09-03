"""Проверка ключевой логики без обращения к внешнему API: python3 tests/test_core.py"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["AI_PROXY_DATA_DIR"] = tempfile.mkdtemp(prefix="ai-proxy-test-")

from app import config, db, docsrc, inspect, proxy, usage  # noqa: E402

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

db.close()
print(f"\nВсе проверки пройдены: {checks}")
