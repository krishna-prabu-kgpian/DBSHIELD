create table if not exists users (
    id integer primary key autoincrement,
    username text unique not null,
    email text unique not null,
    password text not null,
    role text not null,
    name text not null,
    phone text
);

create table if not exists students (
    id integer primary key autoincrement,
    user_id integer references users(id) on delete cascade,
    cgpa numeric(4, 2) not null check (cgpa >= 0.00 and cgpa <= 10.00),
    graduation_year integer not null
);

create table if not exists courses (
    id integer primary key autoincrement,
    course_code text unique not null,
    course_title text not null,
    department text,
    instructor_id integer references users(id) on delete set null,
    credits integer default 3,
    semester text,
    created_date datetime default current_timestamp
);

create table if not exists enrollments (
    id integer primary key autoincrement,
    student_id integer references users(id) on delete cascade,
    course_id integer references courses(id) on delete cascade,
    enrollment_date datetime default current_timestamp,
    status text default 'enrolled',
    admitted_date datetime,
    grade text,
    graded_date datetime,
    unique(student_id, course_id)
);

create table if not exists assignments (
    id integer primary key autoincrement,
    course_id integer references courses(id) on delete cascade,
    title text not null,
    description text,
    due_date datetime,
    created_date datetime default current_timestamp
);
