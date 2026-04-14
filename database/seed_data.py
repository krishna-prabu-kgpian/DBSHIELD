import argparse
import random
import sys
from pathlib import Path
import os
import sqlite3
from datetime import datetime, timedelta

try:
	from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency in local demos
	def load_dotenv(*args, **kwargs):
		return False

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


def random_past_timestamp(max_days_back: int = 240) -> str:
	now = datetime.now()
	offset = timedelta(
		days=random.randint(1, max_days_back),
		hours=random.randint(0, 23),
		minutes=random.randint(0, 59),
		seconds=random.randint(0, 59),
	)
	return (now - offset).strftime("%Y-%m-%d %H:%M:%S")


def random_future_timestamp(min_days_ahead: int = 7, max_days_ahead: int = 90) -> str:
	now = datetime.now()
	offset = timedelta(
		days=random.randint(min_days_ahead, max_days_ahead),
		hours=random.randint(0, 23),
		minutes=random.randint(0, 59),
		seconds=random.randint(0, 59),
	)
	return (now + offset).strftime("%Y-%m-%d %H:%M:%S")


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
		f"""
		INSERT INTO users (username, email, password, role, name, phone)
		VALUES ('{admin_user[0]}', '{admin_user[1]}', '{admin_user[2]}', '{admin_user[3]}', '{admin_user[4]}', '{admin_user[5]}')
		"""
	)

	instructor_users = [
		("instructor1", "instructor1@example.com", "inst123", "instructor", "Instructor One", "8111000001"),
		("instructor2", "instructor2@example.com", "inst456", "instructor", "Instructor Two", "8111000002"),
	]

	for user in instructor_users:
		cursor.execute(
			f"""
			INSERT INTO users (username, email, password, role, name, phone)
			VALUES ('{user[0]}', '{user[1]}', '{user[2]}', '{user[3]}', '{user[4]}', '{user[5]}')
			"""
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

	for user_batch in batched(student_users, batch_size):
		for user in user_batch:
			cursor.execute(
				f"""
				INSERT INTO users (username, email, password, role, name, phone)
				VALUES ('{user[0]}', '{user[1]}', '{user[2]}', '{user[3]}', '{user[4]}', '{user[5]}')
				"""
			)

	cursor.execute("SELECT id FROM users WHERE role = 'student' ORDER BY id")
	student_user_ids = [row[0] for row in cursor.fetchall()]

	student_rows = []
	for user_id in student_user_ids:
		cgpa_value = round(random.uniform(0.0, 10.0), 2)
		student_rows.append((user_id, cgpa_value, random.randint(2026, 2032)))

	for student_batch in batched(student_rows, batch_size):
		for student in student_batch:
			cursor.execute(
				f"""
				INSERT INTO students (user_id, cgpa, graduation_year)
				VALUES ({student[0]}, {student[1]}, {student[2]})
				"""
			)

	print("🎓 Seeding courses...")
	courses_data = [
		("CS101", "Introduction to Programming", "CSE", 3, "Spring 2026"),
		("CS205", "Data Structures", "CSE", 3, "Spring 2026"),
		("CS301", "Algorithms", "CSE", 4, "Spring 2026"),
		("MA201", "Discrete Mathematics", "MATH", 3, "Spring 2026"),
		("MA101", "Calculus I", "MATH", 4, "Spring 2026"),
		("PH101", "Physics I", "PHY", 3, "Spring 2026"),
		("CH101", "Chemistry", "CHE", 3, "Spring 2026"),
		("HS110", "Communication Skills", "HS", 2, "Spring 2026"),
		("CS401", "Database Systems", "CSE", 4, "Spring 2026"),
		("CS501", "Web Development", "CSE", 3, "Spring 2026"),
		("CS251", "Object-Oriented Programming", "CSE", 3, "Spring 2026"),
		("MA301", "Linear Algebra", "MATH", 3, "Spring 2026"),
	]

	cursor.execute("SELECT id FROM users WHERE role = 'instructor' ORDER BY id")
	instructor_ids = [row[0] for row in cursor.fetchall()]
	fallback_instructor_id = instructor_ids[0] if instructor_ids else 1

	for course in courses_data:
		assigned_instructor = random.choice(instructor_ids) if instructor_ids else fallback_instructor_id
		cursor.execute(
			f"""
			INSERT INTO courses (course_code, course_title, department, instructor_id, credits, semester)
			VALUES ('{course[0]}', '{course[1]}', '{course[2]}', {assigned_instructor}, {course[3]}, '{course[4]}')
			"""
		)
	print(f"✅ Seeded {len(courses_data)} courses")

	cursor.execute("SELECT id, course_code FROM courses ORDER BY id")
	course_rows = cursor.fetchall()
	course_ids = [row[0] for row in course_rows]

	print("📝 Seeding enrollments...")
	enrollment_rows = []
	enrollment_student_ids = student_user_ids[: min(len(student_user_ids), 1500)]
	grade_values = ["A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F"]

	for student_id in enrollment_student_ids:
		num_courses = random.randint(3, 6)
		selected_courses = random.sample(course_ids, min(num_courses, len(course_ids)))

		for course_id in selected_courses:
			status = random.choices(["enrolled", "admitted", "completed"], weights=[25, 45, 30])[0]
			enrollment_date = random_past_timestamp(320)
			admitted_date = random_past_timestamp(260) if status in {"admitted", "completed"} else None

			grade = None
			graded_date = None
			should_grade = status == "completed" or (status == "admitted" and random.random() < 0.35)
			if should_grade:
				grade = random.choice(grade_values)
				graded_date = random_past_timestamp(180)

			enrollment_rows.append(
				(student_id, course_id, enrollment_date, status, admitted_date, grade, graded_date)
			)

	for enrollment_batch in batched(enrollment_rows, batch_size):
		for enrollment in enrollment_batch:
			admitted_date_sql = "NULL" if enrollment[4] is None else f"'{enrollment[4]}'"
			grade_sql = "NULL" if enrollment[5] is None else f"'{enrollment[5]}'"
			graded_date_sql = "NULL" if enrollment[6] is None else f"'{enrollment[6]}'"
			cursor.execute(
				f"""
				INSERT INTO enrollments (student_id, course_id, enrollment_date, status, admitted_date, grade, graded_date)
				VALUES ({enrollment[0]}, {enrollment[1]}, '{enrollment[2]}', '{enrollment[3]}', {admitted_date_sql}, {grade_sql}, {graded_date_sql})
				"""
			)
	print(f"✅ Seeded {len(enrollment_rows)} enrollments")

	print("📚 Seeding assignments...")
	assignment_titles = [
		"Problem Set",
		"Quiz",
		"Lab Assignment",
		"Case Study",
		"Midterm Project",
		"Final Project",
		"Reading Report",
		"Design Exercise",
		"Coding Task",
		"Research Note",
	]

	assignment_rows = []
	for course_id in course_ids:
		num_assignments = random.randint(4, 9)
		for index in range(1, num_assignments + 1):
			title = random.choice(assignment_titles)
			description = f"{title} for this course"
			due_date = random_future_timestamp(7, 95)
			assignment_rows.append((course_id, f"{title} {index}", description, due_date))

	for assignment_batch in batched(assignment_rows, batch_size):
		for assignment in assignment_batch:
			cursor.execute(
				f"""
				INSERT INTO assignments (course_id, title, description, due_date)
				VALUES ({assignment[0]}, '{assignment[1]}', '{assignment[2]}', '{assignment[3]}')
				"""
			)
	print(f"✅ Seeded {len(assignment_rows)} assignments")

	print("📎 Seeding course materials...")
	material_types = [
		"Lecture Notes",
		"Slides",
		"Tutorial Sheet",
		"Reference Reading",
		"Lab Guide",
		"Practice Questions",
	]

	material_rows = []
	for course_id, course_code in course_rows:
		num_materials = random.randint(5, 10)
		for week in range(1, num_materials + 1):
			material_type = random.choice(material_types)
			title = f"{material_type} Week {week}"
			slug = material_type.lower().replace(" ", "-")
			resource_link = f"https://resources.dbshield.local/{course_code.lower()}/{slug}-{week}"
			material_rows.append((course_id, title, resource_link))

	for material_batch in batched(material_rows, batch_size):
		for material in material_batch:
			cursor.execute(
				f"""
				INSERT INTO course_materials (course_id, title, resource_link)
				VALUES ({material[0]}, '{material[1]}', '{material[2]}')
				"""
			)
	print(f"✅ Seeded {len(material_rows)} materials")





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
			f"  - Enrollments for up to 1500 students (randomly selected courses)\n"
			f"  - Assignments with random due dates\n"
			f"  - Course materials with generated resource links"
		)
	except Exception as exc:
		print(f"Failed to reset/seed database: {exc}", file=sys.stderr)
		raise


if __name__ == "__main__":
	main()
