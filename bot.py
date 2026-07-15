# -*- coding: utf-8 -*-
"""
ربات تلگرام عکاسی عروس - ثبت سفارش و نمایش پکیج‌ها (منوی مرحله‌ای)
کتابخانه: python-telegram-bot (نسخه ۲۰ به بالا)
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

from config import BOT_TOKEN, ADMIN_CHAT_ID, CATEGORIES
from database import init_db, save_order

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# مراحل مکالمه برای ثبت سفارش
ASK_NAME, ASK_PHONE, ASK_DATE, CONFIRM = range(4)


# ---------- ساخت کیبوردهای مرحله‌ای ----------

def main_categories_keyboard():
    buttons = [
        [InlineKeyboardButton(cat["title"], callback_data=f"cat|{key}")]
        for key, cat in CATEGORIES.items()
    ]
    return InlineKeyboardMarkup(buttons)


def pro_products_keyboard():
    products = CATEGORIES["pro"]["products"]
    buttons = [
        [InlineKeyboardButton(p["title"], callback_data=f"prod|{key}")]
        for key, p in products.items()
    ]
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="back|main")])
    return InlineKeyboardMarkup(buttons)


def pro_sizes_keyboard(product_key):
    sizes = CATEGORIES["pro"]["products"][product_key]["sizes"]
    buttons = [
        [InlineKeyboardButton(size, callback_data=f"size|{product_key}|{size}")]
        for size in sizes
    ]
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="cat|pro")])
    return InlineKeyboardMarkup(buttons)


def victory_items_keyboard():
    items = CATEGORIES["victory"]["items"]
    buttons = [
        [InlineKeyboardButton(item["title"], callback_data=f"victory|{key}")]
        for key, item in items.items()
    ]
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="back|main")])
    return InlineKeyboardMarkup(buttons)


def album_sizes_keyboard():
    sizes = CATEGORIES["album"]["sizes"]
    buttons = [
        [InlineKeyboardButton(size, callback_data=f"album|{size}")]
        for size in sizes
    ]
    buttons.append([InlineKeyboardButton("⬅️ بازگشت", callback_data="back|main")])
    return InlineKeyboardMarkup(buttons)


# ---------- دستورات اصلی ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "سلام! 🌸\n"
        "به ربات سفارش آلبوم و عکاسی عروس خوش اومدی.\n\n"
        "برای دیدن پکیج‌ها و ثبت سفارش روی /packages بزن."
    )
    await update.message.reply_text(text)


async def show_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "یکی از دسته‌های زیر رو انتخاب کن:",
        reply_markup=main_categories_keyboard(),
    )


# ---------- مسیریابی دکمه‌ها (Callback Query) ----------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # بازگشت به منوی اصلی
    if data == "back|main":
        await query.edit_message_text(
            "یکی از دسته‌های زیر رو انتخاب کن:",
            reply_markup=main_categories_keyboard(),
        )
        return

    parts = data.split("|")
    action = parts[0]

    # ---- انتخاب دسته اصلی ----
    if action == "cat":
        category_key = parts[1]

        if category_key == "pro":
            await query.edit_message_text(
                "یکی از این آلبوم‌ها رو انتخاب کن:",
                reply_markup=pro_products_keyboard(),
            )
        elif category_key == "victory":
            await query.edit_message_text(
                "یکی از محصولات Victory رو انتخاب کن:",
                reply_markup=victory_items_keyboard(),
            )
        elif category_key == "album":
            await query.edit_message_text(
                "سایز آلبوم مورد نظرت رو انتخاب کن:",
                reply_markup=album_sizes_keyboard(),
            )
        return

    # ---- انتخاب محصول در دسته PRO -> نمایش سایزها ----
    if action == "prod":
        product_key = parts[1]
        product = CATEGORIES["pro"]["products"][product_key]
        await query.edit_message_text(
            f"سایز مورد نظر برای «{product['title']}» رو انتخاب کن:",
            reply_markup=pro_sizes_keyboard(product_key),
        )
        return

    # ---- انتخاب نهایی سایز در PRO ----
    if action == "size":
        product_key, size = parts[1], parts[2]
        product = CATEGORIES["pro"]["products"][product_key]
        price = product["sizes"][size]

        package = {
            "id": f"pro_{product_key}_{size}",
            "title": f"{product['title']} ({size})",
            "price": price,
        }
        context.user_data["selected_package"] = package

        text = (
            f"📦 *{package['title']}*\n"
            f"💰 قیمت: {package['price']}\n\n"
            "اگه مایل به ثبت سفارش این پکیج هستی، دستور /order رو بزن."
        )
        await query.edit_message_text(text, parse_mode="Markdown")
        return

    # ---- انتخاب نهایی در Victory ----
    if action == "victory":
        item_key = parts[1]
        item = CATEGORIES["victory"]["items"][item_key]

        package = {
            "id": f"victory_{item_key}",
            "title": item["title"],
            "price": item["price"],
        }
        context.user_data["selected_package"] = package

        text = (
            f"📦 *{package['title']}*\n"
            f"💰 قیمت: {package['price']}\n\n"
            "اگه مایل به ثبت سفارش این پکیج هستی، دستور /order رو بزن."
        )
        await query.edit_message_text(text, parse_mode="Markdown")
        return

    # ---- انتخاب نهایی سایز آلبوم ----
    if action == "album":
        size = parts[1]
        price = CATEGORIES["album"]["sizes"][size]

        package = {
            "id": f"album_{size}",
            "title": f"آلبوم سایز {size}",
            "price": price,
        }
        context.user_data["selected_package"] = package

        text = (
            f"📦 *{package['title']}*\n"
            f"💰 قیمت: {package['price']}\n\n"
            "اگه مایل به ثبت سفارش این پکیج هستی، دستور /order رو بزن."
        )
        await query.edit_message_text(text, parse_mode="Markdown")
        return


# ---------- مکالمه ثبت سفارش ----------

async def order_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    package = context.user_data.get("selected_package")
    if not package:
        await update.message.reply_text(
            "اول یه پکیج انتخاب کن. با /packages می‌تونی پکیج‌ها رو ببینی."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"عالیه، در حال ثبت سفارش برای «{package['title']}» هستیم.\n\n"
        "لطفاً اسم و فامیل خودتون رو بفرستید:",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ASK_NAME


async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["customer_name"] = update.message.text.strip()
    await update.message.reply_text("شماره تماس خودتون رو وارد کنید:")
    return ASK_PHONE


async def ask_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["customer_phone"] = update.message.text.strip()
    await update.message.reply_text("تاریخ مراسم عروسی رو وارد کنید (مثلاً ۱۴۰۴/۰۵/۲۰):")
    return ASK_DATE


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["wedding_date"] = update.message.text.strip()
    package = context.user_data["selected_package"]

    summary = (
        "لطفاً اطلاعات زیر رو بررسی کن:\n\n"
        f"📦 پکیج: {package['title']} ({package['price']})\n"
        f"👤 نام: {context.user_data['customer_name']}\n"
        f"📞 تماس: {context.user_data['customer_phone']}\n"
        f"📅 تاریخ مراسم: {context.user_data['wedding_date']}\n\n"
        "اگه همه چیز درسته، بنویس «تایید» تا سفارش ثبت بشه.\n"
        "برای لغو، بنویس «لغو»."
    )
    await update.message.reply_text(summary)
    return CONFIRM


async def save_and_finish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text != "تایید":
        await update.message.reply_text("سفارش لغو شد. هر وقت خواستی می‌تونی دوباره با /packages شروع کنی.")
        context.user_data.clear()
        return ConversationHandler.END

    package = context.user_data["selected_package"]
    user = update.effective_user

    order_id = save_order(
        telegram_user_id=user.id,
        telegram_username=user.username or "",
        package_id=package["id"],
        package_title=package["title"],
        customer_name=context.user_data["customer_name"],
        customer_phone=context.user_data["customer_phone"],
        wedding_date=context.user_data["wedding_date"],
    )

    await update.message.reply_text(
        f"✅ سفارش شما با شماره #{order_id} ثبت شد.\n"
        "به زودی برای هماهنگی بیشتر باهاتون تماس می‌گیریم. ممنون از اعتمادتون 🌷"
    )

    # اطلاع‌رسانی به ادمین
    if ADMIN_CHAT_ID:
        admin_text = (
            "🔔 سفارش جدید ثبت شد!\n\n"
            f"شماره سفارش: #{order_id}\n"
            f"پکیج: {package['title']} ({package['price']})\n"
            f"نام مشتری: {context.user_data['customer_name']}\n"
            f"شماره تماس: {context.user_data['customer_phone']}\n"
            f"تاریخ مراسم: {context.user_data['wedding_date']}\n"
            f"یوزرنیم تلگرام: @{user.username if user.username else 'ندارد'}"
        )
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_text)

    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("عملیات لغو شد.")
    context.user_data.clear()
    return ConversationHandler.END


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "متوجه نشدم 🙂 از /packages برای دیدن پکیج‌ها و /order برای ثبت سفارش استفاده کن."
    )


def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("order", order_start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            ASK_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_date)],
            ASK_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_order)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_and_finish)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("packages", show_packages))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("ربات در حال اجراست...")
    app.run_polling()


if __name__ == "__main__":
    main()
