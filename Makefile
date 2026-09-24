# AI Monitoring Proxy — частые команды. Список: make (или make help).
# Обёртка над скриптами репозитория: логика живёт в *.sh, здесь только короткие имена.

PY   := ./.venv/bin/python
PORT ?=

.DEFAULT_GOAL := help
.PHONY: help install reinstall run run-lan dev test test-core test-web \
        service-install status start stop restart logs service-uninstall \
        config backup

help: ## показать список команд
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo
	@echo "  Порт разово: make run PORT=9000   (иначе — из настроек, data/config.json)"

# ---------------------------------------------------------------- окружение

install: ## создать .venv и поставить зависимости
	./install.sh

reinstall: ## пересоздать .venv с нуля
	./reset.sh
	./install.sh

# ---------------------------------------------------------------- запуск без сервиса

run: ## запустить в переднем плане (адрес и порт из настроек)
	./run.sh $(PORT)

run-lan: ## то же, но с доступом из локальной сети (0.0.0.0)
	./run-all.sh $(PORT)

dev: ## режим разработки: перезапуск при правке кода
	./run.sh $(or $(PORT),$(shell $(PY) -m app.config get port 2>/dev/null || echo 8787)) --reload

# ---------------------------------------------------------------- тесты

test: test-core test-web ## все тесты

test-core: ## логика: usage, баланс, источники, медиа, ретеншен
	$(PY) tests/test_core.py

test-web: ## HTTP: страницы, /_api/*, форма настроек
	$(PY) tests/test_web.py

# ---------------------------------------------------------------- сервис (launchd / systemd)

service-install: ## установить сервис (или обновить описание старого формата)
	./service.sh install

status: ## состояние сервиса: адрес, порт, отвечает ли
	./service.sh status

start: ## запустить сервис
	./service.sh start

stop: ## остановить сервис
	./service.sh stop

restart: ## перезапустить сервис (например, после git pull)
	./service.sh restart

logs: ## хвост журнала сервиса
	./service.sh logs

service-uninstall: ## снять сервис; data/ не трогается
	./service.sh uninstall

# ---------------------------------------------------------------- данные

config: ## показать настройки (ключи замаскированы)
	@$(PY) -c "import json; from app import config as c; d = c.load(); \
	[s.update(api_key=c.masked_key(s['api_key'])) for s in d['sources']]; \
	[d.pop(k) for k in ('api_key', 'base_url', 'source')]; \
	print(json.dumps(d, ensure_ascii=False, indent=2))"

backup: ## копия базы, настроек, картинок и логотипа в data/backup-<время>/ (сервис на время копирования останавливается)
	@dir=data/backup-$$(date +%Y%m%d-%H%M%S); \
	running=$$(./service.sh status 2>/dev/null | grep '^Сервис:' | grep -vq 'не загружен' && echo 1); \
	[ -z "$$running" ] || ./service.sh stop; \
	mkdir -p $$dir && cp data/proxy.duckdb* data/config.json $$dir/ 2>/dev/null; \
	[ ! -d data/media ] || cp -R data/media $$dir/; \
	[ ! -d data/brand ] || cp -R data/brand $$dir/; \
	[ -z "$$running" ] || ./service.sh start; \
	echo "→ сохранено в $$dir"
