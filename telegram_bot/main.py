import os
import telebot

from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

token = os.environ.get("TELEGRAM_TOKEN")
url = os.environ.get("FRONT_URL")
bot = telebot.TeleBot(token)

@bot.message_handler(commands=['start'])
def start(message):
    keyboard = InlineKeyboardMarkup()

    web_app_info = WebAppInfo(url=url)
    button = InlineKeyboardButton("Play Mapster!", web_app=web_app_info)

    keyboard.add(button)
    bot.send_message(message.chat.id, "Click to open Mapster", reply_markup=keyboard)

bot.polling()
