# --- GEODATA-OSM CORPORATE IDENTITY UTILS (PYTHON) ---

C_RESET = "\033[0m"
C_BOLD = "\033[1m"
C_PURPLE = "\033[1;35m"
C_BLUE = "\033[1;34m"
C_GREEN = "\033[1;32m"
C_YELLOW = "\033[1;33m"
C_RED = "\033[1;31m"
C_CYAN = "\033[0;36m"

S_HEADER = "▶▶▶"
S_INFO = "  ℹ"
S_SUCCESS = "  ✔"
S_WARN = "  ⚠"
S_ERROR = "  ✖"

def log_header(msg):
    print(f"\n{C_PURPLE}{S_HEADER} {msg}{C_RESET}")

def log_info(msg):
    print(f"{C_BLUE}{S_INFO}{C_RESET} {msg}")

def log_success(msg):
    print(f"{C_GREEN}{S_SUCCESS}{C_RESET} {msg}")

def log_warn(msg):
    print(f"{C_YELLOW}{S_WARN}{C_RESET} {msg}")

def log_error(msg):
    print(f"{C_RED}{S_ERROR}{C_RESET} {msg}")

def log_step(current, total, msg):
    print(f"{C_BOLD}[{current}/{total}]{C_RESET} {msg}")
