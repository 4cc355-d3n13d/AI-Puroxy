#!/usr/bin/env bash
# Запуск прокси: ./run.sh [порт]
#
# По умолчанию слушает только localhost. Чтобы открыть доступ из локальной сети:
#   AI_PROXY_HOST=0.0.0.0 ./run.sh
set -euo pipefail

cd "$(dirname "$0")"
PORT="${1:-8787}" # Set Proxy Port Number
HOST="${AI_PROXY_HOST:-127.0.0.1}" # Proxy Host to listen on
RED='\033[0;31m' # Red Color
NC='\033[0m' # No Color

# Прокси держит базу DuckDB эксклюзивно: второй экземпляр её не откроет.
# Чаще всего порт уже занят сервисом, который сам стартовал после перезагрузки.
BUSY_PID="$(lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN -t 2>/dev/null | head -1 || true)"
if [ -n "$BUSY_PID" ]; then
  printf "${RED}⚠️  Порт %s уже занят процессом %s — прокси похоже уже запущен.${NC}\n" "$PORT" "$BUSY_PID"
  echo "    Проверьте:  ./service.sh status"
  echo "    Остановить: ./service.sh stop     (если нужен ручной запуск)"
  echo "    Или возьмите свободный порт: ./run.sh 8788"
  exit 1
fi

if [ ! -d .venv ]; then
  ./reset.sh
  # echo "→ удаляю виртуальное окружение…"
  # rm -rf ./.venv
  # echo "→ пересоздаю виртуальное окружение…"
  # python3 -m venv .venv
  # echo "→ устанавливаю зависимости окружения (1/2)…"
  # ./.venv/bin/pip install --quiet --upgrade pip
  # echo "→ устанавливаю зависимости приложения (2/2)…"
  # ./.venv/bin/pip install --quiet -r requirements.txt
  # echo "→ установка зависимостей завершена ✅"
fi

echo "→ интерфейс: http://localhost:${PORT}/monitor"

if [ "$HOST" != "127.0.0.1" ] && [ "$HOST" != "localhost" ]; then
  LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || true)"
  [ -n "$LAN_IP" ] && echo "→ из локальной сети: http://${LAN_IP}:${PORT}/monitor"
  
  printf '\n👋 Добро пожаловать в ИИ-ПРОКСИ!\n\n'

  printf "${RED}"
  echo "⚠️  Прокси открыт наружу (${HOST}) и работает без аутентификации:"
  echo "    любой, кто дотянется до порта, сможет тратить баланс и увидеть API-ключ в /settings."
  printf "${NC}"
fi

exec ./.venv/bin/python -m uvicorn app.main:app --host "${HOST}" --port "${PORT}" "${@:2}"

printf "\n🙋 ${RED}Всего наилучего, до скорых встреч${NC}!!\n\n"
