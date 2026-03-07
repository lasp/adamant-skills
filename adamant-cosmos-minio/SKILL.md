---
name: adamant-cosmos-minio
description: COSMOS test suite execution via Script Runner REST API and result verification through MinIO log retrieval. Use when launching COSMOS test scripts via curl, polling for completion, retrieving suite logs from MinIO, and parsing pass/fail results.
---

# COSMOS Script Runner API + MinIO Log Verification

Execute COSMOS test suites programmatically via the Script Runner REST API,
poll for completion, and retrieve/parse results from MinIO storage.

## Architecture

```
Test Driver (bash/python)
  |
  |--> Script Runner API (curl)  --> COSMOS runs test_suite.py
  |                                      |
  |--> Poll: /script-api/running-script  |
  |                                      v
  |--> Poll: /script-api/completed-scripts
  |
  |--> MinIO: retrieve suite log from openc3-logs bucket
  |
  +--> Parse log: extract PASS/FAIL/ERROR counts
```

## Script Runner REST API

### Base URL
```
http://localhost:2900
```
All endpoints require `Authorization: openc3service` header.

### 1. Load Script (verify it exists)
```bash
curl -s -w "%{http_code}" \
  -H "Authorization: openc3service" \
  "${BASE_URL}/script-api/scripts/${SCRIPT_PATH}/?scope=DEFAULT" \
  -o /dev/null
```
Expect HTTP 200.

### 2. Lock Script
```bash
curl -s -w "%{http_code}" -X POST \
  -H "Authorization: openc3service" \
  "${BASE_URL}/script-api/scripts/${SCRIPT_PATH}/lock?scope=DEFAULT" \
  -o /dev/null
```
Expect HTTP 200.

### 3. Run Script
```bash
curl -s -w "%{http_code}" -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: openc3service" \
  "${BASE_URL}/script-api/scripts/${SCRIPT_PATH}/run?scope=DEFAULT" \
  --data-raw '{"environment":[],"suiteRunner":{"method":"start","suite":"TestSuite","options":["continueAfterError"]}}' \
  -o /dev/null
```
Expect HTTP 200. The `continueAfterError` option runs all tests even if one fails.

### 4. Poll Running Scripts
```bash
curl -s -H "Authorization: openc3service" \
  "${BASE_URL}/script-api/running-script?scope=DEFAULT"
```
Returns JSON array. Empty array `[]` means no scripts running.
Poll every 10 seconds until empty (script finished).

### 5. Check Completed Scripts
```bash
curl -s -H "Authorization: openc3service" \
  "${BASE_URL}/script-api/completed-scripts?scope=DEFAULT"
```
Returns JSON with completion info including log file names.

## MinIO Log Retrieval

COSMOS stores all logs in the `openc3-logs` MinIO bucket. The MinIO service
runs inside the COSMOS Docker Compose stack.

### Log Paths
```
logs/DEFAULT/tool_logs/sr/YYYY_MM_DD/   -- Script Runner logs by date
```

### Retrieve Logs via Docker exec
```bash
# Find the minio container
MINIO_CONTAINER=$(docker ps --format '{{.Names}}' | grep minio)

# List today's script runner logs
docker exec $MINIO_CONTAINER mc ls local/openc3-logs/DEFAULT/tool_logs/sr/$(date +%Y_%m_%d)/

# Copy log to temp, then to host
LOG_NAME="test_suite_TIMESTAMP.log"
docker exec $MINIO_CONTAINER mc cp \
  "local/openc3-logs/DEFAULT/tool_logs/sr/$(date +%Y_%m_%d)/${LOG_NAME}" \
  "/tmp/${LOG_NAME}"
docker cp "$MINIO_CONTAINER:/tmp/${LOG_NAME}" "./suite_results.log"
```

### Alternative: Direct MinIO API
MinIO listens on port 9000 inside the Docker network. From the host:
```bash
# List bucket contents (requires mc configured)
docker exec $MINIO_CONTAINER mc ls local/openc3-logs/ --recursive | grep test_suite
```

## Log Parsing

Suite logs contain structured output. Key patterns:

### Pass/Fail Extraction
```bash
# Count results
grep -c "PASS" suite_results.log
grep -c "FAIL" suite_results.log
grep -c "ERROR" suite_results.log
grep -c "SKIP" suite_results.log

# Extract summary line (usually at end)
tail -20 suite_results.log | grep -i "total\|summary\|result"
```

### Script Runner Log Format
The log contains timestamped entries for each test step:
```
YYYY/MM/DD HH:MM:SS.SSS | SCRIPTRUNNER | test_name | PASS
YYYY/MM/DD HH:MM:SS.SSS | SCRIPTRUNNER | test_name | FAIL | error message
```

## Complete Test Driver Script

Reference pattern (adapt for each assembly):

```bash
#!/bin/bash
# run_cosmos_suite.sh - Execute COSMOS test suite and verify results
set -e

BASE_URL="${COSMOS_URL:-http://localhost:2900}"
SCOPE="DEFAULT"
SCRIPT_PATH="$1"  # e.g., T17_PARAM_SYSTEM/procedures/test_parameter_lifecycle.py
TIMEOUT=${2:-300}  # seconds

AUTH_HEADER="Authorization: openc3service"

echo "[1/5] Loading script: ${SCRIPT_PATH}"
HTTP_CODE=$(curl -s -w "%{http_code}" -H "$AUTH_HEADER" \
  "${BASE_URL}/script-api/scripts/${SCRIPT_PATH}/?scope=${SCOPE}" -o /dev/null)
[[ "$HTTP_CODE" == "200" ]] || { echo "FAIL: script load HTTP $HTTP_CODE"; exit 1; }

echo "[2/5] Locking script"
curl -s -X POST -H "$AUTH_HEADER" \
  "${BASE_URL}/script-api/scripts/${SCRIPT_PATH}/lock?scope=${SCOPE}" -o /dev/null

echo "[3/5] Running script"
curl -s -X POST \
  -H "Content-Type: application/json" -H "$AUTH_HEADER" \
  "${BASE_URL}/script-api/scripts/${SCRIPT_PATH}/run?scope=${SCOPE}" \
  --data-raw '{"environment":[],"suiteRunner":{"method":"start","suite":"TestSuite","options":["continueAfterError"]}}' \
  -o /dev/null

echo "[4/5] Polling for completion (timeout: ${TIMEOUT}s)"
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
  RUNNING=$(curl -s -H "$AUTH_HEADER" \
    "${BASE_URL}/script-api/running-script?scope=${SCOPE}")
  if [ "$RUNNING" = "[]" ] || [ -z "$RUNNING" ]; then
    echo "  Script finished after ${ELAPSED}s"
    break
  fi
  sleep 10
  ELAPSED=$((ELAPSED + 10))
done

if [ $ELAPSED -ge $TIMEOUT ]; then
  echo "FAIL: script timed out after ${TIMEOUT}s"
  exit 1
fi

echo "[5/5] Retrieving results from MinIO"
MINIO_CONTAINER=$(docker ps --format '{{.Names}}' | grep minio)
DATE_DIR=$(date +%Y_%m_%d)
LOG_DIR="local/openc3-logs/DEFAULT/tool_logs/sr/${DATE_DIR}/"

# Find the most recent test_suite log
LATEST_LOG=$(docker exec $MINIO_CONTAINER mc ls "${LOG_DIR}" 2>/dev/null \
  | grep "test" | tail -1 | awk '{print $NF}')

if [ -n "$LATEST_LOG" ]; then
  docker exec $MINIO_CONTAINER mc cp "${LOG_DIR}${LATEST_LOG}" "/tmp/${LATEST_LOG}"
  docker cp "$MINIO_CONTAINER:/tmp/${LATEST_LOG}" "./suite_results.log"
  
  PASS_COUNT=$(grep -c "PASS" suite_results.log 2>/dev/null || echo 0)
  FAIL_COUNT=$(grep -c "FAIL" suite_results.log 2>/dev/null || echo 0)
  
  echo "Results: ${PASS_COUNT} PASS, ${FAIL_COUNT} FAIL"
  [ "$FAIL_COUNT" -eq 0 ] && echo "SUITE PASSED" || { echo "SUITE FAILED"; exit 1; }
else
  echo "WARNING: No log file found in MinIO"
  # Fall back to completed-scripts API
  curl -s -H "$AUTH_HEADER" \
    "${BASE_URL}/script-api/completed-scripts?scope=${SCOPE}"
fi
```

## COSMOS Docker Container Names

Standard COSMOS compose stack container naming:
```
*-openc3-minio-*          -- MinIO (S3-compatible storage, port 9000)
*-openc3-cosmos-cmd-tlm-api-*  -- API server
*-openc3-operator-*       -- Operator (manages microservices)
*-openc3-traefik-*        -- Reverse proxy (port 2900)
```

Use `docker ps --format '{{.Names}}' | grep <pattern>` to find containers.

## Guidelines

1. Always use `continueAfterError` in suite options -- partial results are better than abort
2. Poll interval: 10 seconds is reasonable; don't hammer the API
3. MinIO logs appear after script completion -- allow 5-10s delay
4. Log paths use underscored dates (YYYY_MM_DD), not dashes
5. The `mc` client inside the minio container uses alias `local` (pre-configured)
6. Suite timeout should be generous (5-10 min) for large assemblies
7. Parse the LAST matching log file -- earlier runs may exist from prior iterations
