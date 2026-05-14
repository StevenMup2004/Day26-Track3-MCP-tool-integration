from __future__ import annotations

import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = Path(__file__).with_name("sqlite_lab.db")


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS enrollments;
DROP TABLE IF EXISTS courses;
DROP TABLE IF EXISTS students;

CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    cohort TEXT NOT NULL,
    age INTEGER NOT NULL CHECK (age > 0),
    score REAL NOT NULL CHECK (score >= 0 AND score <= 100),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE enrollments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    course_id INTEGER NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'completed', 'dropped')),
    score REAL NOT NULL CHECK (score >= 0 AND score <= 100),
    enrolled_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    UNIQUE (student_id, course_id)
);
"""


STUDENTS = [
    ("An Nguyen", "an.nguyen@example.com", "A1", 21, 88.5),
    ("Binh Tran", "binh.tran@example.com", "A1", 22, 91.0),
    ("Chi Le", "chi.le@example.com", "A2", 20, 84.0),
    ("Dung Pham", "dung.pham@example.com", "A2", 23, 77.5),
    ("Hanh Vo", "hanh.vo@example.com", "B1", 21, 95.0),
    ("Minh Dang", "minh.dang@example.com", "B1", 24, 69.5),
]


COURSES = [
    ("MCP101", "Model Context Protocol Basics", 3),
    ("SQL201", "Safe SQL with SQLite", 4),
    ("AI301", "Applied AI Agents", 3),
]


ENROLLMENTS = [
    (1, 1, "completed", 90.0),
    (1, 2, "active", 87.0),
    (2, 1, "completed", 92.0),
    (2, 3, "active", 90.0),
    (3, 1, "completed", 83.0),
    (3, 2, "active", 85.0),
    (4, 2, "completed", 78.0),
    (5, 1, "completed", 96.0),
    (5, 3, "active", 94.0),
    (6, 3, "dropped", 70.0),
]


def create_database(db_path: str | Path = DEFAULT_DB_PATH) -> Path:
    """Create a fresh SQLite database with deterministic schema and seed data."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(SCHEMA_SQL)
        connection.executemany(
            """
            INSERT INTO students (name, email, cohort, age, score)
            VALUES (?, ?, ?, ?, ?)
            """,
            STUDENTS,
        )
        connection.executemany(
            """
            INSERT INTO courses (code, title, credits)
            VALUES (?, ?, ?)
            """,
            COURSES,
        )
        connection.executemany(
            """
            INSERT INTO enrollments (student_id, course_id, status, score)
            VALUES (?, ?, ?, ?)
            """,
            ENROLLMENTS,
        )
        connection.commit()

    return path


if __name__ == "__main__":
    database_path = create_database()
    print(f"Created SQLite database at {database_path}")
