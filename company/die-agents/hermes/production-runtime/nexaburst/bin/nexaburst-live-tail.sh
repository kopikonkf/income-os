#!/usr/bin/env bash
printf 'NexaBurst H01 Live Ledger\n========================\n'
exec tail -n 25 -F /var/lib/die/h01/nexaburst/receipts/nexaburst-ledger.jsonl
