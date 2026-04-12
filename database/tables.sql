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
