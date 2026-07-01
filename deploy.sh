#!/bin/bash
set -e
cd "$(dirname "$0")"

git fetch origin master

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/master)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - найдены обновления, разворачиваю новую версию" >> deploy.log
    git pull origin master
    docker compose up -d --build
fi
