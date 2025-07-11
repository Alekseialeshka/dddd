import telebot
import random
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from telegram import Update
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext
from random import choice
from telegram.error import BadRequest
from telebot import types, TeleBot
from random import shuffle
from pyexpat.errors import messages
from telebot.types import Message
import time
import threading

API_TOKEN = '7905486303:AAH7VdvwWzp4eIeq3T30uXmPMDeLTSIlN5A'
bot = telebot.TeleBot('7905486303:AAH7VdvwWzp4eIeq3T30uXmPMDeLTSIlN5A')

ADMIN_ID = 5587077591  # ID администратора


# Функция для удаления сообщения через 5 секунд
def delete_message(chat_id, message_id):
    time.sleep(5)
    bot.delete_message(chat_id, message_id)


# Команда для бана пользователя
@bot.message_handler(commands=['ban'])
def ban_user(message):
    # Проверяем, что пользователь является администратором
    if message.from_user.id not in [admin.user.id for admin in bot.get_chat_administrators(message.chat.id)]:
        bot.reply_to(message, "У вас нет прав для бана пользователей.")
        return

    # Проверяем, что команда была использована с упоминанием пользователя
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
        try:
            bot.ban_chat_member(message.chat.id, user_id)
            ban_message = bot.reply_to(message,
                                       f"Пользователь {message.reply_to_message.from_user.first_name} был забанен.")

            # Запускаем поток для удаления сообщения через 5 секунд
            threading.Thread(target=delete_message, args=(message.chat.id, ban_message.message_id)).start()
        except Exception as e:
            bot.reply_to(message, f"Ошибка при бане пользователя: {str(e)}")
    else:
        bot.reply_to(message, "Пожалуйста, ответьте на сообщение пользователя, которого вы хотите забанить.")



# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

# Словарь для хранения статусов доступа пользователей
user_access = {}
# Словарь для хранения уведомлений о запрете
notification_sent = {}
# Словарь для хранения ID сообщений с вопросами
question_messages = {}

# Вопросы и правильные ответы (правильный ответ хранится отдельно)
questions = {
    'Сколько будет 2 + 2?': ('4', ['3', '5', '6']),
    'Какой цвет у неба?': ('Синий', ['Зелёный', 'Красный', 'Жёлтый']),
    'Сколько дней в неделе?': ('7', ['6', '5', '8'])
}

current_question = None


@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    for new_member in message.new_chat_members:
        welcome_msg = bot.send_message(message.chat.id,
                                       f'Добро пожаловать, {new_member.first_name}! Вы сейчас в режиме наблюдателя, чтобы писать что-то в этой группе, авторизуйтесь через нашего бота: @Tesssttbbot, (ЕСЛИ ВЫ ЭТО НЕ СДЕЛАЕТЕ, ВЫ НЕ СМОЖЕТЕ ПИСАТЬ В ЧАТ)')

        # Запускаем поток для удаления сообщения через 5 секунд
        threading.Thread(target=delete_welcome_message, args=(message.chat.id, welcome_msg.message_id)).start()

        # Устанавливаем статус доступа для нового участника
        user_access[new_member.id] = {'vhod': False}  # По умолчанию доступ запрещен
        notification_sent[new_member.id] = False  # Уведомление еще не отправлено

        # Удаляем возможность отправки сообщений
        bot.restrict_chat_member(message.chat.id, new_member.id, can_send_messages=False)

        # Запускаем вопрос для нового пользователя
        start_question(new_member.id, message.chat.id)  # Передаем ID группы


def delete_welcome_message(chat_id, message_id):
    time.sleep(20)  # Задержка на 5 секунд
    bot.delete_message(chat_id, message_id)  # Удаляем сообщение


def start_question(user_id, chat_id):
    global current_question
    question_text = choice(list(questions.keys()))
    correct_answer, wrong_answers = questions[question_text]  # Получаем правильный ответ и все неправильные варианты

    # Создаем список вариантов ответов, включая только один правильный ответ
    answers = wrong_answers + [correct_answer]
    shuffle(answers)  # Перемешиваем варианты ответов

    markup = types.InlineKeyboardMarkup()
    for answer in answers:
        markup.add(types.InlineKeyboardButton(answer, callback_data=answer))

    question_msg = bot.send_message(user_id, question_text, reply_markup=markup)  # Отправляем вопрос в личные сообщения
    question_messages[user_id] = (question_msg.message_id, correct_answer,
                                  chat_id)  # Сохраняем ID сообщения и правильный ответ


@bot.callback_query_handler(func=lambda call: True)
def handle_answer(call):
    user_id = call.from_user.id
    question_text = call.message.text
    correct_answer = question_messages[user_id][1]  # Получаем правильный ответ для текущего вопроса
    chat_id = question_messages[user_id][2]  # Получаем ID группы

    if call.data == correct_answer:
        bot.answer_callback_query(call.id, "Верно!")
        user_access[user_id]['vhod'] = True  # Разрешаем пользователю писать в чат
        bot.restrict_chat_member(chat_id, user_id, can_send_messages=True)  # Разрешаем отправку сообщений

        # Удаляем сообщение с вопросом
        if user_id in question_messages:
            bot.delete_message(user_id, question_messages[user_id][0])  # Удаляем вопрос из личных сообщений
            del question_messages[user_id]  # Удаляем ID сообщения из словаря

    else:
        bot.answer_callback_query(call.id, "Не верно! Вы будете удалены из группы.")
        # Удаляем пользователя из группы
        bot.kick_chat_member(chat_id, user_id)

        # Отправляем уведомление о том, что пользователь был исключён
        bot.send_message(chat_id,
                         f"Пользователь {call.from_user.first_name} был исключён из группы за неправильный ответ.")

        # Удаляем сообщение с вопросом
        if user_id in question_messages:
            bot.delete_message(user_id, question_messages[user_id][0])  # Удаляем вопрос из личных сообщений
            del question_messages[user_id]  # Удаляем ID сообщения из словаря
bot.polling(none_stop=True)
