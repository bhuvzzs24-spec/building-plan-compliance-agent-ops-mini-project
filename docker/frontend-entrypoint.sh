#!/bin/sh
set -eu
API_BASE_URL="$(printenv API_BASE_URL 2>/dev/null || printf '%s' 'http://localhost:8000')"
printf 'window.BUILDING_COMPLIANCE_CONFIG = { apiBaseUrl: "%s" };\n' "$API_BASE_URL" > /usr/share/nginx/html/runtime-config.js
