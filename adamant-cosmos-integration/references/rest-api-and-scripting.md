# COSMOS REST API & Scripting Reference

This document provides comprehensive reference for automating COSMOS operations via curl/REST API and Python scripting.

## Base URL and Scope

All API requests go through Traefik at port 2900:
- **Base URL**: `http://localhost:2900`
- **Required Parameter**: All endpoints require `?scope=DEFAULT` (or your specific scope)

## 1. Authentication

### Get Session Token

```bash
# Authenticate and get session token
TOKEN=$(curl -s -X POST \
  "http://localhost:2900/openc3-api/auth/verify?scope=DEFAULT" \
  -H "Content-Type: application/json" \
  -d '{"password": "your_password"}')
echo "Token: $TOKEN"
```

### Using Token in Requests

Include the session token in the `Authorization` header:

```bash
curl -H "Authorization: $TOKEN" \
  "http://localhost:2900/script-api/scripts?scope=DEFAULT"
```

### Environment Variables for External Python Scripts

For external Python scripts (running outside Script Runner):

```python
import os

os.environ["OPENC3_API_SCHEMA"] = "http"
os.environ["OPENC3_API_HOSTNAME"] = "localhost"
os.environ["OPENC3_API_PORT"] = "2900"
os.environ["OPENC3_SCRIPT_API_SCHEMA"] = "http"
os.environ["OPENC3_SCRIPT_API_HOSTNAME"] = "localhost"
os.environ["OPENC3_SCRIPT_API_PORT"] = "2900"
os.environ["OPENC3_API_PASSWORD"] = "your_password"
os.environ["OPENC3_NO_STORE"] = "1"

from openc3.script import *
```

## 2. Script Management via REST

### List All Scripts

```bash
# List scripts in a target
curl -H "Authorization: $TOKEN" \
  "http://localhost:2900/script-api/scripts?scope=DEFAULT&target=INST"

# List all scripts (no target filter)
curl -H "Authorization: $TOKEN" \
  "http://localhost:2900/script-api/scripts?scope=DEFAULT"
```

Response: Array of script information objects.

### Get Script Body

```bash
# Get script content
curl -H "Authorization: $TOKEN" \
  "http://localhost:2900/script-api/scripts/INST/example.py?scope=DEFAULT"
```

Response: JSON object with `contents`, `breakpoints`, `locked` status, and optionally `suites` if it's a test suite.

### Create/Upload Script

```bash
# Upload a new script
curl -X POST \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"text": "print(\"Hello World\")", "breakpoints": []}' \
  "http://localhost:2900/script-api/scripts/INST/hello.py?scope=DEFAULT"
```

### Delete Script

```bash
# Delete a script
curl -X POST \
  -H "Authorization: $TOKEN" \
  "http://localhost:2900/script-api/scripts/INST/example.py/delete?scope=DEFAULT"
```

### Run Script

#### Simple Script Run

```bash
# Run a script normally
RUNNING_ID=$(curl -s -X POST \
  -H "Authorization: $TOKEN" \
  "http://localhost:2900/script-api/scripts/INST/example.py/run?scope=DEFAULT")
echo "Running ID: $RUNNING_ID"
```

#### Run in Disconnect Mode

```bash
# Run script in disconnect mode (background)
RUNNING_ID=$(curl -s -X POST \
  -H "Authorization: $TOKEN" \
  "http://localhost:2900/script-api/scripts/INST/example.py/run/disconnect?scope=DEFAULT")
```

#### Run with Environment Variables

```bash
# Run with custom environment
curl -X POST \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"environment": [{"name": "MY_VAR", "value": "my_value"}]}' \
  "http://localhost:2900/script-api/scripts/INST/example.py/run?scope=DEFAULT"
```

## 3. Running Script Control

### List Running Scripts

```bash
# List currently running scripts
curl -H "Authorization: $TOKEN" \
  "http://localhost:2900/script-api/running-script?scope=DEFAULT&limit=10&offset=0"
```

Response: `{"items": [...], "total": number}`

### Get Running Script Status

```bash
# Get status of specific running script
curl -H "Authorization: $TOKEN" \
  "http://localhost:2900/script-api/running-script/$RUNNING_ID?scope=DEFAULT"
```

### Stop Script

```bash
# Stop a running script gracefully
curl -X POST \
  -H "Authorization: $TOKEN" \
  "http://localhost:2900/script-api/running-script/$RUNNING_ID/stop?scope=DEFAULT"
```

### Pause/Resume Script

```bash
# Pause script
curl -X POST \
  -H "Authorization: $TOKEN" \
  "http://localhost:2900/script-api/running-script/$RUNNING_ID/pause?scope=DEFAULT"

# Resume script  
curl -X POST \
  -H "Authorization: $TOKEN" \
  "http://localhost:2900/script-api/running-script/$RUNNING_ID/go?scope=DEFAULT"
```

### Step Script

```bash
# Execute one step when paused
curl -X POST \
  -H "Authorization: $TOKEN" \
  "http://localhost:2900/script-api/running-script/$RUNNING_ID/step?scope=DEFAULT"
```

### Delete (Force Kill)

```bash
# Force kill a running script
curl -X POST \
  -H "Authorization: $TOKEN" \
  "http://localhost:2900/script-api/running-script/$RUNNING_ID/delete?scope=DEFAULT"
```

## 4. Completed Scripts

### List Completed Scripts

```bash
# List recently completed scripts
curl -H "Authorization: $TOKEN" \
  "http://localhost:2900/script-api/completed-scripts?scope=DEFAULT&limit=10&offset=0"
```

Response: `{"items": [...], "total": number}`

## 5. Running Test Suites

### Suite Runner JSON Structure

For Python test suites, the `suiteRunner` parameter expects this JSON structure:

```json
{
  "suite": "MySuite",
  "group": "MyGroup", 
  "script": "MyScript",
  "method": "start",
  "options": ["continueAfterError", "pauseOnError", "abortAfterError", "manual", "loop", "breakLoopOnError"]
}
```

### Python Suite Detection

COSMOS detects Python test suites using this regex pattern:
```python
# Must match: class MySuite(Suite) or class MySuite(TestSuite)
class MySuite(Suite):
    def setup(self):
        pass
    
    def start(self):
        pass
        
    def teardown(self):
        pass
```

### Suite Options

- `continueAfterError`: Continue executing other tests after a failure
- `pauseOnError`: Pause execution when an error occurs
- `abortAfterError`: Stop entire suite on first error
- `manual`: Require manual confirmation at each step
- `loop`: Loop the suite execution
- `breakLoopOnError`: Break out of loop mode on error

### Run Test Suite Example

```bash
# Run a complete test suite
curl -X POST \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "suiteRunner": {
      "suite": "ExampleSuite",
      "group": "TestGroup", 
      "script": "TestScript",
      "method": "start",
      "options": ["continueAfterError", "pauseOnError"]
    }
  }' \
  "http://localhost:2900/script-api/scripts/INST/test_suite.py/run?scope=DEFAULT"
```

## 6. Log/Output Retrieval via Storage API

### List Buckets

```bash
# List all available buckets
curl -H "Authorization: $TOKEN" \
  "http://localhost:2900/openc3-api/storage/buckets?scope=DEFAULT"
```

### List Files in Bucket

```bash
# List files in logs bucket
curl -H "Authorization: $TOKEN" \
  "http://localhost:2900/openc3-api/storage/files/logs/?path=DEFAULT/decom_logs/tlm/INST/&scope=DEFAULT"

# List files in config bucket
curl -H "Authorization: $TOKEN" \
  "http://localhost:2900/openc3-api/storage/files/config/?path=DEFAULT/targets/INST/&scope=DEFAULT"
```

### Download File

```bash
# Download a specific file
curl -H "Authorization: $TOKEN" \
  "http://localhost:2900/openc3-api/storage/download_file/DEFAULT/logs/script_runner/sr_inst_example.py_20240101.log?scope=DEFAULT"
```

Response: JSON with `filename` and base64-encoded `contents`.

### Common Bucket Paths

**Log Buckets:**
- Raw logs: `{SCOPE}/raw_logs/tlm/{TARGET}/`
- Decommutated logs: `{SCOPE}/decom_logs/tlm/{TARGET}/`  
- Command logs: `{SCOPE}/raw_logs/cmd/{TARGET}/`
- Script Runner logs: `{SCOPE}/logs/script_runner/`

**Config Buckets:**
- Target configs: `{SCOPE}/targets/{TARGET}/`
- Modified configs: `{SCOPE}/targets_modified/{TARGET}/`
- Target archives: `{SCOPE}/target_archives/{TARGET}/`

## 7. External Python Scripts

### Direct API Access Pattern

```python
#!/usr/bin/env python3

import os
import tempfile

# Set environment variables
os.environ["OPENC3_API_SCHEMA"] = "http"
os.environ["OPENC3_API_HOSTNAME"] = "localhost" 
os.environ["OPENC3_API_PORT"] = "2900"
os.environ["OPENC3_SCRIPT_API_SCHEMA"] = "http"
os.environ["OPENC3_SCRIPT_API_HOSTNAME"] = "localhost"
os.environ["OPENC3_SCRIPT_API_PORT"] = "2900"
os.environ["OPENC3_API_PASSWORD"] = "password"
os.environ["OPENC3_NO_STORE"] = "1"

# Import COSMOS Python API
from openc3.utilities.string import formatted
from openc3.script import *

# Use standard COSMOS API calls
print("Targets:", get_target_names())
print("Telemetry:", tlm("INST ADCS POSX"))
cmd("INST ABORT")

# File operations
put_target_file("INST/test.txt", "Hello World")
file = get_target_file("INST/test.txt")
print("File contents:", file.read())
file.close()
delete_target_file("INST/test.txt")
```

## 8. Complete Workflow Example

### End-to-End Test Suite Automation

```bash
#!/bin/bash

# 1. Authenticate
echo "Authenticating..."
TOKEN=$(curl -s -X POST \
  "http://localhost:2900/openc3-api/auth/verify?scope=DEFAULT" \
  -H "Content-Type: application/json" \
  -d '{"password": "password"}')

if [ -z "$TOKEN" ]; then
  echo "Authentication failed"
  exit 1
fi

echo "Got token: $TOKEN"

# 2. Upload test script
echo "Uploading test script..."
cat > test_suite.py << 'EOF'
from openc3.script import *

class TestSuite(Suite):
    def setup(self):
        print("Setting up test suite")
        
    def start(self):
        print("Running test cases")
        # Add your test logic here
        cmd("INST COLLECT with TYPE NORMAL, DURATION 1")
        wait(2)
        
    def teardown(self):
        print("Cleaning up test suite")

suite = TestSuite()
EOF

SCRIPT_CONTENT=$(cat test_suite.py | jq -R -s .)
curl -X POST \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"text\": $SCRIPT_CONTENT, \"breakpoints\": []}" \
  "http://localhost:2900/script-api/scripts/INST/test_suite.py?scope=DEFAULT"

# 3. Run test suite
echo "Running test suite..."
RUNNING_ID=$(curl -s -X POST \
  -H "Authorization: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "suiteRunner": {
      "suite": "TestSuite",
      "method": "start",
      "options": ["continueAfterError"]
    }
  }' \
  "http://localhost:2900/script-api/scripts/INST/test_suite.py/run?scope=DEFAULT")

echo "Script running with ID: $RUNNING_ID"

# 4. Poll for completion
echo "Monitoring execution..."
while true; do
  STATUS=$(curl -s -H "Authorization: $TOKEN" \
    "http://localhost:2900/script-api/running-script/$RUNNING_ID?scope=DEFAULT")
  
  if echo "$STATUS" | jq -e '.state' | grep -q '"error\|completed\|stopped"'; then
    echo "Script finished with state: $(echo "$STATUS" | jq -r '.state')"
    break
  fi
  
  echo "Still running... (state: $(echo "$STATUS" | jq -r '.state'))"
  sleep 5
done

# 5. Retrieve logs
echo "Retrieving script logs..."
LOG_FILES=$(curl -s -H "Authorization: $TOKEN" \
  "http://localhost:2900/openc3-api/storage/files/logs/?path=DEFAULT/logs/script_runner/&scope=DEFAULT")

# Find the most recent log file for our script
LOG_FILE=$(echo "$LOG_FILES" | jq -r '.[1][] | select(.name | contains("test_suite.py")) | .name' | head -1)

if [ ! -z "$LOG_FILE" ]; then
  echo "Downloading log file: $LOG_FILE"
  LOG_DATA=$(curl -s -H "Authorization: $TOKEN" \
    "http://localhost:2900/openc3-api/storage/download_file/DEFAULT/logs/script_runner/$LOG_FILE?scope=DEFAULT")
  
  echo "$LOG_DATA" | jq -r '.contents' | base64 -d > "test_results.log"
  echo "Log saved to test_results.log"
fi

echo "Workflow complete!"
```

### Bash Script for Suite Management

```bash
#!/bin/bash

# COSMOS Suite Manager
COSMOS_BASE="http://localhost:2900"
SCOPE="DEFAULT"

authenticate() {
    TOKEN=$(curl -s -X POST \
      "$COSMOS_BASE/openc3-api/auth/verify?scope=$SCOPE" \
      -H "Content-Type: application/json" \
      -d "{\"password\": \"$COSMOS_PASSWORD\"}")
    
    if [ -z "$TOKEN" ]; then
        echo "Authentication failed"
        exit 1
    fi
    echo "$TOKEN"
}

list_running_scripts() {
    local token=$1
    curl -s -H "Authorization: $token" \
      "$COSMOS_BASE/script-api/running-script?scope=$SCOPE" | \
      jq -r '.items[] | "\(.name) - \(.state) - \(.filename)"'
}

stop_all_scripts() {
    local token=$1
    local running=$(curl -s -H "Authorization: $token" \
      "$COSMOS_BASE/script-api/running-script?scope=$SCOPE")
    
    echo "$running" | jq -r '.items[].name' | while read script_id; do
        echo "Stopping script: $script_id"
        curl -s -X POST -H "Authorization: $token" \
          "$COSMOS_BASE/script-api/running-script/$script_id/stop?scope=$SCOPE"
    done
}

# Usage
TOKEN=$(authenticate)
echo "Available commands: list_running, stop_all"
```

## Security Notes

1. **Token Management**: Session tokens should be treated as credentials and not logged
2. **HTTPS**: Use HTTPS in production environments  
3. **Scope Isolation**: Different scopes provide isolation between environments
4. **Authorization**: Most endpoints require proper authorization headers
5. **File Paths**: Always validate and sanitize file paths in storage operations

## Error Handling

Common HTTP status codes:
- `200`: Success
- `401`: Unauthorized (invalid/missing token)
- `403`: Forbidden (insufficient permissions) 
- `404`: Not Found (script/resource doesn't exist)
- `500`: Internal Server Error

Example error response:
```json
{
  "status": "error",
  "message": "Script not found",
  "type": "OpenC3::ForbiddenError"
}
```