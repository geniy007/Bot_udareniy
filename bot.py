import telebot
from telebot import types
import requests
import json
import os
import redis

token = os.environ["TELEGRAM_TOKEN"]

bot = telebot.TeleBot(token)
api_url = 'https://stepik.akentev.com/api/stress'

redis_url = os.environ.get('REDIS_URL')
if redis_url is None:
    try:
        user_data = json.load(open('user_data.json', 'r', encoding='utf-8'))
    except FileNotFoundError:
        user_data = {
            'states': {},
            'current_question': {},
            'first_symbol': {},
            'win': {},
            'lose': {}
        }
else:
    redis_db = redis.from_url(redis_url)
    raw_data = redis_db.get('user_data')
    if raw_data is None:
        user_data = {
            'states': {},
            'current_question': {},
            'first_symbol': {},
            'win': {},
            'lose': {}
        }
    else:
        user_data = json.loads(raw_data)


def change_data(key, user_id, value):
    user_data[key][user_id] = value
    if redis_url is None:
        json.dump(
            user_data,
            open('user_data.json', 'w', encoding='utf-8'),
            indent=2,
            ensure_ascii=False
        )
    else:
        redis_db1 = redis.from_url(redis_url)
        redis_db1.set('user_data', json.dumps(user_data))


MAIN_STATE = 'main'
ANSWER_STATE = 'answer_handler'
FIRST_SYMBOL_STATE = 'first_symbol_handler'

markup = types.ReplyKeyboardMarkup(resize_keyboard=True,
                                   one_time_keyboard=False)
markup.add(
    *[types.KeyboardButton(button) for button in
      ['Спроси меня слово', 'Первая буква',
       'Покажи счет', 'Сбросить счет', 'Привет', 'Что мне делать?']]
)

markup1 = types.ReplyKeyboardMarkup(resize_keyboard=True,
                                    one_time_keyboard=True)
markup1.add(
    *[types.KeyboardButton(button) for button in
      ['а', 'б', 'в', 'г', 'д', 'е', 'ж', 'з', 'и',
       'к', 'л', 'м', 'н', 'о', 'п', 'р', 'с', 'т', 'у',
       'ф', 'х', 'ц', 'ч', 'ш', 'щ', 'э', 'Сброс', 'Что мне делать?']]
)


@bot.message_handler(func=lambda message: user_data['states']
                     .get(str(message.from_user.id),
                          MAIN_STATE) == MAIN_STATE)
def main_handler(message):
    user_id = str(message.from_user.id)
    if user_id not in user_data['win']:
        user_data['win'][user_id] = 0
    if user_id not in user_data['lose']:
        user_data['lose'][user_id] = 0
    if user_id not in user_data['states']:
        user_data['states'][user_id] = 'main'
    if user_id not in user_data['first_symbol']:
        user_data['first_symbol'][user_id] = {'first_letter': ''}
    if user_id not in user_data['current_question']:
        user_data['current_question'][user_id] = ''

    if message.text == '/start':
        bot.send_message(user_id, 'Это бот-тренажер ударений: он поможет '
                                  'научиться правильной постановке ударений '
                                  'в сложных словах', reply_markup=markup
                         )

    elif 'привет' in message.text.lower():
        bot.send_message(user_id, 'Ну привет, ' +
                         message.from_user.first_name + '!')

    elif 'первая буква' in message.text.lower():
        bot.send_message(user_id, 'Введите первую букву или введите '
                                  '"сброс" для сброса первой буквы',
                         reply_markup=markup1)
        change_data('states', user_id, FIRST_SYMBOL_STATE)

    elif 'спроси меня слово' in message.text.lower():
        user_data['current_question'][user_id] = \
            requests.get(api_url, params=user_data['first_symbol'][user_id]
                         ).json()['word']
        bot.send_message(user_id, 'Выдели большой буквой правильное '
                                  'ударение в слове: ' +
                         user_data['current_question'][user_id].lower())
        change_data('states', user_id, ANSWER_STATE)

    elif 'покажи счет' in message.text.lower() or 'покажи счёт' in \
            message.text.lower():
        bot.send_message(user_id, 'Побед: ' +
                         str(user_data['win'][user_id]) +
                         '\nПоражений: ' + str(user_data['lose'][user_id]))

    elif 'сбросить счет' in message.text.lower():
        user_data['win'][user_id] = 0
        user_data['lose'][user_id] = 0
        bot.send_message(user_id, 'Счетчик побед и поражений сброшен.')
        change_data('states', user_id, MAIN_STATE)

    elif 'что мне делать?' in message.text.lower():
        bot.send_message(user_id, 'Ты в главном меню')

    else:
        bot.send_message(user_id, 'Я тебя не понял')


@bot.message_handler(func=lambda message: user_data['states']
                     .get(str(message.from_user.id),
                          MAIN_STATE) == ANSWER_STATE)
def answer_handler(message):
    user_id = str(message.from_user.id)
    if message.text == user_data['current_question'][user_id]:
        bot.send_message(user_id, 'Правильно!')
        user_data['win'][user_id] += 1
        change_data('states', user_id, MAIN_STATE)
    elif 'что мне делать?' in message.text.lower():
        bot.send_message(user_id, 'Тебе надо поставить удерение в слове ' +
                         user_data['current_question'][user_id].lower())
    elif message.text != user_data['current_question'][user_id] and \
            message.text.lower() == \
            user_data['current_question'][user_id].lower():
        bot.send_message(user_id, 'Неправильно :(\nПравильный ответ:  ' +
                         user_data['current_question'][user_id])
        user_data['lose'][user_id] += 1
        change_data('states', user_id, MAIN_STATE)
    else:
        bot.send_message(user_id, 'Я тебя не понял')


@bot.message_handler(func=lambda message: user_data['states']
                     .get(str(message.from_user.id),
                          MAIN_STATE) == FIRST_SYMBOL_STATE)
def first_symbol_handler(message):
    alphabet = ['а', 'б', 'в', 'г', 'д', 'е', 'ж', 'з', 'и',
                'к', 'л', 'м', 'н', 'о', 'п', 'р', 'с', 'т', 'у',
                'ф', 'х', 'ц', 'ч', 'ш', 'щ', 'э']
    alphabet_bad = ['ё', 'й', 'ъ', 'ы', 'ь', 'ю', 'я']
    user_id = str(message.from_user.id)
    if message.text.lower() != 'сброс':
        if str(message.text).lower() in alphabet:
            user_data['first_symbol'][user_id]['first_letter'] = \
                str(message.text)
            bot.send_message(message.chat.id, 'Теперь все слова будут '
                                              'начинаться на букву ' + '"' +
                             user_data['first_symbol'][user_id]
                             ['first_letter'] + '"' + '\n' +
                             'Чтобы её изменить введите: "первая буква"',
                             reply_markup=markup)
            change_data('states', user_id, MAIN_STATE)
        elif str(message.text).lower() in alphabet_bad:
            bot.send_message(message.chat.id, 'На такую букву у меня нет '
                                              'слов, введи другую букву '
                                              'русского алфавита')
        elif 'что мне делать?' in message.text.lower():
            bot.send_message(user_id, 'Тебе надо выбрать букву '
                                      'русского алфавита')
        else:
            bot.send_message(message.chat.id, 'Я тебя не понял, введи букву '
                                              'русского алфавита')
    else:
        user_data['first_symbol'][user_id]['first_letter'] = ''
        bot.send_message(message.chat.id, 'Теперь все слова будут '
                                          'начинаться на разные буквы',
                         reply_markup=markup)
        change_data('states', user_id, MAIN_STATE)


bot.polling()
