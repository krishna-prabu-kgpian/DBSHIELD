"""
Caching layer for the DDoS Shield system.

Implements:
- Full result caching (exact query match)
- Intermediate/Mid-AST caching (superset query matching)
- Optimized locking and pre-compiled regex for ReDoS mitigation
"""

import asyncio
import hashlib
import sys
import time
import re
import sqlparse
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from config import (
    FULL_CACHE_MAX_ENTRIES,
    FULL_CACHE_MAX_MEMORY_BYTES,
    FULL_CACHE_TTL_SECONDS,
    INTERMEDIATE_CACHE_MAX_PER_TABLE,
    INTERMEDIATE_CACHE_TTL_SECONDS,
)

# --- Data Classes ---

@dataclass
class CacheEntry:
    """Represents a cached query result."""
    result: Any
    created_at: float
    last_accessed: float
    access_count: int = 0
    size_bytes: int = 0

@dataclass
class WhereCondition:
    """Single WHERE clause condition."""
    column: str
    operator: str  
    value: Any

    def to_tuple(self) -> Tuple:
        return (self.column.upper(), self.operator, self.value)

@dataclass
class ParsedQuery:
    """Structured representation of a parsed SQL query."""
    table_name: str
    select_columns: List[str]
    where_conditions: List[WhereCondition]
    original_query: str = ""

    def get_condition_key(self) -> str:
        """Generate a key from sorted conditions for cache lookup."""
        sorted_conds = sorted(
            [f"{c.column.upper()}{c.operator}{c.value}" for c in self.where_conditions]
        )
        return "|".join(sorted_conds)

@dataclass
class IntermediateCacheEntry:
    """Cache entry for intermediate results."""
    parsed_query: ParsedQuery
    result_set: List[Dict[str, Any]]
    created_at: float

# --- Full Result Cache ---

class FullResultCache:
    """
    Cache for complete query results.
    Key: hash(AST_structure + sorted_parameter_values)
    """

    def __init__(
        self,
        max_entries: int = FULL_CACHE_MAX_ENTRIES,
        max_memory_bytes: int = FULL_CACHE_MAX_MEMORY_BYTES,
        ttl_seconds: int = FULL_CACHE_TTL_SECONDS
    ):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
        self.max_entries = max_entries
        self.max_memory_bytes = max_memory_bytes
        self.ttl_seconds = ttl_seconds
        self.current_memory = 0
        self.hits = 0
        self.misses = 0

    async def get(self, cache_key: str) -> Optional[Any]:
        """Get cached result."""
        async with self._lock:
            if cache_key not in self._cache:
                self.misses += 1
                return None

            entry = self._cache[cache_key]
            current_time = time.time()

            if current_time - entry.created_at > self.ttl_seconds:
                self.current_memory -= entry.size_bytes
                del self._cache[cache_key]
                self.misses += 1
                return None

            entry.last_accessed = current_time
            entry.access_count += 1
            self.hits += 1
            return entry.result

    async def set(self, cache_key: str, result: Any):
        """Store result in cache. Heavy lifting done outside the lock."""
        # Estimate size outside the lock to prevent blocking the event loop
        size_bytes = sys.getsizeof(result)
        if isinstance(result, list):
            size_bytes += sum(sys.getsizeof(item) for item in result)

        current_time = time.time()

        async with self._lock:
            await self._evict_if_needed(size_bytes)
            self._cache[cache_key] = CacheEntry(
                result=result,
                created_at=current_time,
                last_accessed=current_time,
                access_count=1,
                size_bytes=size_bytes
            )
            self.current_memory += size_bytes

    async def _evict_if_needed(self, incoming_size: int):
        """Evict entries if over limits."""
        current_time = time.time()
        expired_keys = [
            k for k, v in self._cache.items()
            if current_time - v.created_at > self.ttl_seconds
        ]
        for key in expired_keys:
            self.current_memory -= self._cache[key].size_bytes
            del self._cache[key]

        while (
            len(self._cache) >= self.max_entries or
            self.current_memory + incoming_size > self.max_memory_bytes
        ):
            if not self._cache:
                break
            lru_key = min(self._cache.keys(), key=lambda k: self._cache[k].last_accessed)
            self.current_memory -= self._cache[lru_key].size_bytes
            del self._cache[lru_key]

    async def cleanup_expired(self):
        """Remove all expired entries."""
        async with self._lock:
            current_time = time.time()
            expired_keys = [
                k for k, v in self._cache.items()
                if current_time - v.created_at > self.ttl_seconds
            ]
            for key in expired_keys:
                self.current_memory -= self._cache[key].size_bytes
                del self._cache[key]

    async def get_stats(self) -> dict:
        """Get cache statistics."""
        async with self._lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                "entries": len(self._cache),
                "memory_bytes": self.current_memory,
                "memory_mb": round(self.current_memory / (1024 * 1024), 2),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate_percent": round(hit_rate, 2),
            }

# --- Query Parser for Mid-AST Caching ---

class QuerySupersetDetector:
    """Parses SQL queries and detects superset relationships."""

    def parse_query(self, sql: str) -> Optional[ParsedQuery]:
        try:
            parsed = sqlparse.parse(sql)
            if not parsed:
                return None
            stmt = parsed[0]
            table_name = self._extract_table_name(stmt)
            if not table_name:
                return None
            select_columns = self._extract_select_columns(stmt)
            where_conditions = self._extract_where_conditions(stmt)

            return ParsedQuery(
                table_name=table_name,
                select_columns=select_columns,
                where_conditions=where_conditions,
                original_query=sql
            )
        except Exception:
            return None

    def _extract_table_name(self, stmt) -> Optional[str]:
        from_seen = False
        for token in stmt.tokens:
            if from_seen:
                if token.ttype is None:  
                    name = str(token).split()[0]  
                    return name.upper().strip()
                elif token.ttype is not sqlparse.tokens.Whitespace:
                    return str(token).upper().strip()
            if token.ttype is sqlparse.tokens.Keyword and token.value.upper() == "FROM":
                from_seen = True
        return None

    def _extract_select_columns(self, stmt) -> List[str]:
        columns = []
        for token in stmt.tokens:
            if token.ttype is sqlparse.tokens.Keyword and token.value.upper() in ("FROM", "WHERE"):
                break
            if token.ttype is sqlparse.tokens.Wildcard:
                return ["*"]
            if isinstance(token, sqlparse.sql.IdentifierList):
                for identifier in token.get_identifiers():
                    columns.append(str(identifier).strip().upper())
            elif isinstance(token, sqlparse.sql.Identifier):
                columns.append(str(token).strip().upper())
        return columns if columns else ["*"]

    def _extract_where_conditions(self, stmt) -> List[WhereCondition]:
        conditions = []
        where_clause = None
        for token in stmt.tokens:
            if isinstance(token, sqlparse.sql.Where):
                where_clause = token
                break

        if not where_clause:
            return conditions

        where_text = str(where_clause)
        where_text = re.sub(r'^\s*WHERE\s+', '', where_text, flags=re.IGNORECASE)
        parts = re.split(r'\s+AND\s+', where_text, flags=re.IGNORECASE)

        for part in parts:
            condition = self._parse_condition(part.strip())
            if condition:
                conditions.append(condition)
        return conditions

    def _parse_condition(self, condition_str: str) -> Optional[WhereCondition]:
        patterns = [
            (r'(\w+)\s*(>=|<=|!=|<>|=|>|<)\s*(\d+)', 'numeric'),
            (r"(\w+)\s*(>=|<=|!=|<>|=|>|<)\s*'([^']*)'", 'string'),
            (r'(\w+)\s*(>=|<=|!=|<>|=|>|<)\s*"([^"]*)"', 'string'),
            (r'(\w+)\s+LIKE\s+[\'"]([^\'"]*)[\'"]', 'like'),
            (r'(\w+)\s+IN\s*\(([^)]+)\)', 'in'),
        ]

        for pattern, value_type in patterns:
            match = re.match(pattern, condition_str, re.IGNORECASE)
            if match:
                groups = match.groups()
                column = groups[0].upper()

                if value_type == 'numeric':
                    operator = groups[1]
                    value = int(groups[2]) if '.' not in groups[2] else float(groups[2])
                elif value_type == 'string':
                    operator = groups[1]
                    value = groups[2]
                elif value_type == 'like':
                    operator = 'LIKE'
                    value = groups[1]
                elif value_type == 'in':
                    operator = 'IN'
                    in_values = [v.strip().strip("'\"") for v in groups[1].split(',')]
                    value = tuple(in_values)
                else:
                    continue
                return WhereCondition(column=column, operator=operator, value=value)
        return None

    def is_superset_of(self, query_b: ParsedQuery, query_a: ParsedQuery) -> Tuple[bool, List[WhereCondition]]:
        if query_b.table_name != query_a.table_name:
            return False, []

        if query_a.select_columns != ["*"]:
            if query_b.select_columns != ["*"]:
                if not set(query_b.select_columns).issubset(set(query_a.select_columns)):
                    return False, []

        a_conditions_set = {c.to_tuple() for c in query_a.where_conditions}
        b_conditions_set = {c.to_tuple() for c in query_b.where_conditions}

        if not a_conditions_set.issubset(b_conditions_set):
            return False, []

        additional_tuples = b_conditions_set - a_conditions_set
        additional_conditions = [
            WhereCondition(column=t[0], operator=t[1], value=t[2])
            for t in additional_tuples
        ]
        return True, additional_conditions

# --- In-Memory Result Filtering ---

class InMemoryFilter:
    """Applies additional WHERE conditions to cached result sets in memory with pre-compiled regex."""

    def filter_results(self, result_set: List[Dict[str, Any]], conditions: List[WhereCondition]) -> List[Dict[str, Any]]:
        if not conditions:
            return result_set

        # Pre-compile regex patterns for LIKE operators OUTSIDE the row loop
        # This prevents ReDoS and massive CPU spikes on large datasets
        compiled_conditions = []
        for cond in conditions:
            if cond.operator == "LIKE":
                pattern = str(cond.value).replace("%", ".*").replace("_", ".")
                regex = re.compile(f"^{pattern}$", re.IGNORECASE)
                compiled_conditions.append((cond, regex))
            else:
                compiled_conditions.append((cond, None))

        filtered = []
        for row in result_set:
            if self._row_matches_all(row, compiled_conditions):
                filtered.append(row)

        return filtered

    def _row_matches_all(self, row: Dict[str, Any], compiled_conditions: List[Tuple[WhereCondition, Any]]) -> bool:
        for cond, regex in compiled_conditions:
            column_value = row.get(cond.column) or row.get(cond.column.lower())
            if column_value is None:
                return False
            if not self._evaluate_condition(column_value, cond.operator, cond.value, regex):
                return False
        return True

    def _evaluate_condition(self, actual: Any, operator: str, expected: Any, regex: Any) -> bool:
        try:
            if operator == "=":
                return actual == expected
            elif operator in ("!=", "<>"):
                return actual != expected
            elif operator == ">":
                return actual > expected
            elif operator == "<":
                return actual < expected
            elif operator == ">=":
                return actual >= expected
            elif operator == "<=":
                return actual <= expected
            elif operator == "IN":
                return str(actual) in expected
            elif operator == "LIKE":
                return bool(regex.match(str(actual)))
            else:
                return False
        except (TypeError, ValueError):
            return False

# --- Intermediate Result Cache ---

class IntermediateResultCache:
    """Cache for intermediate/partial results enabling mid-AST matching."""

    def __init__(self, max_per_table: int = INTERMEDIATE_CACHE_MAX_PER_TABLE, ttl_seconds: int = INTERMEDIATE_CACHE_TTL_SECONDS):
        self._cache: Dict[str, Dict[str, IntermediateCacheEntry]] = defaultdict(dict)
        self._lock = asyncio.Lock()
        self.max_per_table = max_per_table
        self.ttl_seconds = ttl_seconds
        self.detector = QuerySupersetDetector()
        self.filter = InMemoryFilter()
        self.hits = 0
        self.misses = 0

    async def find_reusable_cache(self, incoming_query: ParsedQuery) -> Optional[Tuple[List[Dict], List[WhereCondition]]]:
        async with self._lock:
            table = incoming_query.table_name
            if table not in self._cache:
                self.misses += 1
                return None

            current_time = time.time()
            candidates = []

            for cache_key, entry in list(self._cache[table].items()):
                if current_time - entry.created_at > self.ttl_seconds:
                    del self._cache[table][cache_key]
                    continue

                is_superset, additional_conds = self.detector.is_superset_of(incoming_query, entry.parsed_query)
                if is_superset:
                    score = len(additional_conds)
                    candidates.append((score, entry, additional_conds))

            if not candidates:
                self.misses += 1
                return None

            candidates.sort(key=lambda x: x[0])
            best = candidates[0]
            self.hits += 1
            return best[1].result_set, best[2]

    async def set(self, parsed_query: ParsedQuery, result: List[Dict[str, Any]]):
        table = parsed_query.table_name
        cache_key = parsed_query.get_condition_key()
        entry = IntermediateCacheEntry(parsed_query=parsed_query, result_set=result, created_at=time.time())

        async with self._lock:
            if len(self._cache[table]) >= self.max_per_table:
                oldest_key = min(self._cache[table].keys(), key=lambda k: self._cache[table][k].created_at)
                del self._cache[table][oldest_key]
            self._cache[table][cache_key] = entry

    async def cleanup_expired(self):
        async with self._lock:
            current_time = time.time()
            for table in list(self._cache.keys()):
                expired = [k for k, v in self._cache[table].items() if current_time - v.created_at > self.ttl_seconds]
                for key in expired:
                    del self._cache[table][key]
                if not self._cache[table]:
                    del self._cache[table]

    async def get_stats(self) -> dict:
        async with self._lock:
            total_entries = sum(len(entries) for entries in self._cache.values())
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0
            return {
                "tables_cached": len(self._cache),
                "total_entries": total_entries,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate_percent": round(hit_rate, 2),
            }

# --- Cache Key Computation ---

def compute_full_cache_key(sql_query: str) -> str:
    try:
        parsed = sqlparse.parse(sql_query)
        if not parsed:
            return hashlib.sha256(sql_query.encode()).hexdigest()

        stmt = parsed[0]
        normalized_tokens = []
        param_values = []

        for token in stmt.flatten():
            if token.is_whitespace:
                continue

            is_literal = (
                token.ttype in (
                    sqlparse.tokens.Literal.Number.Integer,
                    sqlparse.tokens.Literal.Number.Float,
                    sqlparse.tokens.Literal.String.Single,
                    sqlparse.tokens.Literal.String.Symbol,
                ) or
                (token.ttype is not None and 'Literal' in str(token.ttype))
            )

            if is_literal:
                param_values.append(str(token))
                normalized_tokens.append("?")
            else:
                normalized_tokens.append(str(token).upper())

        ast_structure = " ".join(normalized_tokens)
        params_str = "|".join(param_values)
        combined = f"{ast_structure}||{params_str}"
        return hashlib.sha256(combined.encode()).hexdigest()
    except Exception:
        return hashlib.sha256(sql_query.encode()).hexdigest()

def normalize_and_hash(sql_query: str) -> str:
    try:
        parsed = sqlparse.parse(sql_query)
        if not parsed:
            return ""

        stmt = parsed[0]
        normalized_tokens = []
        for token in stmt.flatten():
            if token.is_whitespace:
                continue

            is_literal = (
                token.ttype in (
                    sqlparse.tokens.Literal.Number.Integer,
                    sqlparse.tokens.Literal.Number.Float,
                    sqlparse.tokens.Literal.String.Single,
                    sqlparse.tokens.Literal.String.Symbol,
                ) or
                (token.ttype is not None and 'Literal' in str(token.ttype))
            )

            if is_literal:
                normalized_tokens.append("?")
            else:
                normalized_tokens.append(str(token).upper())

        normalized_query = " ".join(normalized_tokens)
        return hashlib.sha256(normalized_query.encode()).hexdigest()
    except Exception:
        return hashlib.sha256(sql_query.encode()).hexdigest()