"""
Configuration constants for the DDoS Shield system.
"""

# --- AST-Based Rate Limiting ---
RATE_LIMIT_THRESHOLD = 50  # Max identical structure queries per window
RATE_LIMIT_WINDOW = 10  # Window in seconds

# --- IP-Based Rate Limiting ---
IP_REQUESTS_PER_SECOND = 10
IP_REQUESTS_PER_MINUTE = 100
IP_MAX_CONNECTIONS = 20

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

# --- Worker Pool ---
NUM_WORKERS = 4
WORKER_TIMEOUT_SECONDS = 30

# --- Enhanced Priority System ---
# Priority levels (lower number = higher priority, processed first)
PRIORITY_METRO_VERIFIED = 1    # Metro city, verified by IP geolocation
PRIORITY_METRO_CLAIMED = 2     # Metro city from header only (unverified)
PRIORITY_TIER2_CITY = 3        # Large non-metro cities
PRIORITY_STANDARD = 4          # Everything else
PRIORITY_SUSPICIOUS = 5        # Spoofing detected (header contradicts IP)

# Backward compatibility
PRIORITY_METRO = PRIORITY_METRO_VERIFIED

# --- City Classifications ---
# Tier 1: Metro cities (highest priority when verified)
METRO_CITIES = {
    "mumbai", "delhi", "bangalore", "bengaluru", "chennai",
    "kolkata", "hyderabad", "pune", "new delhi"
}

# Tier 2: Large non-metro cities
TIER2_CITIES = {
    "ahmedabad", "surat", "jaipur", "lucknow", "kanpur", "nagpur",
    "indore", "thane", "bhopal", "visakhapatnam", "patna", "vadodara",
    "ghaziabad", "ludhiana", "agra", "nashik", "faridabad", "meerut",
    "rajkot", "varanasi", "srinagar", "aurangabad", "dhanbad", "amritsar",
    "noida", "gurgaon", "gurugram", "coimbatore", "kochi", "trivandrum"
}

# --- Geolocation Settings ---
GEOIP_CACHE_MAX_ENTRIES = 100000
GEOIP_CACHE_TTL_SECONDS = 86400  # 24 hours
GEOIP_API_URL = "http://ip-api.com/json/{ip}?fields=status,city,country,regionName"
GEOIP_API_TIMEOUT = 2  # seconds

# --- Spoofing Detection ---
ENABLE_SPOOFING_DETECTION = True
DEMOTE_SPOOFING_TO_SUSPICIOUS = True
LOG_SPOOFING_ATTEMPTS = True

# Private/local IPs that skip geolocation lookup
LOCAL_IP_PREFIXES = ("127.", "10.", "192.168.", "172.16.", "172.17.", "172.18.",
                     "172.19.", "172.20.", "172.21.", "172.22.", "172.23.",
                     "172.24.", "172.25.", "172.26.", "172.27.", "172.28.",
                     "172.29.", "172.30.", "172.31.", "::1", "localhost")
