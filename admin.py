from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_IDS
import database as db
from keyboards import (
    main_menu, courses_kb, del_courses_kb,
    groups_kb, del_groups_kb,
    students_kb, student_detail_kb,
    confirm_kb, stats_courses_kb, back
)

router = Router()


def adm(uid: int) -> bool:
    return uid in ADMIN_IDS


# ── FSM ──────────────────────────────────────────────────────

class AddCourse(StatesGroup):
    name = State()

class AddGroup(StatesGroup):
    name = State()
    course_id = State()

class AddStudent(StatesGroup):
    first_name = State()
    last_name  = State()
    age        = State()
    phone      = State()
    username   = State()
    group_id   = State()
    course_id  = State()

class Search(StatesGroup):
    query = State()


# ── START ────────────────────────────────────────────────────

@router.message(Command("start"))
async def cmd_start(msg: Message):
    if not adm(msg.from_user.id):
        return  # oddiy user — jim

    await msg.answer(
        f"👋 Xush kelibsiz, ADMIN: <b> {msg.from_user.full_name}!</b>\n🏫 <b>TURKON TECH O'QUV MARKAZI MALUMOTLAR BAZASI</b>",
        parse_mode="HTML",
        reply_markup=main_menu()
    )


# ── COURSES ──────────────────────────────────────────────────

async def send_courses(target, edit=False):
    courses = await db.get_courses()
    text = f"📚 <b>Kurslar</b> ({len(courses)} ta):"
    kb   = courses_kb(courses)
    if edit:
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.message(F.text == "📚 Kurslar")
async def courses_btn(msg: Message):
    if not adm(msg.from_user.id): return
    await send_courses(msg)


@router.callback_query(F.data == "courses")
async def courses_cb(cb: CallbackQuery):
    if not adm(cb.from_user.id): return await cb.answer()
    await send_courses(cb, edit=True)
    await cb.answer()


# Kurs qo'shish
@router.callback_query(F.data == "add_course")
async def add_course_cb(cb: CallbackQuery, state: FSMContext):
    if not adm(cb.from_user.id): return await cb.answer()
    await state.set_state(AddCourse.name)
    await cb.message.answer("✏️ Yangi kurs nomini kiriting:")
    await cb.answer()

@router.message(AddCourse.name)
async def save_course(msg: Message, state: FSMContext):
    if not adm(msg.from_user.id): return
    await db.add_course(msg.text.strip())
    await state.clear()
    courses = await db.get_courses()
    await msg.answer(f"✅ <b>{msg.text.strip()}</b> kursi qo'shildi!", parse_mode="HTML",
                     reply_markup=courses_kb(courses))


# Kurs o'chirish
@router.callback_query(F.data == "del_course")
async def del_course_list(cb: CallbackQuery):
    if not adm(cb.from_user.id): return await cb.answer()
    courses = await db.get_courses()
    await cb.message.edit_text("🗑 Qaysi kursni o'chirmoqchisiz?",
                                reply_markup=del_courses_kb(courses))
    await cb.answer()

@router.callback_query(F.data.startswith("dc:"))
async def del_course_confirm(cb: CallbackQuery):
    if not adm(cb.from_user.id): return await cb.answer()
    cid = int(cb.data.split(":")[1])
    course = await db.get_course(cid)
    await cb.message.edit_text(
        f"⚠️ <b>{course[1]}</b> kursini o'chirasizmi?\n(Barcha guruh va o'quvchilar ham o'chadi)",
        parse_mode="HTML",
        reply_markup=confirm_kb(f"yes_dc:{cid}", "courses")
    )
    await cb.answer()

@router.callback_query(F.data.startswith("yes_dc:"))
async def del_course_yes(cb: CallbackQuery):
    if not adm(cb.from_user.id): return await cb.answer()
    cid = int(cb.data.split(":")[1])
    await db.delete_course(cid)
    await send_courses(cb, edit=True)
    await cb.answer("✅ O'chirildi!")


# ── GROUPS ───────────────────────────────────────────────────

async def send_groups(target, course_id: int, edit=False):
    course  = await db.get_course(course_id)
    groups  = await db.get_groups(course_id)
    total   = sum([await db.count_students(g[0]) for g in groups])
    text = (
        f"📖 <b>{course[1]}</b>\n\n"
        f"👥 Guruhlar: <b>{len(groups)}</b>\n"
        f"🎓 Jami o'quvchilar: <b>{total}</b>"
    )
    kb = groups_kb(groups, course_id)
    if edit:
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("c:"))
async def course_cb(cb: CallbackQuery):
    if not adm(cb.from_user.id): return await cb.answer()
    cid = int(cb.data.split(":")[1])
    await send_groups(cb, cid, edit=True)
    await cb.answer()


# Guruh qo'shish
@router.callback_query(F.data.startswith("add_group:"))
async def add_group_cb(cb: CallbackQuery, state: FSMContext):
    if not adm(cb.from_user.id): return await cb.answer()
    cid = int(cb.data.split(":")[1])
    await state.set_state(AddGroup.name)
    await state.update_data(course_id=cid)
    await cb.message.answer("✏️ Guruh nomini kiriting (masalan: Guruh-1):")
    await cb.answer()

@router.message(AddGroup.name)
async def save_group(msg: Message, state: FSMContext):
    if not adm(msg.from_user.id): return
    data = await state.get_data()
    cid  = data["course_id"]
    await db.add_group(cid, msg.text.strip())
    await state.clear()
    groups = await db.get_groups(cid)
    course = await db.get_course(cid)
    await msg.answer(f"✅ <b>{msg.text.strip()}</b> guruhi qo'shildi!",
                     parse_mode="HTML", reply_markup=groups_kb(groups, cid))


# Guruh o'chirish
@router.callback_query(F.data.startswith("del_group:"))
async def del_group_list(cb: CallbackQuery):
    if not adm(cb.from_user.id): return await cb.answer()
    cid    = int(cb.data.split(":")[1])
    groups = await db.get_groups(cid)
    if not groups:
        await cb.answer("Guruhlar yo'q!", show_alert=True); return
    await cb.message.edit_text("🗑 Qaysi guruhni o'chirmoqchisiz?",
                                reply_markup=del_groups_kb(groups, cid))
    await cb.answer()

@router.callback_query(F.data.startswith("dg:"))
async def del_group_confirm(cb: CallbackQuery):
    if not adm(cb.from_user.id): return await cb.answer()
    _, gid, cid = cb.data.split(":")
    group = await db.get_group(int(gid))
    await cb.message.edit_text(
        f"⚠️ <b>{group[2]}</b> guruhini o'chirasizmi?\n(Guruh o'quvchilari ham o'chadi)",
        parse_mode="HTML",
        reply_markup=confirm_kb(f"yes_dg:{gid}:{cid}", f"c:{cid}")
    )
    await cb.answer()

@router.callback_query(F.data.startswith("yes_dg:"))
async def del_group_yes(cb: CallbackQuery):
    if not adm(cb.from_user.id): return await cb.answer()
    _, gid, cid = cb.data.split(":")
    await db.delete_group(int(gid))
    await send_groups(cb, int(cid), edit=True)
    await cb.answer("✅ O'chirildi!")


# ── STUDENTS ─────────────────────────────────────────────────

async def send_students(target, group_id: int, edit=False):
    group    = await db.get_group(group_id)
    course_id = group[1]
    students = await db.get_students(group_id)
    text = f"👥 <b>{group[2]}</b> — o'quvchilar ({len(students)} kishi):"
    kb   = students_kb(students, group_id, course_id)
    if edit:
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        await target.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("g:"))
async def group_cb(cb: CallbackQuery):
    if not adm(cb.from_user.id): return await cb.answer()
    gid = int(cb.data.split(":")[1])
    await send_students(cb, gid, edit=True)
    await cb.answer()


# O'quvchi qo'shish
@router.callback_query(F.data.startswith("add_student:"))
async def add_student_cb(cb: CallbackQuery, state: FSMContext):
    if not adm(cb.from_user.id): return await cb.answer()
    gid = int(cb.data.split(":")[1])
    group = await db.get_group(gid)
    await state.set_state(AddStudent.first_name)
    await state.update_data(group_id=gid, course_id=group[1])
    await cb.message.answer("1️⃣ O'quvchining <b>ismini</b> kiriting:", parse_mode="HTML")
    await cb.answer()

@router.message(AddStudent.first_name)
async def student_first_name(msg: Message, state: FSMContext):
    if not adm(msg.from_user.id): return
    await state.update_data(first_name=msg.text.strip())
    await state.set_state(AddStudent.last_name)
    await msg.answer("2️⃣ O'quvchining <b>familiyasini</b> kiriting:", parse_mode="HTML")

@router.message(AddStudent.last_name)
async def student_last_name(msg: Message, state: FSMContext):
    if not adm(msg.from_user.id): return
    await state.update_data(last_name=msg.text.strip())
    await state.set_state(AddStudent.age)
    await msg.answer("3️⃣ <b>Yoshini</b> kiriting (raqamda):", parse_mode="HTML")

@router.message(AddStudent.age)
async def student_age(msg: Message, state: FSMContext):
    if not adm(msg.from_user.id): return
    if not msg.text.strip().isdigit():
        await msg.answer("❌ Faqat raqam kiriting:"); return
    await state.update_data(age=int(msg.text.strip()))
    await state.set_state(AddStudent.phone)
    await msg.answer("4️⃣ <b>Telefon raqamini</b> kiriting (+998901234567):", parse_mode="HTML")

@router.message(AddStudent.phone)
async def student_phone(msg: Message, state: FSMContext):
    if not adm(msg.from_user.id): return
    await state.update_data(phone=msg.text.strip())
    await state.set_state(AddStudent.username)
    await msg.answer(
        "5️⃣ <b>Telegram username</b> kiriting (@username).\n"
        "Yo'q bo'lsa — <b>yo'q</b> deb yozing:",
        parse_mode="HTML"
    )

@router.message(AddStudent.username)
async def student_username(msg: Message, state: FSMContext):
    if not adm(msg.from_user.id): return
    raw = msg.text.strip()
    username = None if raw.lower() in ["yo'q", "yoq", "-", "none", "no", "yok"] else raw
    await state.update_data(username=username)

    d = await state.get_data()
    await state.clear()

    await db.add_student(
        d["group_id"], d["first_name"], d["last_name"],
        d["age"], d["phone"], d["username"] if "username" in d else username
    )

    # yangi qo'shilgan o'quvchi ID sini olish uchun qayta qidiramiz
    students = await db.get_students(d["group_id"])
    new_st   = students[-1]  # eng oxirgi

    uname = f"@{username}" if username else "Username yo'q"
    await msg.answer(
        f"✅ <b>O'quvchi qo'shildi!</b>\n\n"
        f"🆔 ID: <b>#{new_st[0]}</b>\n"
        f"👤 Ism: <b>{d['first_name']}</b>\n"
        f"👤 Familiya: <b>{d['last_name']}</b>\n"
        f"🎂 Yoshi: <b>{d['age']}</b>\n"
        f"📞 Tel: <b>{d['phone']}</b>\n"
        f"📱 Username: <b>{uname}</b>",
        parse_mode="HTML",
        reply_markup=students_kb(students, d["group_id"], d["course_id"])
    )


# O'quvchi detali
@router.callback_query(F.data.startswith("s:"))
async def student_cb(cb: CallbackQuery):
    if not adm(cb.from_user.id): return await cb.answer()
    sid = int(cb.data.split(":")[1])
    st  = await db.get_student(sid)
    if not st:
        await cb.answer("Topilmadi!", show_alert=True); return

    sid2, gid, fn, ln, age, phone, uname, active = st
    group  = await db.get_group(gid)
    course = await db.get_course(group[1])
    uname_show = f"@{uname}" if uname else "Username yo'q"

    await cb.message.edit_text(
        f"🎓 <b>O'quvchi ma'lumoti</b>\n\n"
        f"🆔 ID: <b>#{sid2}</b>\n"
        f"👤 Ismi: <b>{fn}</b>\n"
        f"👤 Familiyasi: <b>{ln}</b>\n"
        f"🎂 Yoshi: <b>{age}</b>\n"
        f"📞 Telefon: <b>{phone}</b>\n"
        f"📱 Username: <b>{uname_show}</b>\n"
        f"📖 Kursi: <b>{course[1]}</b>\n"
        f"👥 Guruhi: <b>{group[2]}</b>",
        parse_mode="HTML",
        reply_markup=student_detail_kb(sid2, gid, group[1])
    )
    await cb.answer()


# O'quvchini chiqarish
@router.callback_query(F.data.startswith("remove:"))
async def remove_confirm(cb: CallbackQuery):
    if not adm(cb.from_user.id): return await cb.answer()
    _, sid, gid, cid = cb.data.split(":")
    st = await db.get_student(int(sid))
    await cb.message.edit_text(
        f"⚠️ <b>{st[2]} {st[3]}</b> ni kursdan chiqarasizmi?",
        parse_mode="HTML",
        reply_markup=confirm_kb(f"yes_rm:{sid}:{gid}:{cid}", f"s:{sid}")
    )
    await cb.answer()

@router.callback_query(F.data.startswith("yes_rm:"))
async def remove_yes(cb: CallbackQuery):
    if not adm(cb.from_user.id): return await cb.answer()
    _, sid, gid, cid = cb.data.split(":")
    await db.remove_student(int(sid))
    await send_students(cb, int(gid), edit=True)
    await cb.answer("✅ Chiqarildi!")


# ── STATISTIKA ───────────────────────────────────────────────

@router.message(F.text == "📊 Statistika")
async def stats_btn(msg: Message):
    if not adm(msg.from_user.id): return
    courses = await db.get_courses()
    if not courses:
        await msg.answer("Kurslar yo'q."); return
    await msg.answer("📊 <b>Statistika — kursni tanlang:</b>",
                     parse_mode="HTML", reply_markup=stats_courses_kb(courses))

@router.callback_query(F.data.startswith("stat:"))
async def stats_course(cb: CallbackQuery):
    if not adm(cb.from_user.id): return await cb.answer()
    cid    = int(cb.data.split(":")[1])
    course = await db.get_course(cid)
    stats  = await db.course_stats(cid)
    total  = sum(r[2] for r in stats)

    lines = [f"📊 <b>{course[1]}</b>\n",
             f"👥 Guruhlar soni: <b>{len(stats)}</b>",
             f"🎓 Jami o'quvchilar: <b>{total}</b>\n"]
    for _, gname, cnt in stats:
        lines.append(f"  📁 {gname}: <b>{cnt}</b> o'quvchi")

    courses = await db.get_courses()
    await cb.message.edit_text("\n".join(lines), parse_mode="HTML",
                                reply_markup=stats_courses_kb(courses))
    await cb.answer()


# ── QIDIRISH ─────────────────────────────────────────────────

@router.message(F.text == "🔍 ID bo'yicha qidirish")
async def search_id_btn(msg: Message, state: FSMContext):
    if not adm(msg.from_user.id): return
    await state.set_state(Search.query)
    await state.update_data(mode="id")
    await msg.answer("🔍 O'quvchi <b>ID raqamini</b> kiriting:", parse_mode="HTML")

@router.message(F.text == "🔎 Ism bo'yicha qidirish")
async def search_name_btn(msg: Message, state: FSMContext):
    if not adm(msg.from_user.id): return
    await state.set_state(Search.query)
    await state.update_data(mode="name")
    await msg.answer("🔎 O'quvchi <b>ism yoki familiyasini</b> kiriting:", parse_mode="HTML")

@router.message(Search.query)
async def do_search(msg: Message, state: FSMContext):
    if not adm(msg.from_user.id): return
    data = await state.get_data()
    mode = data.get("mode", "name")
    await state.clear()

    if mode == "id":
        if not msg.text.strip().isdigit():
            await msg.answer("❌ ID raqam bo'lishi kerak!", reply_markup=main_menu()); return
        st = await db.search_by_id(int(msg.text.strip()))
        if not st:
            await msg.answer("❌ Bunday ID li o'quvchi topilmadi.", reply_markup=main_menu()); return
        sid, gid, fn, ln, age, phone, uname, active = st
        group  = await db.get_group(gid)
        course = await db.get_course(group[1])
        uname_show = f"@{uname}" if uname else "Username yo'q"
        status = "✅ Faol" if active else "🚫 Chiqarilgan"
        await msg.answer(
            f"🎓 <b>O'quvchi topildi!</b>\n\n"
            f"🆔 ID: <b>#{sid}</b>\n"
            f"👤 Ismi: <b>{fn}</b>\n"
            f"👤 Familiyasi: <b>{ln}</b>\n"
            f"🎂 Yoshi: <b>{age}</b>\n"
            f"📞 Telefon: <b>{phone}</b>\n"
            f"📱 Username: <b>{uname_show}</b>\n"
            f"📖 Kursi: <b>{course[1]}</b>\n"
            f"👥 Guruhi: <b>{group[2]}</b>\n"
            f"📌 Holati: {status}",
            parse_mode="HTML", reply_markup=main_menu()
        )
    else:
        results = await db.search_by_name(msg.text.strip())
        if not results:
            await msg.answer("❌ Topilmadi.", reply_markup=main_menu()); return
        lines = [f"🔎 <b>Natijalar ({len(results)} ta):</b>\n"]
        for sid, fn, ln, age, phone, uname in results:
            uname_show = f"@{uname}" if uname else "yo'q"
            lines.append(f"🆔 #{sid} | <b>{fn} {ln}</b> | {age} yosh | {phone} | {uname_show}")
        await msg.answer("\n".join(lines), parse_mode="HTML", reply_markup=main_menu())
