import os
import json
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.utils import executor
from aiogram.dispatcher.filters import BoundFilter
from aiogram.contrib.middlewares.logging import LoggingMiddleware
import firebase_admin
from firebase_admin import credentials, db

# Firebase setup
cred = credentials.Certificate("durexbot-a9666-firebase-adminsdk-fbsvc-dce5ab7395.json")
firebase_admin.initialize_app(cred, {
    "databaseURL": "https://durexbot-a9666-default-rtdb.firebaseio.com/"
})

TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Firebase DB reference
root_ref = db.reference("/")
admins_ref = root_ref.child("admins")
warns_ref = root_ref.child("warns")

# Admin filter
class AdminLevelFilter(BoundFilter):
    key = "admin_level"

    def __init__(self, admin_level):
        self.admin_level = admin_level

    async def check(self, message: Message):
        user_id = str(message.from_user.id)
        return admins_ref.child(user_id).get() or 0 >= self.admin_level

dp.filters_factory.bind(AdminLevelFilter)

@dp.message_handler(commands=["start"])
async def start_cmd(message: Message):
    await message.reply("🔥 Firebase-негізіндегі модерация бот іске қосылды.")

@dp.message_handler(commands=["повысить"])
async def promote_admin(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    if not message.reply_to_message:
        return await message.reply("Кімді көтеру керектігін жауаппен көрсет.")
    uid = str(message.reply_to_message.from_user.id)
    lvl = admins_ref.child(uid).get() or 0
    if lvl < 3:
        admins_ref.child(uid).set(lvl + 1)
        await message.reply(f"✅ @{message.reply_to_message.from_user.username} {lvl + 1}-деңгейге көтерілді.")
    else:
        await message.reply("⛔️ Бұл админ ең жоғары деңгейде.")

@dp.message_handler(commands=["снять"])
async def demote_admin(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    if not message.reply_to_message:
        return await message.reply("Кімді төмендету керектігін жауаппен көрсет.")
    uid = str(message.reply_to_message.from_user.id)
    if admins_ref.child(uid).get():
        admins_ref.child(uid).delete()
        await message.reply("🗑️ Админ рөлі алынды.")
    else:
        await message.reply("⛔️ Бұл адам админ емес.")

@dp.message_handler(admin_level=1, commands=["мут"])
async def mute_user(message: Message):
    if not message.reply_to_message:
        return await message.reply("Мут беру үшін жауаппен көрсет.")
    reason = message.get_args() or "ештеңе"
    target = message.reply_to_message.from_user
    await message.bot.restrict_chat_member(
        message.chat.id,
        target.id,
        types.ChatPermissions(can_send_messages=False),
        until_date=1800
    )
    await message.reply(f"{target.full_name} муть алды!
⏰ 30 минут
📄 Себебі: {reason}")
    await bot.send_message(OWNER_ID, f"👮‍♂️ @{message.from_user.username} мут берді @{target.username}
🕒 30 минут
📄 Себебі: {reason}")

@dp.message_handler(admin_level=2, commands=["пред"])
async def warn_user(message: Message):
    if not message.reply_to_message:
        return await message.reply("Ескерту беру үшін жауаппен көрсет.")
    uid = str(message.reply_to_message.from_user.id)
    warns = warns_ref.child(uid).get() or 0
    warns += 1
    warns_ref.child(uid).set(warns)
    await message.reply(f"⚠️ Ескерту берілді! Жалпы: {warns}")
    await bot.send_message(OWNER_ID, f"⚠️ @{message.from_user.username} @{message.reply_to_message.from_user.username}-ге пред берді. Жалпы: {warns}")
    if warns >= 3:
        await message.bot.kick_chat_member(message.chat.id, int(uid))
        await message.reply("❌ 3 пред алды. БАН берілді!")
        await bot.send_message(OWNER_ID, f"🚫 @{message.reply_to_message.from_user.username} бан алды (3 пред)")

@dp.message_handler(admin_level=3, commands=["бан"])
async def ban_user(message: Message):
    if not message.reply_to_message:
        return await message.reply("Бан үшін жауаппен көрсет.")
    target = message.reply_to_message.from_user
    await message.bot.kick_chat_member(message.chat.id, target.id)
    await message.reply(f"{target.full_name} бан алды!")
    await bot.send_message(OWNER_ID, f"🚫 @{message.from_user.username} @{target.username}-ге бан берді.")

@dp.message_handler()
async def detect_word(message: Message):
    if "калл" in message.text.lower():
        link = f"https://t.me/c/{str(message.chat.id)[4:]}/{message.message_id}"
        await bot.send_message(OWNER_ID, f"🚨 @{message.from_user.username} 'кал' деп жазды!
🔗 [Хабарламаға өту]({link})", parse_mode="Markdown")

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
