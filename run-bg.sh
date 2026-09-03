#!/usr/bin/env bash
# Запуск прокси: ./run-all.sh [порт]
PORT="${1:-8787}"
AI_PROXY_HOST=0.0.0.0 ./run.sh $PORT

# Regular Colors
YELLOW='\033[0;33m'       # Yellow
PURPLE='\033[0;35m'       # Purple
BLACK='\033[0;30m'        # Black
WHITE='\033[0;37m'        # White
GREEN='\033[0;32m'        # Green
BLUE='\033[0;34m'         # Blue
CYAN='\033[0;36m'         # Cyan
RED='\033[0;31m'          # Red
NC='\033[0m' # No Color
