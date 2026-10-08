#!/usr/bin/env bash
# Post-deployment smoke test: exercises the UI, health endpoints and a full CRUD cycle.
#   scripts/smoke-test.sh http://localhost:3000            (Docker Compose)
#   scripts/smoke-test.sh http://stockpilot.localtest.me   (Kubernetes Ingress)
set -euo pipefail

BASE="${1:-http://localhost:3000}"
SKU="SMOKE-$(date +%s)"
fail() { echo "FAIL: $*" >&2; exit 1; }
check() {  # check <description> <expected status> <curl args...>
  local description="$1" expected="$2"; shift 2
  local status
  status="$(curl -s -o /tmp/smoke-body.$$ -w '%{http_code}' "$@")"
  [[ "$status" == "$expected" ]] || fail "$description: expected HTTP $expected, got $status ($(cat /tmp/smoke-body.$$))"
  echo "ok  $description ($status)"
}

check "UI index"            200 "$BASE/"
check "API info"            200 "$BASE/api/info"
check "list products"       200 "$BASE/api/products"
check "inventory stats"     200 "$BASE/api/stats"
check "create product"      201 -X POST "$BASE/api/products" -H 'Content-Type: application/json' \
  -d "{\"sku\":\"$SKU\",\"name\":\"Smoke test item\",\"category\":\"Testing\",\"quantity\":10,\"reorder_level\":2,\"unit_price\":1}"
ID="$(sed -E 's/.*"id":([0-9]+).*/\1/' /tmp/smoke-body.$$)"
check "get product"         200 "$BASE/api/products/$ID"
check "update product"      200 -X PUT "$BASE/api/products/$ID" -H 'Content-Type: application/json' -d '{"unit_price":2.5}'
check "record sale"         201 -X POST "$BASE/api/products/$ID/adjustments" -H 'Content-Type: application/json' -d '{"change":-4,"reason":"SALE"}'
check "reject oversell"     409 -X POST "$BASE/api/products/$ID/adjustments" -H 'Content-Type: application/json' -d '{"change":-100,"reason":"SALE"}'
check "delete product"      204 -X DELETE "$BASE/api/products/$ID"
check "deleted is gone"     404 "$BASE/api/products/$ID"
rm -f /tmp/smoke-body.$$
echo "Smoke test passed against $BASE"
