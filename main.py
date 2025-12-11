import telebot
import random
import datetime
import os

token = '8570961043:AAHm0rk2iVapXE6kldOdcVmayn1QYsIhIyI'

bot = telebot.TeleBot(token)

def extract_party_code(text):
    return text.split()[1] if len(text.split()) > 1 else None

@bot.message_handler(commands=['start'])
def start(message):
    # safely extract start payload (e.g. "pool_xxx")
    payload = None
    if message.text:
        parts = message.text.split(maxsplit=1)
        if len(parts) > 1:
            payload = parts[1].strip()

    if payload and payload.startswith('pool_'):
        filename = f'{payload}.txt'

        # read existing participant ids (avoid duplicates)
        participants = set()
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                participants = {line.strip() for line in f if line.strip()}

        user_id = str(message.from_user.id)
        if user_id not in participants:
            participants.add(user_id)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(sorted(participants)))

        # create default profile if missing or empty
        userfile = f'{user_id}.txt'
        if (not os.path.exists(userfile)) or os.path.getsize(userfile) == 0:
            username = message.from_user.username
            with open(userfile, 'w', encoding='utf-8') as uf:
                if username:
                    uf.write(f'profile of https://t.me/{username} (tg://{user_id})')
                else:
                    uf.write(f'profile of tg://{user_id} ({user_id})')

        with open(userfile, 'r', encoding='utf-8') as uf:
            profile_contents = uf.read()

        bot.send_message(message.chat.id,
                         f'Вы успешно присоединились к группе {payload}.\n\n'
                         f'Чтобы отредактировать профиль, напишите /editprofile\n\n'
                         f'Твой профиль сейчас выглядит так:\n{profile_contents}')
        return

    # default start behaviour
    bot.send_message(message.chat.id, 'Привет! Это бот по тайному санте! Если тебя пригласили присоединиться - перейди по ссылке твоего организатора, если ты и есть организатор - создай свою группу. \n\n Создать группу - startparty\n\nРедактировать профиль - /editprofile\n\nПросмотреть свой профиль - /myprofile\n\n Просмотреть профиль получателя /myrecipent')

@bot.message_handler(commands=['editprofile'])
def edit_profile(message):
    filename = f'{message.from_user.id}.txt'
    try:
        current = open(filename, 'r', encoding='utf-8').read()
    except FileNotFoundError:
        current = '(пустой профиль)'
    bot.send_message(
        message.from_user.id,
        f'Твой профиль сейчас выглядит так:\n{current}\n\n'
        'Ответь на это сообщение, чтобы ЗАМЕНИТЬ текст, который сейчас у тебя в профиле.\n\n'
        'В конце будет ссылка на твой профиль в формате t.me/твой_юзер (если есть username) '
        'или tg://<id> если username нет.'
    )
    # register_next_step_handler will call profile_write(message, filename)
    bot.register_next_step_handler(message, profile_write, filename)

def profile_write(message, filename):
    contents = message.text or ''
    username = message.from_user.username
    with open(filename, 'w', encoding='utf-8') as file:
        if username:
            file.write(contents + f'\nhttps://t.me/{username}')
        else:
            file.write(contents + f'\ntg://{message.from_user.id}')
    with open(filename, 'r', encoding='utf-8') as file:
        saved = file.read()
    bot.send_message(message.from_user.id, f'Твой профиль сохранён:\n{saved}')

def create_pool(message):
    code = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
    pool_name = f'pool_{code}'
    filename = f'{pool_name}.txt'
    creator_id = str(message.from_user.id)

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(creator_id + '\n')

    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = None

    if bot_username:
        deeplink = f'https://t.me/{bot_username}?start={pool_name}'
    else:
        deeplink = f'/start {pool_name}  (попросите пользователей отправить эту команду боту)'

    bot.send_message(
        message.from_user.id,
        f'Создан пул: {pool_name}\n\n'
        f'Ссылка для приглашения участников:\n{deeplink}\n\n'
        'Когда участник перейдёт по ссылке, бот добавит его в этот пул.'
    )
    return pool_name

@bot.message_handler(commands=['startparty'])
def startparty_handler(message):
    bot.send_message(message.from_user.id, f'Когда вы захотите запустить жеребьёвку, перейдите по этой ссылке: \nhttps://t.me/{bot.get_me().username}?draw={create_pool(message)}')

@bot.message_handler(commands=['draw'])
def draw(message):
    party_code = extract_party_code(message.text)
    if party_code is None:
        bot.send_message(message.from_user.id, 'Пожалуйста, укажите код группы для жеребьёвки.')
        return

    try:
        with open(f'{party_code}.txt', 'r', encoding='utf-8') as party_pool:
            participants = party_pool.read().strip().split('\n')
    except FileNotFoundError:
        bot.send_message(message.from_user.id, 'Группа с таким кодом не найдена.')
        return

    if len(participants) < 2:
        bot.send_message(message.from_user.id, 'Недостаточно участников для жеребьёвки.')
        return

    random.shuffle(participants)
    assignments = {participants[i]: participants[(i + 1) % len(participants)] for i in range(len(participants))}

    for giver, receiver in assignments.items():
        try:
            bot.send_message(giver, f'Ты тайный Санта для: {receiver}')
        except Exception as e:
            bot.send_message(message.from_user.id, f'Не удалось отправить сообщение участнику {giver}: {str(e)}')

    bot.send_message(message.from_user.id, 'Жеребьёвка завершена! Участники получили свои назначения.')

@bot.message_handler(commands=['myprofile'])
def my_profile(message):
    filename = f'{message.from_user.id}.txt'
    try:
        profile = open(filename, 'r', encoding='utf-8').read()
    except FileNotFoundError:
        profile = '(пустой профиль)'
    bot.send_message(message.from_user.id, f'Твой профиль выглядит так:\n{profile}')

@bot.message_handler(commands=['endparty'])
def end_party(message):
    party_code = extract_party_code(message.text)
    if party_code is None:
        bot.send_message(message.from_user.id, 'Пожалуйста, укажите код группы для завершения.')
        return

    filename = f'{party_code}.txt'
    try:
        with open(filename, 'r', encoding='utf-8') as party_pool:
            participants = party_pool.read().strip().split('\n')
    except FileNotFoundError:
        bot.send_message(message.from_user.id, 'Группа с таким кодом не найдена.')
        return

    for participant in participants:
        try:
            bot.send_message(participant, 'Группа завершена организатором. Спасибо за участие!')
        except Exception as e:
            bot.send_message(message.from_user.id, f'Не удалось отправить сообщение участнику {participant}: {str(e)}')

    try:
        os.remove(filename)
        bot.send_message(message.from_user.id, f'Группа {party_code} успешно завершена и удалена.')
    except Exception as e:
        bot.send_message(message.from_user.id, f'Не удалось удалить группу {party_code}: {str(e)}')

if __name__ == '__main__':
    bot.polling(none_stop=True)


