#!/usr/bin/env bash
set -euo pipefail

mkdir -p backups
if [ ! -f data/escrow.db ]; then
  echo "No database found."
  exit 1
fi

ts=$(date +%Y%m%d%H%M%S)
cp data/escrow.db backups/escrow-${ts}.db
