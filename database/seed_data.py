import argparse
import random
import sys
from decimal import Decimal
from pathlib import Path
from dotenv import load_dotenv
import psycopg
from psycopg import sql
import os

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

host = os.getenv("DB_HOST")
port = os.getenv("DB_PORT")
dbname = os.getenv("DB_NAME")
user = os.getenv("DB_USER")
password = os.getenv("DB_PASSWORD")

def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(
		description="Reset PostgreSQL tables, apply schema SQL, and seed arbitrary data."
	)
	parser.add_argument("--host", default=host, help="PostgreSQL host")
	parser.add_argument("--port", type=int, default=port, help="PostgreSQL port")
	parser.add_argument("--user", default=user, help="PostgreSQL username")
	parser.add_argument("--password", default=password, help="PostgreSQL password")
	parser.add_argument("--dbname", default=dbname, help="PostgreSQL database name")
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


def drop_all_tables(connection: psycopg.Connection, schema: str = "public") -> None:
	with connection.cursor() as cursor:
		cursor.execute(
			"""
			SELECT tablename
			FROM pg_tables
			WHERE schemaname = %s
			""",
			(schema,),
		)
		table_names = [row[0] for row in cursor.fetchall()]

		for table_name in table_names:
			cursor.execute(
				sql.SQL("DROP TABLE IF EXISTS {} CASCADE").format(
					sql.Identifier(table_name)
				)
			)


def apply_schema_sql(connection: psycopg.Connection, sql_file_path: Path) -> None:
	if not sql_file_path.exists():
		raise FileNotFoundError(f"SQL file not found: {sql_file_path}")

	sql_content = sql_file_path.read_text(encoding="utf-8")
	with connection.cursor() as cursor:
		cursor.execute(sql_content)


def batched(iterable, batch_size: int):
	batch = []
	for item in iterable:
		batch.append(item)
		if len(batch) == batch_size:
			yield batch
			batch = []
	if batch:
		yield batch


def seed_data(connection: psycopg.Connection, total_users: int, batch_size: int) -> None:
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

	with connection.cursor() as cursor:
		cursor.execute(
			"""
			INSERT INTO users (username, email, password, role, name, phone)
			VALUES (%s, %s, %s, %s, %s, %s)
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

	with connection.cursor() as cursor:
		for user_batch in batched(student_users, batch_size):
			cursor.executemany(
				"""
				INSERT INTO users (username, email, password, role, name, phone)
				VALUES (%s, %s, %s, %s, %s, %s)
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

	with connection.cursor() as cursor:
		for student_batch in batched(student_rows, batch_size):
			cursor.executemany(
				"""
				INSERT INTO students (user_id, cgpa, graduation_year)
				VALUES (%s, %s, %s)
				""",
				student_batch,
			)


def main() -> None:
	args = parse_args()
	sql_file_path = Path(args.sql_file).resolve()

	connection_string = (
		f"host={args.host} port={args.port} dbname={args.dbname} "
		f"user={args.user} password={args.password}"
	)

	try:
		with psycopg.connect(connection_string, autocommit=False) as connection:
			drop_all_tables(connection)
			apply_schema_sql(connection, sql_file_path)
			seed_data(connection, args.rows, args.batch_size)
			connection.commit()

		print(
			f"Database reset complete. Applied {sql_file_path} and seeded {args.rows} users "
			f"(1 admin, {args.rows - 1} students)."
		)
	except Exception as exc:
		print(f"Failed to reset/seed database: {exc}", file=sys.stderr)
		raise


if __name__ == "__main__":
	main()
