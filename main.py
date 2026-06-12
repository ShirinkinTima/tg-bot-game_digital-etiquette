import sqlite3
import telebot
from telebot import types

# Импортируем наши данные
from questions import QUEST_DATA, RESULTS_DATA

# Токен вашего бота
TOKEN = '8031020231:AAERTIeVe1QBcebSRNz8u8nq0t-ihgwzGro'
bot = telebot.TeleBot(TOKEN)

# --- РАБОТА С БАЗОЙ ДАННЫХ ---

def init_db():
    """Создает таблицу пользователей, если она еще не создана"""
    conn = sqlite3.connect('game_progress.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            current_step TEXT,
            score INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def get_user_data(user_id):
    """Получает данные игрока из БД"""
    conn = sqlite3.connect('game_progress.db')
    cursor = conn.cursor()
    cursor.execute("SELECT current_step, score FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {"step": row[0], "score": row[1]}
    return None

def save_user_data(user_id, step, score):
    """Сохраняет или обновляет прогресс игрока"""
    conn = sqlite3.connect('game_progress.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO users (user_id, current_step, score)
        VALUES (?, ?, ?)
    ''', (user_id, step, score))
    conn.commit()
    conn.close()

def delete_user_data(user_id):
    """Удаляет данные игрока (после завершения игры)"""
    conn = sqlite3.connect('game_progress.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- ЛОГИКА БОТА ---

# def get_keyboard(step_id):
#     """Автоматически создает столько кнопок, сколько вариантов в QUEST_DATA"""
#     markup = types.InlineKeyboardMarkup()
#     options = QUEST_DATA[step_id]["options"]
    
#     for i, opt in enumerate(options):
#         # callback_data содержит индекс нажатой кнопки
#         callback_data = f"btn_{i}"
#         markup.add(types.InlineKeyboardButton(text=opt["text"], callback_data=callback_data))
    
#     return markup

def get_keyboard(step_id):
    markup = types.InlineKeyboardMarkup()
    options = QUEST_DATA[step_id]["options"]
    
    # Создаем кнопки в один ряд (row), если их мало, или в столбик
    buttons = []
    for i, _ in enumerate(options):
        callback_data = f"btn_{i}"
        buttons.append(types.InlineKeyboardButton(text=str(i+1), callback_data=callback_data))
    
    markup.add(*buttons) # Добавит все кнопки в один ряд
    return markup

def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    start_button = types.InlineKeyboardButton(text="Посмотреть", callback_data="start_game")
    markup.add(start_button)
    
    welcome_text = (
        f"Привет, ты, наверное, знаешь её — про неё вся школа говорит."
        "Не знаю, что она будет делать, но видео с той тусовки уже залили сюда"
    )	
    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

# @bot.message_handler(commands=['start', 'game'])
# def start_cmd(message):
#     user_id = message.from_user.id
#     # Сбрасываем прогресс в БД на начало
#     save_user_data(user_id, "start", 0)
    
#     send_question(message.chat.id, user_id)
# Изменяем обработчик команды /start

@bot.message_handler(commands=['start'])
def start_cmd(message):
    send_welcome(message)

# Команда /stop для сброса
@bot.message_handler(commands=['stop'])
def stop_cmd(message):
    delete_user_data(message.from_user.id)
    bot.send_message(message.chat.id, "Игра остановлена. Чтобы начать заново, напиши что-нибудь.")

# Добавляем обработчик нажатия на кнопку "Начать приключение"
@bot.callback_query_handler(func=lambda call: call.data == "start_game")
def begin_game_callback(call):
    user_id = call.from_user.id
    # Инициализируем данные в БД
    save_user_data(user_id, "start", 0)
    
    # Убираем кнопку из приветствия, чтобы нельзя было нажать дважды
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="Интересно, что там.."
    )
    
    # Отправляем первый вопрос
    send_question(call.message.chat.id, user_id)
    bot.answer_callback_query(call.id)

# Обработчик любого текста и сообщений
@bot.message_handler(func=lambda message: True)
def handle_any_message(message):
    user_id = message.from_user.id
    data = get_user_data(user_id)
    
    if data:
        # Если пользователь уже в игре, а прислал текст вместо нажатия кнопки
        bot.reply_to(message, "Игра уже идет! Пожалуйста, используй кнопки под вопросом. "
                              "Если хочешь начать заново, введи /stop")
    else:
        # Если игры нет — отправляем приветствие
        send_welcome(message)

# def send_question(chat_id, user_id):
#     data = get_user_data(user_id)
#     if not data: return
    
#     step_id = data["step"]
    
#     # Если текущий шаг - финал или его нет в данных
#     if step_id == "finish" or step_id not in QUEST_DATA:
#         show_results(chat_id, user_id, data["score"])
#         return

#     question_text = QUEST_DATA[step_id]["text"]
#     bot.send_message(
#         chat_id, 
#         f"{question_text}", 
#         reply_markup=get_keyboard(step_id)
#     )

def send_question(chat_id, user_id):
    data = get_user_data(user_id)
    if not data: return
    
    step_id = data["step"]
    if step_id == "finish" or step_id not in QUEST_DATA:
        show_results(chat_id, user_id, data["score"])
        return

    question_text = QUEST_DATA[step_id]["text"]
    options = QUEST_DATA[step_id]["options"]
    
    # Формируем текст сообщения с перечислением вариантов
    full_message_text = f"{question_text}\n\n"
    for i, opt in enumerate(options):
        full_message_text += f"{i+1}. {opt['text']}\n" # Добавляем "1. Вариант текста"
        
    bot.send_message(
        chat_id, 
        full_message_text, 
        reply_markup=get_keyboard(step_id)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('btn_'))
def handle_answer(call):
    user_id = call.from_user.id
    data = get_user_data(user_id)
    if not data: return

    choice_index = int(call.data.split('_')[1])
    current_step_id = data["step"]
    choice_data = QUEST_DATA[current_step_id]["options"][choice_index]
    
    next_step = choice_data["next_step"]
    new_score = data["score"] + choice_data["score"]

    # ПРОВЕРКА: Если следующий шаг — это результат (есть в словаре RESULTS_DATA)
    if next_step in RESULTS_DATA:
        # Сохраняем: в step — название результата, в score — индекс текущей части (0)
        save_user_data(user_id, next_step, 0) 
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="Результат действий..")
        show_result_part(call.message.chat.id, user_id)
    else:
        # Обычный переход к следующему вопросу
        save_user_data(user_id, next_step, new_score)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"+ {choice_data['text']}")
        send_question(call.message.chat.id, user_id)

def show_result_part(chat_id, user_id):
    data = get_user_data(user_id)
    result_key = data["step"]  # например, "result_easy"
    part_index = data["score"] # текущий индекс части (0, 1 или 2)
    
    parts = RESULTS_DATA[result_key]
    text_to_send = parts[part_index]
    
    markup = types.InlineKeyboardMarkup()
    
    # Если еще есть части впереди
    if part_index < len(parts) - 1:
        markup.add(types.InlineKeyboardButton(text="Далее", callback_data="next_result"))
    else:
        # Если это последняя часть
        markup.add(types.InlineKeyboardButton(text="Далее", callback_data="finish_game"))
    
    bot.send_message(chat_id, text_to_send, reply_markup=markup)

# Обработка кнопки "Далее" в финале
@bot.callback_query_handler(func=lambda call: call.data == "next_result")
def handle_next_part(call):
    user_id = call.from_user.id
    data = get_user_data(user_id)
    
    if data and data["step"] in RESULTS_DATA:
        new_part_index = data["score"] + 1
        save_user_data(user_id, data["step"], new_part_index)
        
        # Убираем кнопку у старого сообщения
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=None)
        
        # Показываем следующую часть
        show_result_part(call.message.chat.id, user_id)
    bot.answer_callback_query(call.id)

# Обработка кнопки "Завершить"
@bot.callback_query_handler(func=lambda call: call.data == "finish_game")
def handle_finish(call):
    user_id = call.from_user.id
    delete_user_data(user_id) # Очищаем БД
    
    bot.edit_message_text(
        chat_id=call.message.chat.id, 
        message_id=call.message.message_id, 
        text="Следите за тем, как вы общаетесь в сети. Потому что как и здесь, там нет кнопки «назад»."
    )
    bot.answer_callback_query(call.id)

def show_results(chat_id, user_id, final_score):
    # Определяем звание
    rank = "Неизвестный странник"
    # Сортируем результаты по порогу очков (от большего к меньшему)
    sorted_results = sorted(RESULTS_DATA, key=lambda x: x['threshold'], reverse=True)
    
    for res in sorted_results:
        if final_score >= res["threshold"]:
            rank = res["word"]
            break
            
    result_text = (
        f"🏁 ПРИКЛЮЧЕНИЕ ОКОНЧЕНО!\n\n"
        f"Ваш итоговый счет: {final_score}\n"
        f"Ваш статус: {rank}\n\n"
        f"Чтобы играть снова, введите /start"
    )
    bot.send_message(chat_id, result_text)
    
    # Удаляем прогресс, чтобы начать с чистого листа в следующий раз
    delete_user_data(user_id)

if __name__ == '__main__':
    init_db() # Инициализируем БД при запуске
    print("Бот запущен...")
    bot.infinity_polling()