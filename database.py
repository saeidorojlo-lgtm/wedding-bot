# -*- coding: utf-8 -*-
"""
مدیریت ساده‌ی دیتابیس سفارش‌ها با SQLite
نیازی به نصب دیتابیس جداگانه نیست، یک فایل ساده کنار پروژه ساخته میشه.
"""

import sqlite3
from datetime import datetime
from config import DB_PATH


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER,
            telegram_username TEXT,
            package_id TEXT,
            package_title TEXT,
            customer_name TEXT,
            customer_phone TEXT,
            wedding_date TEXT,
            created_at TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def save_order(telegram_user_id, telegram_username, package_id, package_title,
                customer_name, customer_phone, wedding_date):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO orders (
            telegram_user_id, telegram_username, package_id, package_title,
            customer_name, customer_phone, wedding_date, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            telegram_user_id,
            telegram_username,
            package_id,
            package_title,
            customer_name,
            customer_phone,
            wedding_date,
            datetime.now().isoformat(),
        ),
    )
    conn.commit()
    order_id = cur.lastrowid
    conn.close()
    return order_id


def get_all_orders():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows
