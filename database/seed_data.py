import argparse
import random
import sys
from pathlib import Path
import os
import sqlite3
from decimal import Decimal

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

DEFAULT_DB_PATH = BASE_DIR / "dbshield.sqlite3"
db_path = os.getenv("SQLITE_DB_PATH", str(DEFAULT_DB_PATH))

def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Reset SQLite tables, apply schema SQL, and seed arbitrary data."
	)
	parser.add_argument(
		"--db-path",
		default=db_path,
		help="Path to the SQLite database file",
	)
	parser.add_argument(
		"--sql-file",
		default=str(Path(__file__).resolve().parents[1] / "database" / "tables.sql"),
		help="Path to SQL schema file",
	)
	parser.add_argument(
		"--rows",
		type=int,
		default=20000,
		help="Total number of users to seed (includes 1 admin)",
	)
	parser.add_argument(
		"--batch-size",
		type=int,
		default=1000,
		help="Batch size for inserts",
	)
	return parser.parse_args()


def drop_all_tables(connection: sqlite3.Connection) -> None:
	cursor = connection.cursor()
	cursor.execute(
		"""
		SELECT name
		FROM sqlite_master
		WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
		"""
	)
	table_names = [row[0] for row in cursor.fetchall()]

	for table_name in table_names:
		cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')


def apply_schema_sql(connection: sqlite3.Connection, sql_file_path: Path) -> None:
	if not sql_file_path.exists():
		raise FileNotFoundError(f"SQL file not found: {sql_file_path}")

	sql_content = sql_file_path.read_text(encoding="utf-8")
	connection.executescript(sql_content)


def batched(iterable, batch_size: int):
	batch = []
	for item in iterable:
		batch.append(item)
		if len(batch) == batch_size:
			yield batch
			batch = []
	if batch:
		yield batch


def seed_data(connection: sqlite3.Connection, total_users: int, batch_size: int) -> None:
	if total_users < 1:
		raise ValueError("--rows must be at least 1")

	student_count = total_users - 1

	admin_user = (
		"admin",
		"admin@dbshield.local",
		"admin123",
		"admin",
		"Admin User",
		"9000000000",
	)

	cursor = connection.cursor()
	cursor.execute(
		"""
		INSERT INTO users (username, email, password, role, name, phone)
		VALUES (?, ?, ?, ?, ?, ?)
		""",
		admin_user,
	)

	student_users = []
	for index in range(1, student_count + 1):
		student_users.append(
			(
				f"student{index}",
				f"student{index}@example.com",
				f"pass{index}",
				"student",
				f"Student {index}",
				f"9{index % 1_000_000_000:09d}",
			)
		)

	cursor = connection.cursor()
	for user_batch in batched(student_users, batch_size):
		cursor.executemany(
			"""
			INSERT INTO users (username, email, password, role, name, phone)
			VALUES (?, ?, ?, ?, ?, ?)
			""",
			user_batch,
		)

	student_rows = []
	for user_id in range(2, total_users + 1):
		cgpa_value = (Decimal(random.randint(0, 1000)) / Decimal("100")).quantize(
			Decimal("0.00")
		)
		student_rows.append(
			(
				user_id,
				cgpa_value,
				random.randint(2026, 2032),
			)
		)

	cursor = connection.cursor()
	for student_batch in batched(student_rows, batch_size):
		cursor.executemany(
			"""
			INSERT INTO students (user_id, cgpa, graduation_year)
			VALUES (?, ?, ?)
			""",
			student_batch,
		)


def main() -> None:
	args = parse_args()
	sql_file_path = Path(args.sql_file).resolve()
	db_file = Path(args.db_path).expanduser().resolve()
	db_file.parent.mkdir(parents=True, exist_ok=True)

	try:
		with sqlite3.connect(db_file) as connection:
			connection.execute("PRAGMA foreign_keys = ON")
			drop_all_tables(connection)
			apply_schema_sql(connection, sql_file_path)
			seed_data(connection, args.rows, args.batch_size)
			connection.commit()

		print(
			f"Database reset complete at {db_file}. Applied {sql_file_path} and seeded {args.rows} users "
			f"(1 admin, {args.rows - 1} students)."
		)
	except Exception as exc:
		print(f"Failed to reset/seed database: {exc}", file=sys.stderr)
		raise


if __name__ == "__main__":
	main()
