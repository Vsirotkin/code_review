import os
from aiogram.types import CallbackQuery, FSInputFile
from config.bot_config import bot
from lexicon.lexicon_ru import lexicon
from keyboards.admin_solve import admin_solve_keyboard
from keyboards.ins_report import ins_start_keyboard
import database.commands as db
from database.timers_deadline import insert_deadline_timer, get_timer_value


# Функция для положительного решения
async def get_good_solve(callback: CallbackQuery):
    try:
        await callback.answer()
        game_id = int(callback.data.rsplit("-")[-1])
        game = await db.get_game_by_id(game_id)
        time_delta = await get_timer_value("Default")
        await bot.send_message(
            chat_id=game[2],
            text=lexicon["report_exc"].format(game[6], game[7], time_delta),
            reply_markup=await ins_start_keyboard(game[1], game_id),
        )
        # Добавление таймера для проверяющего на рассмотрение ТЗ
        await insert_deadline_timer(game[2], "Проверяющий", time_delta, "tz")
        await callback.message.edit_text(text=lexicon["good_solve"], reply_markup=None)
    except Exception as e:
        logging.error(f"Error in get_good_solve: {e}")


# Функция для отрицательного решения
async def get_bad_solve(callback: CallbackQuery):
    try:
        await callback.answer()
        game_id = int(callback.data.rsplit("-")[-1])
        game = await db.get_game_by_id(game_id)
        user = await db.get_users_by_id(game[1])
        await callback.message.edit_text(
            text=lexicon["bad_solve"].format(user[1]),
            reply_markup=await admin_solve_keyboard(game_id, 0),
        )
    except Exception as e:
        logging.error(f"Error in get_bad_solve: {e}")


# Функция для экспорта данных пользователей
async def handle_export_users(callback_query: CallbackQuery):
    try:
        file_path = "./exports"  # Путь для сохранения файлов экспорта
        os.makedirs(file_path, exist_ok=True)
        # Экспортирует данные из таблицы "users" в файлы форматов CSV и Excel.
        await db.export_users_to_csv_and_excel(file_path)

        # Создание и отправка CSV файла пользователю
        csv_file = FSInputFile(f"{file_path}/users.csv", filename="users_data.csv")
        await bot.send_document(chat_id=callback_query.from_user.id, document=csv_file)

        # Создание и отправка Excel файла пользователю
        excel_file = FSInputFile(f"{file_path}/users.xlsx", filename="users_data.xlsx")
        await bot.send_document(
            chat_id=callback_query.from_user.id, document=excel_file
        )
    except Exception as e:
        logging.error(f"Error in handle_export_users: {e}")


# Функция для экспорта данных всех таблиц
async def handle_export_all_tables(callback_query: CallbackQuery):
    try:
        file_path = "./exports/all_tables"  # Путь для сохранения файлов экспорта
        await db.export_all_tables_to_csv_and_excel(
            file_path
        )  # Экспорт данных из всех таблиц
        # Отправка всех файлов
        for table in [
            "games",
            "args",
            "stats_task",
            "stats_judge",
            "stats_inspector",
            "stats_executor",
            "stats_player",
            "overdue_count",
            "timer_deadline",
            "timer_values",
        ]:
            # Создание и отправка CSV файла для каждой таблицы
            csv_file = FSInputFile(f"{file_path}/{table}.csv", filename=f"{table}.csv")
            await bot.send_document(
                chat_id=callback_query.from_user.id, document=csv_file
            )
            # Создание и отправка Excel файла для каждой таблицы
            excel_file = FSInputFile(
                f"{file_path}/{table}.xlsx", filename=f"{table}.xlsx"
            )
            await bot.send_document(
                chat_id=callback_query.from_user.id, document=excel_file
            )
    except Exception as e:
        logging.error(f"Error in handle_export_all_tables: {e}")
