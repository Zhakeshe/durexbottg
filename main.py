import telebot
import yt_dlp
import os
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '7597316965:AAH9lwDoj9OtOuFdNFD54IaIMH0AtMigFqw'  # ← Мына жерге BotFather берген токенді қой

bot = telebot.TeleBot(TOKEN)

search_results = {}  # user_id → list of results

@bot.message_handler(func=lambda message: message.text.lower().startswith("муз "))
def handle_music_search(message):
    query = message.text[4:].strip()
    user_id = message.from_user.id
    msg = bot.reply_to(message, f"🔍 Іздеуде: `{query}`...", parse_mode="Markdown")

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        search = f"ytsearch5:{query}"
        try:
            info = ydl.extract_info(search, download=False)['entries']
        except Exception as e:
            bot.edit_message_text("❌ Іздеу кезінде қате шықты.", message.chat.id, msg.message_id)
            return

    if not info:
        bot.edit_message_text("⚠️ Нәтиже табылмады.", message.chat.id, msg.message_id)
        return

    markup = InlineKeyboardMarkup()
    search_results[user_id] = info

    for i, entry in enumerate(info):
        btn_text = f"{i+1}. {entry['title'][:40]}"
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"pick_{i}"))

    bot.edit_message_text("🎧 Таңдаңыз:", message.chat.id, msg.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("pick_"))
def handle_choice(call):
    user_id = call.from_user.id
    index = int(call.data.split("_")[1])

    if user_id not in search_results:
        bot.answer_callback_query(call.id, "Қате: нәтижелер табылмады.")
        return

    entry = search_results[user_id][index]
    url = entry['webpage_url']
    title = entry['title']

    msg = bot.send_message(call.message.chat.id, f"⬇️ Жүктелуде: *{title}*", parse_mode="Markdown")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f"{user_id}_music.%(ext)s",
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        bot.edit_message_text("❌ Жүктеу кезінде қате шықты.", call.message.chat.id, msg.message_id)
        return

    file_path = f"{user_id}_music.mp3"
    with open(file_path, 'rb') as audio:
        bot.send_audio(call.message.chat.id, audio, title=title)

    os.remove(file_path)
    bot.delete_message(call.message.chat.id, msg.message_id)


bot.polling(non_stop=True)
