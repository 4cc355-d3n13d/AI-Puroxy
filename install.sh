#!/usr/bin/env bash
echo "→ создаю виртуальное окружение…"
python3 -m venv .venv
echo "→ устанавливаю зависимости окружения… (1/2)"
./.venv/bin/pip install --quiet --upgrade pip
echo "→ устанавливаю зависимости приложения… (2/2)"
./.venv/bin/pip install --quiet -r requirements.txt
echo "→ установка зависимостей завершена ✅"
