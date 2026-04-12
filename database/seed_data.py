import argparse
import random
import sys
from pathlib import Path
import os
import sqlite3

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
		cgpa_value = round(random.uniform(0.0, 10.0), 2)
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
	
	# Seed Courses
	print("🎓 Seeding courses...")
	courses_data = [
		("CS101", "Introduction to Programming", "CSE", 1, 3, "Spring 2026"),
		("CS205", "Data Structures", "CSE", 1, 3, "Spring 2026"),
		("CS301", "Algorithms", "CSE", 1, 4, "Spring 2026"),
		("MA201", "Discrete Mathematics", "MATH", 1, 3, "Spring 2026"),
		("MA101", "Calculus I", "MATH", 1, 4, "Spring 2026"),
		("PH101", "Physics I", "PHY", 1, 3, "Spring 2026"),
		("CH101", "Chemistry", "CHE", 1, 3, "Spring 2026"),
		("HS110", "Communication Skills", "HS", 1, 2, "Spring 2026"),
		("CS401", "Database Systems", "CSE", 1, 4, "Spring 2026"),
		("CS501", "Web Development", "CSE", 1, 3, "Spring 2026"),
		("CS251", "Object-Oriented Programming", "CSE", 1, 3, "Spring 2026"),
		("MA301", "Linear Algebra", "MATH", 1, 3, "Spring 2026"),
	]
	
	cursor.executemany(
		"""
		INSERT INTO courses (course_code, course_title, department, instructor_id, credits, semester)
		VALUES (?, ?, ?, ?, ?, ?)
		""",
		courses_data,
	)
	print(f"✅ Seeded {len(courses_data)} courses")
	
	# Seed Enrollments - Enroll students randomly
	print("📝 Seeding enrollments...")
	cursor.execute("SELECT id FROM courses")
	course_ids = [row[0] for row in cursor.fetchall()]
	
	enrollment_rows = []
	for student_id in range(2, min(total_users + 1, 1002)):  # Limit to 1000 students for performance
		num_courses = random.randint(3, 6)
		selected_courses = random.sample(course_ids, min(num_courses, len(course_ids)))
		
		for course_id in selected_courses:
			# 70% chance of being admitted, 30% pending
			status = random.choices(["admitted", "enrolled"], weights=[70, 30])[0]
			grade = random.choices(
				["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F", None],
				weights=[10, 8, 12, 15, 10, 9, 12, 6, 3, 2, 2, 12]
			)[0]
			
			enrollment_rows.append((student_id, course_id, status, grade))
	
	cursor = connection.cursor()
	for enrollment_batch in batched(enrollment_rows, batch_size):
		cursor.executemany(
			"""
			INSERT INTO enrollments (student_id, course_id, status, grade)
			VALUES (?, ?, ?, ?)
			""",
			enrollment_batch,
		)
	print(f"✅ Seeded {len(enrollment_rows)} enrollments")
	
	# Seed Assignments
	print("📚 Seeding assignments...")
	assignment_titles = [
		"Problem Set 1",
		"Problem Set 2", 
		"Midterm Project",
		"Final Project",
		"Quiz 1",
		"Quiz 2",
		"Lab Assignment 1",
		"Lab Assignment 2",
		"Case Study",
		"Research Paper",
	]
	
	assignment_rows = []
	for course_id in course_ids:
		num_assignments = random.randint(3, 8)
		selected_titles = random.sample(assignment_titles, min(num_assignments, len(assignment_titles)))
		
		for title in selected_titles:
			description = f"Complete {title} for this course"
			assignment_rows.append((course_id, title, description))
	
	cursor = connection.cursor()
	for assignment_batch in batched(assignment_rows, batch_size):
		cursor.executemany(
			"""
			INSERT INTO assignments (course_id, title, description)
			VALUES (?, ?, ?)
			""",
			assignment_batch,
		)
	print(f"✅ Seeded {len(assignment_rows)} assignments")





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
			f"Database reset complete at {db_file}. Applied {sql_file_path}.\n"
			f"✅ Seeded data:\n"
			f"  - {args.rows} users (1 admin, {args.rows - 1} students)\n"
			f"  - 12 courses\n"
			f"  - Enrollments for up to 1000 students (randomly selected courses)\n"
			f"  - 40+ assignments across courses"
		)
	except Exception as exc:
		print(f"Failed to reset/seed database: {exc}", file=sys.stderr)
		raise


if __name__ == "__main__":
	main()
