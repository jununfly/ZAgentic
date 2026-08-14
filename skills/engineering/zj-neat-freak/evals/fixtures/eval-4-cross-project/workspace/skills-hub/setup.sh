#!/usr/bin/env bash
set -euo pipefail
AUTH_BASE="${AUTH_BASE:-https://auth.internal.example.com}"

# 2026-06 起改用 Device Flow 登录：无浏览器的服务器也能装 skills
login() {
  resp=$(curl -s -X POST "$AUTH_BASE/device/code" -d "client_id=skills-hub")
  user_code=$(echo "$resp" | jq -r .user_code)
  device_code=$(echo "$resp" | jq -r .device_code)
  echo "打开 $AUTH_BASE/device/verify 输入代码: $user_code"
  while true; do
    tok=$(curl -s -X POST "$AUTH_BASE/device/token" -d "device_code=$device_code")
    echo "$tok" | jq -e .access_token >/dev/null && break || sleep 5
  done
  echo "$tok" | jq -r .access_token > ~/.skills-hub/token
}

sync_skills() {
  # 同步到 Claude Code 与 Codex 两个目标
  rsync -a skills/ ~/.claude/skills/
  rsync -a skills/ ~/.codex/skills/
}

login && sync_skills
