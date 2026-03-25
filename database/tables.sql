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
    cgpa numeric(4, 2) not null,
    graduation_year integer not null
);