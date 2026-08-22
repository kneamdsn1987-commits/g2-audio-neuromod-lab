#!/bin/bash
# Test script for G2 Audio Neuromod Lab API

API_URL="http://127.0.0.1:8000"
TOKEN="change-this-token"

echo "========================================="
echo "G2 Audio Neuromod Lab - API Test Suite"
echo "========================================="
echo ""

# 1. Health check
echo "1. Health Check..."
curl -s -X GET "$API_URL/health" | jq .
echo ""
sleep 1

# 2. Validate setup
echo "2. Validate Setup Configuration..."
curl -s -X POST "$API_URL/validate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  --data-binary @setup.json | jq .
echo ""
sleep 1

# 3. Start session
echo "3. Starting Session (with approval)..."
curl -s -X POST "$API_URL/start" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Manual-Approval: approved" \
  -H "Content-Type: application/json" \
  --data-binary @setup.json | jq .
echo ""
sleep 2

# 4. Check status
echo "4. Checking Session Status..."
curl -s -X GET "$API_URL/status" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo ""
sleep 2

# 5. Check status again
echo "5. Checking Status Again (uptime increased)..."
curl -s -X GET "$API_URL/status" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo ""
sleep 1

# 6. Stop session
echo "6. Stopping Session..."
curl -s -X POST "$API_URL/stop" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo ""

# 7. Final status check
echo "7. Final Status Check (should be idle)..."
curl -s -X GET "$API_URL/status" \
  -H "Authorization: Bearer $TOKEN" | jq .
echo ""

echo "========================================="
echo "Test Suite Complete!"
echo "========================================="
