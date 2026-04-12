create table if not exists users (
    id serial primary key,
    username varchar(255) unique not null,
    email varchar(255) unique not null,
    password varchar(255) not null,
    role varchar(50) not null,
    name varchar(255) not null,
    phone varchar(20)
);

create table if not exists students (
    id serial primary key,
    user_id integer references users(id) on delete cascade,
    cgpa numeric(4, 2) not null check (cgpa >= 0.00 and cgpa <= 10.00),
    graduation_year integer not null
);

create table if not exists courses (
    id serial primary key,
    course_code varchar(50) unique not null,
    course_title varchar(255) not null,
    department varchar(100),
    instructor_id integer references users(id) on delete set null,
    credits integer default 3,
    semester varchar(20),
    created_date timestamp default now()
);

create table if not exists enrollments (
    id serial primary key,
    student_id integer references users(id) on delete cascade,
    course_id integer references courses(id) on delete cascade,
    enrollment_date timestamp default now(),
    status varchar(50) default 'enrolled',
    admitted_date timestamp,
    grade varchar(2),
    graded_date timestamp,
    unique(student_id, course_id)
);

create table if not exists assignments (
    id serial primary key,
    course_id integer references courses(id) on delete cascade,
    title varchar(255) not null,
    description text,
    due_date timestamp,
    created_date timestamp default now()
);