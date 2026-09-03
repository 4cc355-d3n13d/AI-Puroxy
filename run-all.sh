#!/usr/bin/env bash
# Запуск прокси: ./run-all.sh [порт]
PORT="${1:-8787}"
AI_PROXY_HOST=0.0.0.0 ./run.sh $PORT
echo 0.0.0.0


#  PORT="${1:-8787}"
#  COMMAND="AI_PROXY_HOST=0.0.0.0 ./run.sh ${PORT}"
#  echo $COMMAND
#  `$COMMAND`
