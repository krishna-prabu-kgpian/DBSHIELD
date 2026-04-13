"""
Configuration constants for the DDoS Shield system.
"""

# --- AST-Based Rate Limiting ---
RATE_LIMIT_THRESHOLD = 50  # Max identical structure queries per window
RATE_LIMIT_WINDOW = 10  # Window in seconds

# --- IP-Based Rate Limiting ---
IP_REQUESTS_PER_SECOND = 10
IP_REQUESTS_PER_MINUTE = 100

# --- Penalty Escalation ---
VIOLATIONS_FOR_TEMP_BAN = 3
VIOLATIONS_FOR_BLACKLIST = 10
BASE_BAN_SECONDS = 60
BAN_MULTIPLIER = 2  # Each violation doubles ban time
MAX_BAN_SECONDS = 3600  # Max 1 hour

# --- Full Result Cache ---
FULL_CACHE_MAX_ENTRIES = 10000
FULL_CACHE_MAX_MEMORY_BYTES = 100 * 1024 * 1024  # 100MB
FULL_CACHE_TTL_SECONDS = 300  # 5 minutes

# --- Intermediate (Mid-AST) Cache ---
INTERMEDIATE_CACHE_MAX_PER_TABLE = 1000
INTERMEDIATE_CACHE_TTL_SECONDS = 300  # 5 minutes

# --- Query History (Memory-Bounded) ---
QUERY_HISTORY_MAX_ENTRIES = 50000
QUERY_HISTORY_TTL_SECONDS = 60
QUERY_HISTORY_CLEANUP_INTERVAL = 30

# --- Request Validation ---
MAX_QUERY_LENGTH = 10000  # 10KB
MAX_BODY_SIZE = 50000  # 50KB
BLOCKED_SQL_KEYWORDS = {"DROP", "DELETE", "TRUNCATE", "ALTER", "EXEC", "GRANT", "REVOKE"}
