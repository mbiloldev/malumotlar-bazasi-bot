import aiosqlite

DB = "hulla.db"


async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS courses (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
                name      TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id  INTEGER NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                first_name TEXT NOT NULL,
                last_name  TEXT NOT NULL,
                age        INTEGER,
                phone      TEXT,
                username   TEXT,
                is_active  INTEGER DEFAULT 1
            )
        """)
        await db.commit()


# ── COURSES ──────────────────────────────────────────────────

async def add_course(name: str):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR IGNORE INTO courses(name) VALUES(?)", (name,))
        await db.commit()

async def get_courses():
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT id, name FROM courses ORDER BY id") as c:
            return await c.fetchall()

async def delete_course(cid: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM courses WHERE id=?", (cid,))
        await db.commit()

async def get_course(cid: int):
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT id, name FROM courses WHERE id=?", (cid,)) as c:
            return await c.fetchone()


# ── GROUPS ───────────────────────────────────────────────────

async def add_group(course_id: int, name: str):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT INTO groups(course_id, name) VALUES(?,?)", (course_id, name))
        await db.commit()

async def get_groups(course_id: int):
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT id, name FROM groups WHERE course_id=? ORDER BY id", (course_id,)
        ) as c:
            return await c.fetchall()

async def get_group(gid: int):
    async with aiosqlite.connect(DB) as db:
        async with db.execute("SELECT id, course_id, name FROM groups WHERE id=?", (gid,)) as c:
            return await c.fetchone()

async def delete_group(gid: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM groups WHERE id=?", (gid,))
        await db.commit()


# ── STUDENTS ─────────────────────────────────────────────────

async def add_student(group_id, first_name, last_name, age, phone, username):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO students(group_id,first_name,last_name,age,phone,username) VALUES(?,?,?,?,?,?)",
            (group_id, first_name, last_name, age, phone, username)
        )
        await db.commit()

async def get_students(group_id: int):
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT id,first_name,last_name,age,phone,username FROM students "
            "WHERE group_id=? AND is_active=1 ORDER BY id", (group_id,)
        ) as c:
            return await c.fetchall()

async def get_student(sid: int):
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT id,group_id,first_name,last_name,age,phone,username,is_active "
            "FROM students WHERE id=?", (sid,)
        ) as c:
            return await c.fetchone()

async def remove_student(sid: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE students SET is_active=0 WHERE id=?", (sid,))
        await db.commit()

async def search_by_id(sid: int):
    return await get_student(sid)

async def search_by_name(query: str):
    async with aiosqlite.connect(DB) as db:
        like = f"%{query}%"
        async with db.execute(
            "SELECT id,first_name,last_name,age,phone,username FROM students "
            "WHERE (first_name LIKE ? OR last_name LIKE ?) AND is_active=1",
            (like, like)
        ) as c:
            return await c.fetchall()

async def count_students(group_id: int) -> int:
    async with aiosqlite.connect(DB) as db:
        async with db.execute(
            "SELECT COUNT(*) FROM students WHERE group_id=? AND is_active=1", (group_id,)
        ) as c:
            row = await c.fetchone()
            return row[0] if row else 0

async def course_stats(course_id: int):
    """[(group_id, group_name, student_count), ...]"""
    async with aiosqlite.connect(DB) as db:
        async with db.execute("""
            SELECT g.id, g.name, COUNT(s.id)
            FROM groups g
            LEFT JOIN students s ON s.group_id=g.id AND s.is_active=1
            WHERE g.course_id=?
            GROUP BY g.id ORDER BY g.id
        """, (course_id,)) as c:
            return await c.fetchall()
