#!/usr/bin/env bash
# Установка прокси как сервиса, который стартует сам и переживает перезагрузку.
#
#   ./service.sh install              — поставить и запустить (только localhost)
#   ./service.sh install --host 0.0.0.0 --port 9000
#   ./service.sh status               — состояние
#   ./service.sh start|stop|restart   — управление
#   ./service.sh logs                 — хвост журнала
#   ./service.sh uninstall            — снять сервис (данные и настройки остаются)
#
# macOS — LaunchAgent (~/Library/LaunchAgents), Linux — systemd --user.
set -euo pipefail

cd "$(dirname "$0")"
PROJECT_DIR="$(pwd -P)"

LABEL="com.aipuroxy.proxy"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
UNIT_NAME="ai-puroxy.service"
UNIT="$HOME/.config/systemd/user/${UNIT_NAME}"
LOG_DIR="$PROJECT_DIR/data/logs"
LOG_OUT="$LOG_DIR/service.log"
LOG_ERR="$LOG_DIR/service.err.log"

PORT="${AI_PROXY_PORT:-8787}"
HOST="${AI_PROXY_HOST:-127.0.0.1}"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; NC='\033[0m'

case "$(uname -s)" in
  Darwin) PLATFORM="macos" ;;
  Linux)  PLATFORM="linux" ;;
  *) echo "Неизвестная система $(uname -s): поддерживаются macOS и Linux." >&2; exit 1 ;;
esac

# --------------------------------------------------------------------- разбор аргументов

COMMAND="${1:-}"
shift || true
PORT_GIVEN=""
HOST_GIVEN=""
while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; PORT_GIVEN=1; shift 2 ;;
    --host) HOST="$2"; HOST_GIVEN=1; shift 2 ;;
    --port=*) PORT="${1#*=}"; PORT_GIVEN=1; shift ;;
    --host=*) HOST="${1#*=}"; HOST_GIVEN=1; shift ;;
    *) echo "Неизвестный аргумент: $1" >&2; exit 1 ;;
  esac
done

usage() {
  sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'
  exit 1
}

# Адрес и порт живут в установленном описании сервиса. Без этого команды
# status/start/stop/restart молча брали значения по умолчанию и проверяли не тот порт.
read_installed_config() {
  local host="" port=""
  if [ "$PLATFORM" = "linux" ] && [ -f "$UNIT" ]; then
    host="$(sed -n 's/^ExecStart=.*--host \([^ ]*\).*/\1/p' "$UNIT" | head -1)"
    port="$(sed -n 's/^ExecStart=.*--port \([^ ]*\).*/\1/p' "$UNIT" | head -1)"
  elif [ "$PLATFORM" = "macos" ] && [ -f "$PLIST" ]; then
    host="$(grep -A1 -- '--host' "$PLIST" | tail -1 | sed 's/.*<string>\(.*\)<\/string>.*/\1/')"
    port="$(grep -A1 -- '--port' "$PLIST" | tail -1 | sed 's/.*<string>\(.*\)<\/string>.*/\1/')"
  fi
  [ -z "$HOST_GIVEN" ] && [ -n "$host" ] && HOST="$host"
  [ -z "$PORT_GIVEN" ] && [ -n "$port" ] && PORT="$port"
  return 0
}

# --------------------------------------------------------------------- вспомогательное

# Окружение считаем пригодным, только если его python реально запускается и видит
# зависимости: .venv, скопированный с другой машины или ОС, проверку `-x` проходит,
# но systemd/launchd потом падают с «Exec format error» или ImportError.
venv_ok() {
  "$PROJECT_DIR/.venv/bin/python" -c "import fastapi, uvicorn, duckdb, httpx, jinja2, markdown_it" \
    >/dev/null 2>&1
}

ensure_venv() {
  if ! venv_ok; then
    if [ -e "$PROJECT_DIR/.venv" ]; then
      echo "→ .venv нерабочий (другая ОС или неполные зависимости) — пересоздаю…"
      rm -rf "$PROJECT_DIR/.venv"
    else
      echo "→ виртуального окружения нет, ставлю зависимости…"
    fi
    ./install.sh
  fi
  if ! venv_ok; then
    echo -e "${RED}Окружение .venv не работает — запустите ./install.sh и посмотрите ошибки.${NC}" >&2
    exit 1
  fi
}

# PID слушателя порта. lsof есть не везде (на Linux часто нет) — пробуем ss и fuser.
port_holder() {
  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | head -1 && return 0
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -lntpH "sport = :${PORT}" 2>/dev/null | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2 && return 0
  fi
  if command -v fuser >/dev/null 2>&1; then
    fuser "${PORT}/tcp" 2>/dev/null | tr -s ' ' '\n' | head -1 && return 0
  fi
  return 0
}

is_running() {
  if [ "$PLATFORM" = "macos" ]; then
    launchctl list "$LABEL" >/dev/null 2>&1
  else
    systemctl --user is-active --quiet "$UNIT_NAME"
  fi
}

is_installed() {
  [ "$PLATFORM" = "macos" ] && [ -f "$PLIST" ] || { [ "$PLATFORM" = "linux" ] && [ -f "$UNIT" ]; }
}

http_check() {
  curl -fsS -m 4 -o /dev/null "http://127.0.0.1:${PORT}/monitor" 2>/dev/null
}

# PID, под которым launchd держит сервис (0 — зарегистрирован, но не запущен)
service_pid() {
  if [ "$PLATFORM" = "macos" ]; then
    launchctl list 2>/dev/null | awk -v l="$LABEL" '$3 == l { print $1 }' | head -1
  else
    systemctl --user show -p MainPID --value "$UNIT_NAME" 2>/dev/null
  fi
}

# Ждём, пока launchd/systemd действительно снимет сервис: сразу после bootout
# метка ещё числится, и повторный bootstrap падает с «Input/output error».
wait_until_unloaded() {
  local tries=20
  while [ $tries -gt 0 ]; do
    is_running || return 0
    sleep 0.5
    tries=$((tries - 1))
  done
  return 1
}

# Успех — это живой процесс сервиса, а не просто ответ по HTTP:
# отвечать может умирающий старый экземпляр или посторонний процесс на том же порту.
wait_until_up() {
  local tries=30 pid
  while [ $tries -gt 0 ]; do
    pid="$(service_pid)"
    if [ -n "$pid" ] && [ "$pid" != "0" ] && [ "$pid" != "-" ] && http_check; then
      return 0
    fi
    sleep 0.5
    tries=$((tries - 1))
  done
  return 1
}

# Диагностика, когда сервис не поднялся: настоящая причина прячется в журнале.
report_failure() {
  echo -e "${RED}Сервис не запустился.${NC}" >&2
  local pid; pid="$(service_pid)"
  if [ "$PLATFORM" = "linux" ]; then
    echo "  systemd: MainPID=${pid:-—} (0 — процесс не живёт)" >&2
    echo "  Состояние:" >&2
    systemctl --user status "$UNIT_NAME" --no-pager -n 0 2>&1 | sed 's/^/    /' >&2 || true
    echo "  Последние строки журнала:" >&2
    journalctl --user -u "$UNIT_NAME" -n 20 --no-pager 2>&1 | sed 's/^/    /' >&2 || true
  else
    [ -n "$pid" ] && echo "  launchctl: метка есть, PID=${pid} (0 — процесс не живёт)" >&2 \
                  || echo "  launchctl: метка не зарегистрирована" >&2
    if [ -s "$LOG_ERR" ]; then
      echo "  Последние строки $LOG_ERR:" >&2
      tail -12 "$LOG_ERR" | sed 's/^/    /' >&2
    fi
  fi
  echo "  Полный журнал: ./service.sh logs" >&2
}

# --------------------------------------------------------------------- описания сервиса

write_plist() {
  mkdir -p "$(dirname "$PLIST")" "$LOG_DIR"
  cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${PROJECT_DIR}/.venv/bin/python</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>app.main:app</string>
        <string>--host</string>
        <string>${HOST}</string>
        <string>--port</string>
        <string>${PORT}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${PROJECT_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>10</integer>
    <key>StandardOutPath</key>
    <string>${LOG_OUT}</string>
    <key>StandardErrorPath</key>
    <string>${LOG_ERR}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONUNBUFFERED</key>
        <string>1</string>
    </dict>
</dict>
</plist>
PLIST_EOF
}

write_unit() {
  mkdir -p "$(dirname "$UNIT")" "$LOG_DIR"
  cat > "$UNIT" <<UNIT_EOF
[Unit]
Description=AI Monitoring Proxy
After=network-online.target

[Service]
Type=simple
WorkingDirectory=${PROJECT_DIR}
ExecStart=${PROJECT_DIR}/.venv/bin/python -m uvicorn app.main:app --host ${HOST} --port ${PORT}
Environment=PYTHONUNBUFFERED=1
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
UNIT_EOF
}

# --------------------------------------------------------------------- загрузка в launchd

# Загрузить метку в launchd. Ошибку не глушим: «Load failed: 5: Input/output error»
# обычно означает, что метка ещё не снята после предыдущего bootout.
load_service() {
  local out status
  if [ "$PLATFORM" = "linux" ]; then
    out="$(systemctl --user start "$UNIT_NAME" 2>&1)"; status=$?
    [ $status -ne 0 ] && echo -e "${RED}systemctl не смог запустить сервис:${NC} ${out}" >&2
    return $status
  fi
  out="$(launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>&1)"; status=$?
  if [ $status -ne 0 ]; then
    # старые версии macOS не знают bootstrap — пробуем legacy-путь
    out="$(launchctl load -w "$PLIST" 2>&1)"; status=$?
  fi
  if [ $status -ne 0 ]; then
    echo -e "${RED}launchctl не смог загрузить сервис:${NC} ${out}" >&2
    return 1
  fi
  return 0
}

unload_service() {
  if [ "$PLATFORM" = "linux" ]; then
    systemctl --user stop "$UNIT_NAME" >/dev/null 2>&1 || true
    return 0
  fi
  launchctl bootout "gui/$(id -u)/${LABEL}" >/dev/null 2>&1 \
    || launchctl unload -w "$PLIST" >/dev/null 2>&1 || true
}

# --------------------------------------------------------------------- команды

cmd_install() {
  ensure_venv

  local holder
  holder="$(port_holder || true)"
  if [ -n "$holder" ] && ! is_running; then
    echo -e "${RED}Порт ${PORT} уже занят процессом ${holder}.${NC}" >&2
    echo "Остановите его (например, запущенный вручную ./run.sh) или укажите другой порт:" >&2
    echo "    ./service.sh install --port 8888" >&2
    exit 1
  fi

  if is_running; then
    unload_service
    wait_until_unloaded || {
      echo -e "${RED}Прежний сервис не снялся за 10 секунд.${NC}" >&2
      echo "Попробуйте: ./service.sh uninstall && ./service.sh install --host ${HOST}" >&2
      exit 1
    }
    echo "→ прежний экземпляр остановлен"
  fi

  if [ "$PLATFORM" = "macos" ]; then
    write_plist
    load_service || exit 1
  else
    write_unit
    systemctl --user daemon-reload
    systemctl --user enable --now "$UNIT_NAME"
  fi

  echo "→ сервис установлен: ${LABEL}  (${HOST}:${PORT})"
  if wait_until_up; then
    echo -e "${GREEN}✅ запущен и отвечает: http://localhost:${PORT}/monitor${NC}"
  else
    report_failure
    exit 1
  fi

  if [ "$HOST" != "127.0.0.1" ] && [ "$HOST" != "localhost" ]; then
    local lan_ip
    lan_ip="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null \
              || hostname -I 2>/dev/null | awk '{print $1}' || true)"
    [ -n "$lan_ip" ] && echo "→ из локальной сети: http://${lan_ip}:${PORT}/monitor"
    echo -e "${YELLOW}⚠️  Сервис слушает ${HOST} и работает без аутентификации:"
    echo -e "    любой в сети сможет тратить баланс и увидеть API-ключ в /settings.${NC}"
  fi

  echo
  echo "Автозапуск: при входе в систему. Управление — ./service.sh status|stop|restart|logs"
}

cmd_uninstall() {
  if [ "$PLATFORM" = "macos" ]; then
    unload_service
    rm -f "$PLIST"
  else
    systemctl --user disable --now "$UNIT_NAME" 2>/dev/null || true
    rm -f "$UNIT"
    systemctl --user daemon-reload
  fi
  echo "→ сервис снят. База и настройки в data/ не тронуты."
}

cmd_start() {
  is_installed || { echo "Сервис не установлен — запустите ./service.sh install" >&2; exit 1; }
  if is_running; then
    http_check && { echo "Уже запущен: http://localhost:${PORT}/monitor"; return 0; }
    unload_service
    wait_until_unloaded || true
  fi
  if [ "$PLATFORM" = "macos" ]; then
    load_service || exit 1
  else
    systemctl --user start "$UNIT_NAME"
  fi
  if wait_until_up; then
    echo -e "${GREEN}✅ запущен: http://localhost:${PORT}/monitor${NC}"
  else
    report_failure
    exit 1
  fi
}

cmd_stop() {
  if [ "$PLATFORM" = "macos" ]; then
    unload_service
  else
    systemctl --user stop "$UNIT_NAME" 2>/dev/null || true
  fi
  wait_until_unloaded || true
  echo "→ остановлен"
}

cmd_restart() {
  is_installed || { echo "Сервис не установлен — запустите ./service.sh install" >&2; exit 1; }
  if [ "$PLATFORM" = "macos" ]; then
    if ! is_running; then
      cmd_start
      return
    fi
    launchctl kickstart -k "gui/$(id -u)/${LABEL}" >/dev/null 2>&1 || { cmd_stop; cmd_start; return; }
  else
    systemctl --user restart "$UNIT_NAME"
  fi
  if wait_until_up; then
    echo -e "${GREEN}✅ перезапущен${NC}"
  else
    report_failure
    exit 1
  fi
}

cmd_status() {
  echo "Проект:    $PROJECT_DIR"
  echo "Платформа: $PLATFORM"
  echo "Адрес:     ${HOST}:${PORT}$([ -z "$PORT_GIVEN$HOST_GIVEN" ] && is_installed && echo "  (из описания сервиса)")"
  if is_installed; then
    echo -e "Установлен: ${GREEN}да${NC}  ($([ "$PLATFORM" = macos ] && echo "$PLIST" || echo "$UNIT"))"
  else
    echo -e "Установлен: ${YELLOW}нет${NC}"
  fi

  if is_running; then
    echo -e "Сервис:    ${GREEN}загружен${NC}"
  else
    echo -e "Сервис:    ${YELLOW}не загружен${NC}"
  fi

  local holder
  holder="$(port_holder || true)"
  if [ -n "$holder" ]; then
    echo "Порт ${PORT}: занят процессом ${holder} ($(ps -p "$holder" -o comm= 2>/dev/null || echo '?'))"
  else
    echo "Порт ${PORT}: свободен"
  fi

  if http_check; then
    echo -e "HTTP:      ${GREEN}отвечает${NC} — http://localhost:${PORT}/monitor"
  else
    echo -e "HTTP:      ${RED}не отвечает${NC}"
  fi
  if [ "$PLATFORM" = "linux" ]; then
    echo "Журнал:    journalctl --user -u ${UNIT_NAME}"
  elif [ -f "$LOG_OUT" ]; then
    echo "Журнал:    $LOG_OUT"
  fi
  return 0
}

cmd_logs() {
  if [ "$PLATFORM" = "linux" ]; then
    # systemd пишет в journald, а не в data/logs — файлы там могут остаться от другой машины
    echo "→ journalctl --user -u ${UNIT_NAME} (Ctrl+C для выхода)"
    journalctl --user -u "$UNIT_NAME" -n 50 -f
    return
  fi
  [ -f "$LOG_OUT" ] || { echo "Журнала ещё нет: $LOG_OUT" >&2; exit 1; }
  echo "→ $LOG_OUT и $LOG_ERR (Ctrl+C для выхода)"
  tail -n 50 -f "$LOG_OUT" "$LOG_ERR"
}

case "$COMMAND" in
  # install задаёт адрес и порт сам; остальным командам их надо взять из установленного описания
  install)   cmd_install ;;
  uninstall) read_installed_config; cmd_uninstall ;;
  start)     read_installed_config; cmd_start ;;
  stop)      read_installed_config; cmd_stop ;;
  restart)   read_installed_config; cmd_restart ;;
  status)    read_installed_config; cmd_status ;;
  logs)      cmd_logs ;;
  *)         usage ;;
esac
