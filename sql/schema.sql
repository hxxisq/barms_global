create table if not exists projects (
    project_id   serial primary key,
    project_name text not null,
    location     text not null,
    created_at   timestamptz not null default now()
);

create table if not exists transactions (
    transaction_id   serial primary key,
    project_id       integer not null references projects(project_id),
    unit             text not null,
    transaction_date date not null default current_date,
    build_stage      text not null,
    category text not null check (category in (
    'labour',
    'transport & fuel',
    'professional fees',
    'miscellaneous',
    'funding',
    'accommodation',
    'public relation',
    'plumbing',
    'electrical'
)),
    description      text not null,
    credit           numeric(15, 2) not null default 0,
    debit            numeric(15, 2) not null default 0,
    is_funding       boolean not null default false,
    created_at       timestamptz not null default now()
);

create index if not exists idx_transactions_project_date
    on transactions (project_id, transaction_date desc);


-- insert into projects (project_id, project_name, location)
-- values (1, 'Barms Global Construction Project', 'Anyigba')
-- on conflict (project_id) do nothing;

-- CREATE TABLE users (
--     user_id SERIAL PRIMARY KEY,
--     username TEXT UNIQUE,
--     full_name TEXT,
--     password_hash TEXT,
--     role TEXT
-- );