# -*- coding: utf-8 -*-
"""
ربات تلگرام عکاسی عروس - ثبت سفارش و نمایش پکیج‌ها
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

from config import BOT_TOKEN, ADMIN_CHAT_ID, PACKAGES
from database import init_db, save_order

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# مراحل مکالمه برای ثبت سفارش
ASK_NAME, ASK_PHONE, ASK_DATE, CONFIRM = range(4)


def get_package_by_id(package_id):
    for p in PACKAGES:
        if p["id"] == package_id:
            return p
    return None


def packages_keyboard():
    buttons = [
        [InlineKeyboardButton(f"{p['title']} - {p['price']}", callback_data=f"pkg_{p['id']}")]
        for p in PACKAGES
    ]
    return InlineKeyboardMarkup(buttons)


# ---------- دستورات اصلی ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "سلام! 🌸\n"
        "به ربات سفارش آلبوم و عکاسی عروس خوش اومدی.\n\n"
        "برای دیدن پکیج‌ها و ثبت سفارش روی /packages بزن.\n"
        "برای دیدن سفارش‌های ثبت‌شده‌ات روی /myorders بزن."
    )
    await update.message.reply_text(text)


async def show_packages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "یکی از پکیج‌های زیر رو انتخاب کن تا جزئیاتش رو ببینی:",
        reply_markup=packages_keyboard(),
    )


async def package_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    package_id = query.data.replace("pkg_", "")
    package = get_package_by_id(package_id)

    if not package:
        await query.edit_message_text("این پکیج پیدا نشد، لطفاً دوباره امتحان کن.")
        return

    context.user_data["selected_package"] = package

    text = (
        f"📦 *{package['title']}*\n"
        f"💰 قیمت: {package['price']}\n\n"
        f"{package['description']}\n\n"
        "اگه مایل به ثبت سفارش این پکیج هستی، دستور /order رو بزن."
    )
    await query.edit_message_text(text, parse_mode="Markdown")


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
    app.add_handler(CallbackQueryHandler(package_selected, pattern=r"^pkg_"))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("ربات در حال اجراست...")
    app.run_polling()


if __name__ == "__main__":
    main()
