#!/usr/bin/env bash
set -euo pipefail

git pull --rebase

docker compose build

docker compose up -d
