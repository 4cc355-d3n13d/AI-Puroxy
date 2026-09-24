#!/usr/bin/env bash
# Запуск прокси: ./run.sh [порт] [аргументы uvicorn…]
#
# Адрес и порт по умолчанию — из настроек (/settings, data/config.json); изначально
# это 127.0.0.1:8787. Разово переопределить: ./run.sh 9000, AI_PROXY_HOST=0.0.0.0 ./run.sh
set -euo pipefail

cd "$(dirname "$0")"
RED='\033[0;31m' # Red Color
NC='\033[0m' # No Color

if [ ! -d .venv ]; then
  ./install.sh
fi

PORT="${1:-${AI_PROXY_PORT:-$(./.venv/bin/python -m app.config get port 2>/dev/null || echo 8787)}}"
HOST="${AI_PROXY_HOST:-$(./.venv/bin/python -m app.config get host 2>/dev/null || echo 127.0.0.1)}"

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

# фактический адрес нужен странице настроек, чтобы подсказать про перезапуск
export AI_PROXY_LISTEN="${HOST}:${PORT}"
exec ./.venv/bin/python -m uvicorn app.main:app --host "${HOST}" --port "${PORT}" "${@:2}"

printf "\n🙋 ${RED}Всего наилучего, до скорых встреч${NC}!!\n\n"
