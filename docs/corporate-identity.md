# GEODATA-OSM CORPORATE IDENTITY (CI)

This directory contains standardized logging utilities for both Bash and Python to ensure a consistent look and feel across all CLI tools in the Geodata project family.

## Standards

| Level | Symbol | Color | Purpose |
| :--- | :--- | :--- | :--- |
| **Header** | `▶▶▶` | Purple | Main sections or major task groups |
| **Step** | `[1/x]` | Bold | Numbered steps within a process |
| **Info** | `ℹ` | Blue | Descriptive or informational messages |
| **Success** | `✔` | Green | Completed actions or successful states |
| **Warn** | `⚠` | Yellow | Potential issues that don't stop execution |
| **Error** | `✖` | Red | Critical failures that require attention |

## Usage

### Bash (`utils.sh`)
```bash
source scripts/ci/utils.sh

log_header "MY TASK"
log_step 1 2 "Initializing..."
log_info "Processing data..."
log_success "Task completed."
```

### Python (`utils.py`)
```python
from ci.utils import log_header, log_step, log_info, log_success

log_header("MY TASK")
log_step(1, 2, "Initializing...")
log_info("Processing data...")
log_success("Task completed.")
```

## Colors Reference
- `C_PURPLE`: `\033[1;35m`
- `C_BLUE`: `\033[1;34m`
- `C_GREEN`: `\033[1;32m`
- `C_YELLOW`: `\033[1;33m`
- `C_RED`: `\033[1;31m`
