#!/bin/bash
# Smoke test: stored reporting screen after login
set -e

BASE_URL="${BASE_URL:-http://localhost:5173}"
TEST_EMAIL="${TEST_EMAIL:?Set TEST_EMAIL env var}"
TEST_PASSWORD="${TEST_PASSWORD:?Set TEST_PASSWORD env var}"

agent-browser open "$BASE_URL/login"
sleep 2
agent-browser fill 'input[type="email"]' "$TEST_EMAIL"
agent-browser fill 'input[type="password"]' "$TEST_PASSWORD"
agent-browser click 'button[type="submit"]'
sleep 3
agent-browser open "$BASE_URL/reporting"
sleep 2

SNAPSHOT=$(agent-browser snapshot)
if ! echo "$SNAPSHOT" | grep -qi "Meta Reporting"; then
  agent-browser screenshot /tmp/reporting-fail.png
  agent-browser close
  exit 1
fi

agent-browser close
