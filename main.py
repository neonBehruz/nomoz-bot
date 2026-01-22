import asyncio
import logging
import aiohttp
import datetime
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, CallbackQuery
from aiogram.client.session.aiohttp import AiohttpSession

# --- KONFIGURATSIYA ---
BOT_TOKEN = "8254265513:AAGaHSXqyKpuBo5fEwOL0dVONx_C0K3fiho"

# --- PROXY VA BOTNI SOZLASH ---
# os.name == 'nt' bo'lsa - bu Windows (PyCharm). Aks holda - PythonAnywhere (Linux).
if os.name != 'nt':
    proxy_url = "http://proxy.server:3128"
    session = AiohttpSession(proxy=proxy_url)
    bot = Bot(token="8254265513:AAFXEuFi6mrwb4I8yhD_rwGjQxaGe5wsk4M", session=session)
else:
    bot = Bot(token="8254265513:AAFXEuFi6mrwb4I8yhD_rwGjQxaGe5wsk4M")

dp = Dispatcher()

VILOYATLAR = {
    "Toshkent": "Tashkent", "Namangan": "Namangan", "Andijon": "Andijan",
    "Farg'ona": "Fergana", "Guliston": "Guliston", "Jizzax": "Jizzakh",
    "Samarqand": "Samarkand", "Qarshi": "Karshi", "Termiz": "Termez",
    "Buxoro": "Bukhara", "Navoiy": "Navoi", "Urganch": "Urgench", "Nukus": "Nukus"
}

# --- TUGMALAR ---
def get_main_keyboard():
    builder = ReplyKeyboardBuilder()
    for city in VILOYATLAR.keys():
        builder.add(types.KeyboardButton(text=city))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def get_day_inline_keyboard(city_name):
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Bugun", callback_data=f"day_0_{city_name}"))
    builder.add(InlineKeyboardButton(text="Ertaga", callback_data=f"day_1_{city_name}"))
    # O'chirish (Yopish) tugmasi qo'shildi
    builder.add(InlineKeyboardButton(text="❌ Yopish", callback_data="delete_msg"))
    builder.adjust(2, 1) # 2 ta tepada, 1 ta pastda
    return builder.as_markup()

# --- API BILAN ISHLASH ---
async def get_prayer_data(city_en: str, days_delta: int = 0):
    target_date = datetime.date.today() + datetime.timedelta(days=days_delta)
    date_str = target_date.strftime("%d-%m-%Y")

    api_url = f"https://api.aladhan.com/v1/timingsByAddress/{date_str}"
    params = {"address": f"{city_en}, Uzbekistan", "method": 3}

    async with aiohttp.ClientSession() as api_session:
        try:
            async with api_session.get(api_url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logging.error(f"API xatosi: {e}")
            return None

# --- MATNNI FORMATLASH ---
def format_prayer_text(data, city_name, user_name):
    t = data["data"]["timings"]
    d = data["data"]["date"]

    return (
        f"Hurmatli **{user_name}**, mana siz so'ragan vaqtlar:\n\n"
        f"📍 **{city_name}** shahri\n"
        f"📅 Sana: {d['readable']}\n"
        f"🌙 Hijriy: {d['hijri']['day']} {d['hijri']['month']['en']}\n"
        f"----------------------------\n"
        f"🌅 Bomdod:  **{t['Fajr']}**\n"
        f"☀️ Quyosh:  **{t['Sunrise']}**\n"
        f"🕛 Peshin:  **{t['Dhuhr']}**\n"
        f"🌇 Asr:     **{t['Asr']}**\n"
        f"🌆 Shom:    **{t['Maghrib']}**\n"
        f"🌙 Xufton:  **{t['Isha']}**\n"
        f"----------------------------\n"
        f"⚠️ *Vaqtlar 1-2 daqiqa farq qilishi mumkin.*"
    )

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        f"Assalomu alaykum **{message.from_user.first_name}**!\n\n"
        f"Namoz vaqtlarini bilish uchun viloyatingizni tanlang:",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(F.text.in_(VILOYATLAR.keys()))
async def city_chosen(message: types.Message):
    city_name = message.text
    city_en = VILOYATLAR[city_name]
    user_name = message.from_user.first_name

    data = await get_prayer_data(city_en, 0)
    if data:
        text = format_prayer_text(data, city_name, user_name)
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_day_inline_keyboard(city_name)
        )
    else:
        await message.answer("❌ Ma'lumot olishda xatolik yuz berdi.")

@dp.callback_query(F.data.startswith("day_"))
async def day_callback(callback: CallbackQuery):
    parts = callback.data.split("_")
    delta = int(parts[1])
    city_name = parts[2]
    city_en = VILOYATLAR[city_name]
    user_name = callback.from_user.first_name

    data = await get_prayer_data(city_en, delta)
    if data:
        text = format_prayer_text(data, city_name, user_name)
        try:
            await callback.message.edit_text(
                text,
                parse_mode="Markdown",
                reply_markup=get_day_inline_keyboard(city_name)
            )
        except Exception:
            pass
    await callback.answer()

# O'chirish tugmasi uchun maxsus handler
@dp.callback_query(F.data == "delete_msg")
async def delete_message_handler(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except Exception:
        await callback.answer("Xabarni o'chirib bo'lmadi")
    await callback.answer()

async def main():
    logging.basicConfig(level=logging.INFO)
    print("✅ Bot pollingni boshladi!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Kutilmagan xato: {e}")
        # Faylingizning eng oxirgi qismi shunday bo'lsin:

        from flask import Flask
        from threading import Thread

        app = Flask('')


        @app.route('/')
        def home():
            return "Bot 24/7 rejimida ishlamoqda!"


        def run():
            # Render uchun 10000-port muhim
            app.run(host='0.0.0.0', port=10000)


        def keep_alive():
            t = Thread(target=run)
            t.start()


        async def main():
            logging.basicConfig(level=logging.INFO)
            print("✅ Bot pollingni boshladi!")
            await dp.start_polling(bot)


        if __name__ == "__main__":
            keep_alive()  # Web-serverni yurgizadi
            try:
                asyncio.run(main())
            except Exception as e:
                logging.error(f"Xato yuz berdi: {e}")
