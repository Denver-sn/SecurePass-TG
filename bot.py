# -*- coding: utf-8 -*-
# Код шифрованя был взят из https://www.quickprogrammingtips.com/python/aes-256-encryption-and-decryption-in-python.html

import base64
from Cryptodome.Cipher import AES
from Cryptodome import Random
from Cryptodome.Protocol.KDF import PBKDF2
import random
import os
import models
import telebot
from telebot import *
import json
import requests

# apihelper.proxy = {
#         'https': 'socks5h://{}:{}'.format('127.0.0.1','4444')
#     }

commands = [{'command':'start', 'description':'start'}, {'command':'add', 'description':'add new block'}, {'command':'all', 'description':'view all you blocks'}, {'command':'help', 'description':'help'}]

folder = os.path.dirname(os.path.abspath(__file__))

cfg = json.loads(open('cfg.txt', 'r').read())

bot = telebot.TeleBot(cfg['token'])
requests.get(f'https://api.telegram.org/bot{cfg["token"]}/setMyCommands?commands={json.dumps(commands)}')

BLOCK_SIZE = 16
pad = lambda s: s + (BLOCK_SIZE - len(s) % BLOCK_SIZE) * chr(BLOCK_SIZE - len(s) % BLOCK_SIZE)
unpad = lambda s: s[:-ord(s[len(s) - 1:])]

def get_salt():
    return str(random.randint(100000000000, 999999999999))

def get_password_hash(password, salt):
    salt = salt.encode()
    kdf = PBKDF2(password, salt, 64, 1000)
    key = kdf[:32]
    return key

def encrypt(raw, password):
    private_key = password
    raw = pad(raw)
    iv = Random.new().read(AES.block_size)
    cipher = AES.new(private_key, AES.MODE_CBC, iv)
    return bytes.decode(base64.b64encode(iv + cipher.encrypt(raw.encode())))

def decrypt(enc, password):
    private_key = password
    enc = base64.b64decode(enc)
    iv = enc[:16]
    cipher = AES.new(private_key, AES.MODE_CBC, iv)
    return bytes.decode(unpad(cipher.decrypt(enc[16:])))

def add_data(user, data, name, password, login=False):
    salt1 = get_salt()
    hash1 = get_password_hash(password, salt1)
    if login != False:
        login = encrypt(login, hash1)
    data = models.Data.create(user=user, data=encrypt(data, hash1), login=login, name=name, salt=salt1)
    data.save()
    return data

def get_data(data, password):
    salt = data.salt
    enc = decrypt(data.data, get_password_hash(password, salt))
    if str(data.login) != str(False):
        enc1 = decrypt(data.login, get_password_hash(password, salt))
    else:
        enc1 = None
    return (enc, enc1)

def add_user(id, username = False, firstname = False, lastname = False):
    try:
        user = models.User.get(user_id=id)
        user.username = username or False
        user.firstname = firstname or False
        user.lastname = lastname or False
    except:
        user = models.User.create(user_id = id, username = username or False, firstname = firstname or False, lastname = lastname or False)
    user.save()
    return user

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    text = call.data
    uid = call.from_user.id
    mid = call.message.message_id
    spl = text.split('_')
    id = int(call.message.json['chat']['id'])
    for i in range(9):
        try:
            spl[i]
        except:
            spl.append('')
    if spl[0] == 'delete-message':
        bot.delete_message(id, int(spl[1])+1)
    elif spl[0] == 'delete':
        models.Data.get(uuid=spl[1]).delete_instance()
        bot.delete_message(id, mid)

@bot.message_handler(commands=['start'])
def com(message):
    m = message
    text = m.text
    id = m.chat.id
    uid = m.from_user.id
    user = add_user(id = uid, username =  m.from_user.username, firstname =  m.from_user.first_name, lastname =  m.from_user.last_name)
    bot.send_message(id, f"""Привет {user.firstname}, я бот который будет надёжно хранить твои данные в безопасном хранилище!
● Надёжное AES-256 шифрование твоим паролем
● Пароль нигде не хранится (даже хэш), сообщение с ним удаляется
● Полностью открытый <a href="https://github.com/TheAngryPython/SecurePass-TG">исходный код</a>. Ты можешь сам убедиться в нашей честности.

Для того чтобы начать напиши /add""", disable_web_page_preview=True, parse_mode='html')

@bot.message_handler(commands=['help'])
def com(message):
    m = message
    text = m.text
    id = m.chat.id
    uid = m.from_user.id
    user = add_user(id = uid, username =  m.from_user.username, firstname =  m.from_user.first_name, lastname =  m.from_user.last_name)
    bot.send_message(id, f"""Меня разрабатывает @EgTer. Я написан на python, мой <a href="https://github.com/TheAngryPython/SecurePass-TG">исходный код</a> выдожен на github. Использую шифрование AES-256, хэши паролей не хранятся, а это значит что даже получив доступ к базе данных, НИКТО и НИКОГДА не сможет узнать каким паролем зашифрованы ваши данные""", disable_web_page_preview=True, parse_mode='html')

@bot.message_handler(commands=['add'])
def com(message):
    m = message
    text = m.text
    id = m.chat.id
    uid = m.from_user.id
    user = add_user(id = uid, username =  m.from_user.username, firstname =  m.from_user.first_name, lastname =  m.from_user.last_name)
    user.action = 'data_name'
    user.save()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    cancel = types.KeyboardButton('Остановить')
    markup.row(cancel)
    bot.send_message(id, f"""{user.firstname}, напиши название блока (не шифруется, для вашего удобства). (Помните, что во время создания блока данные хранятся в незашифрованном виде)""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)

@bot.message_handler(commands=['all'])
def com(message):
    m = message
    text = m.text
    id = m.chat.id
    uid = m.from_user.id
    user = add_user(id = uid, username =  m.from_user.username, firstname =  m.from_user.first_name, lastname =  m.from_user.last_name)
    user.action = 'block_see'
    user.tmp = False
    user.save()
    blocks = models.Data.filter(user=user)
    if len(blocks) != 0:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for block in blocks:
            btn = types.KeyboardButton(block.name)
            markup.row(btn)
        bot.send_message(id, f"""Вот твои блоки""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)
    else:
        markup = types.ReplyKeyboardRemove()
        bot.send_message(id, f"""У тебя нет блоков. Создать /add""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)

@bot.message_handler(content_types=['text'])
def com(message):
    m = message
    text = m.text
    id = m.chat.id
    uid = m.from_user.id
    mid = m.message_id
    user = add_user(id = uid, username =  m.from_user.username, firstname =  m.from_user.first_name, lastname =  m.from_user.last_name)
    if text == 'Остановить':
        user.action = False
        user.tmp = False
        user.save()
        markup = types.ReplyKeyboardRemove()
        bot.send_message(id, f"""Действие прервано""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)
    elif user.action == 'data_name':
        try:
            t = True
            models.Data.get(user=user,name=text)
        except:
            t = False
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            cancel = types.KeyboardButton('Остановить')
            no = types.KeyboardButton('Нет')
            markup.row(no, cancel)
            tmp = {'name': text}
            user.tmp = json.dumps(tmp)
            bot.delete_message(id,mid)
            bot.send_message(id, f"""Хорошо, теперь отправь логин (если не требуется нажми "Нет").""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)
            user.action = 'data_login'
            user.save()
        if t:
            bot.send_message(id, f"""У вас уже есть блок с таким названием.""", disable_web_page_preview=True, parse_mode='html')
    elif user.action == 'data_login':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        cancel = types.KeyboardButton('Остановить')
        markup.row(cancel)
        tmp = json.loads(user.tmp)
        if text == 'Нет' or text == 'No':
            tmp['login'] = False
        else:
            tmp['login'] = text
        user.tmp = json.dumps(tmp)
        bot.delete_message(id,mid)
        bot.send_message(id, f"""Дальше идёт сам блок с данными (пароль, пин-код, кодовое слово).""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)
        user.action = 'data_password'
        user.save()
    elif user.action == 'data_password':
        tmp = json.loads(user.tmp)
        tmp['password'] = text
        user.tmp = json.dumps(tmp)
        bot.delete_message(id,mid)
        bot.send_message(id, f"""Теперь нужен ключ для шифрования всех этих данных.""", disable_web_page_preview=True, parse_mode='html')
        user.action = 'data_key'
        user.save()
    elif user.action == 'data_key':
        tmp = json.loads(user.tmp)
        bot.delete_message(id,mid)
        add_data(user, tmp['password'], tmp['name'], text, login=tmp['login'])
        bot.send_message(id, f"""Блок создан!

Просмореть все блоки: /all""", disable_web_page_preview=True, parse_mode='html')
        user.action = False
        user.save()
    elif user.action == 'block_see':
        try:
            models.Data.get(user=user,name=text)
            user.action = 'block_open'
            user.tmp = text
            user.save()
            bot.delete_message(id,mid)
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            cancel = types.KeyboardButton('Остановить')
            markup.row(cancel)
            bot.send_message(id, f"""Введи пароль от блока""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)
        except:
            bot.send_message(id, f"""Такого блока не существует""", disable_web_page_preview=True, parse_mode='html')
    elif user.action == 'block_open':
        try:
            block = models.Data.get(user=user,name=user.tmp)
            data = get_data(block, text)
            bot.delete_message(id,mid)
            if not data[0]:
                markup = types.ReplyKeyboardRemove()
                bot.send_message(id, f"""Неправильный пароль от блока {block.uuid}""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)
            else:
                user.action = False
                user.save()
                keyboard = types.InlineKeyboardMarkup()
                button_1 = types.InlineKeyboardButton(text='Удалить Блок', callback_data=f'delete_{block.uuid}')
                keyboard.add(button_1)
                button_1 = types.InlineKeyboardButton(text='Удалить сообщение', callback_data=f'delete-message_{mid}')
                keyboard.add(button_1)
                button_1 = types.InlineKeyboardButton(text='Переименовать Блок', callback_data=f'rename_{block.uuid}')
                keyboard.add(button_1)
                bot.send_message(id, f"""Блок {block.uuid}
Логин: {data[1]}
Пароль: {data[0]}

Удалите это сообщение по завершении.""", disable_web_page_preview=True, parse_mode='html', reply_markup=keyboard)
        except:
            markup = types.ReplyKeyboardRemove()
            bot.send_message(id, f"""Блок не найден!""", disable_web_page_preview=True, parse_mode='html', reply_markup=markup)

bot.polling(none_stop=True, timeout=123)