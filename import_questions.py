import sqlite3
import json
import os
from questions import QUEST_DATA, RESULTS_DATA

def migrate():
    db_name = 'game_progress.db'
    
    # Удаляем старый файл БД, чтобы создать всё с чистого листа
    if os.path.exists(db_name):
        os.remove(db_name)
        print(f"Старый файл {db_name} удален для чистого обновления.")

    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # 1. Создаем таблицу для вопросов
    cursor.execute('''
        CREATE TABLE quest_content (
            step_id TEXT PRIMARY KEY,
            question_text TEXT,
            options_json TEXT
        )
    ''')

    # 2. Создаем таблицу для финальных результатов
    cursor.execute('''
        CREATE TABLE results_content (
            result_id TEXT,
            part_index INTEGER,
            content TEXT,
            PRIMARY KEY (result_id, part_index)
        )
    ''')
    
    # 3. Создаем таблицу для прогресса пользователей (чтобы бот не падал)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            current_step TEXT,
            score INTEGER
        )
    ''')

    # Заполняем вопросы
    for step_id, data in QUEST_DATA.items():
        cursor.execute(
            "INSERT INTO quest_content (step_id, question_text, options_json) VALUES (?, ?, ?)",
            (step_id, data['text'], json.dumps(data['options'], ensure_ascii=False))
        )

    # Заполняем результаты
    for res_id, parts in RESULTS_DATA.items():
        for i, text in enumerate(parts):
            cursor.execute(
                "INSERT INTO results_content (result_id, part_index, content) VALUES (?, ?, ?)",
                (res_id, i, text)
            )

    conn.commit()
    conn.close()
    print("--- Миграция успешно завершена! ---")
    print(f"Загружено вопросов: {len(QUEST_DATA)}")
    print(f"Загружено финальных сценариев: {len(RESULTS_DATA)}")

if __name__ == '__main__':
    migrate()