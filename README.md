# code_review

# REVIEW OF START GAME FILE
В этом коде есть несколько потенциальных ошибок и проблем, которые могут привести к некорректной работе или исключениям. Вот основные из них:

1. **Неопределенное поведение при исключениях:**
   В функциях `get_ts`, `get_report_with_error`, `get_report_without_error` используется неопределенное поведение при исключениях. Использование `except:` без указания типа исключения может привести к перехвату непредвиденных исключений, что затруднит отладку.

   ```python
   async def get_ts(message: Message, state: FSMContext):
       try:
           document_id = message.text
       except:
           await message.answer(text=lexicon['document_error'])
           return
       user = await db.get_users_by_id(message.chat.id)
       await state.update_data(ts=document_id)
       await message.answer(text=lexicon['report_with_error'].format(user[3]))
       await state.set_state(GameStates.WITH_ERROR)
   ```

   **Исправление:**
   Следует явно указывать тип исключения, например, `except Exception as e:`.

2. **Отсутствие обработки ошибок при асинхронных вызовах:**
   В функциях, где происходят асинхронные вызовы к базе данных (например, `await db.get_users_by_id`), отсутствует обработка возможных исключений, что может привести к неожиданным сбоям.

   ```python
   user = await db.get_users_by_id(message.chat.id)
   ```

   **Исправление:**
   Добавить обработку исключений для асинхронных вызовов.

3. **Использование индексов для доступа к элементам кортежа:**
   В нескольких местах используются индексы для доступа к элементам кортежа (например, `user[3]`, `user[0]`). Это снижает читаемость кода и может привести к ошибкам, если структура данных изменится.

   ```python
   await callback.message.edit_text(text=lexicon['start_game'].format(user[3], formatted_deadline_time))
   ```

   **Исправление:**
   Использовать именованные атрибуты или словари для доступа к данным.

4. **Отсутствие логирования:**
   В коде отсутствует логирование, что затрудняет отладку и мониторинг работы приложения.

   **Исправление:**
   Добавить логирование для ключевых операций и исключений.

Пример исправленного кода с учетом этих замечаний:

```python
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from database.timers_deadline import insert_deadline_timer, delete_deadline_timer, get_timer_value
from keyboards.start_keyboard import start_keyboard
from lexicon.lexicon_ru import lexicon
from states.game import GameStates
from config.bot_config import bot
from keyboards.admin_solve import admin_solve_keyboard

import database.commands as db
from utils import capitalize

logging.basicConfig(level=logging.ERROR)

async def start_game(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    try:
        user = await db.get_users_by_id(callback.message.chat.id)
        if not user[7]:
            time_delta = await get_timer_value("TZ")
            deadline_time = datetime.now() + timedelta(hours=time_delta)
            formatted_deadline_time = deadline_time.strftime("%Y/%m/%d %H:%M")
            await callback.message.edit_text(text=lexicon['start_game'].format(user[3], formatted_deadline_time))
            await asyncio.sleep(1)
            await callback.message.answer(text=lexicon['report_ts'].format(user[3]))
            await state.set_state(GameStates.TS)

            await insert_deadline_timer(user[0], "Исполнитель", time_delta, "tz")

            return

        await callback.message.edit_text(text=lexicon['err_start_game'])
    except Exception as e:
        logging.error(f"Error in start_game: {e}")
        await callback.message.edit_text(text=lexicon['err_start_game'])


async def get_ts(message: Message, state: FSMContext):
    try:
        document_id = message.text
    except Exception as e:
        logging.error(f"Error in get_ts: {e}")
        await message.answer(text=lexicon['document_error'])
        return
    try:
        user = await db.get_users_by_id(message.chat.id)
        await state.update_data(ts=document_id)
        await message.answer(text=lexicon['report_with_error'].format(user[3]))
        await state.set_state(GameStates.WITH_ERROR)
    except Exception as e:
        logging.error(f"Error in get_ts: {e}")
        await message.answer(text=lexicon['document_error'])


async def get_report_with_error(message: Message, state: FSMContext):
    try:
        document_id = message.text
    except Exception as e:
        logging.error(f"Error in get_report_with_error: {e}")
        await message.answer(text=lexicon['document_error'])
        return
    try:
        user = await db.get_users_by_id(message.chat.id)
        await state.update_data(with_error=document_id)
        await message.answer(text=lexicon['report_without_error'].format(user[3]))
        await state.set_state(GameStates.WITHOUT_ERROR)
    except Exception as e:
        logging.error(f"Error in get_report_with_error: {e}")
        await message.answer(text=lexicon['document_error'])


async def get_report_without_error(message: Message, state: FSMContext):
    try:
        document_id = message.text
    except Exception as e:
        logging.error(f"Error in get_report_without_error: {e}")
        await message.answer(text=lexicon['document_error'])
        return
    try:
        user = await db.get_users_by_id(message.chat.id)
        await state.update_data(without_error=document_id)
        await message.answer(text=lexicon['all_errors'].format(user[3]))
        await state.set_state(GameStates.ERRORS)
    except Exception as e:
        logging.error(f"Error in get_report_without_error: {e}")
        await message.answer(text=lexicon['document_error'])


async def get_all_errors(message: Message, state: FSMContext):
    try:
        user = await db.get_users_by_id(message.chat.id)
        await state.update_data(all_errors=message.text)
        await message.answer(text=lexicon['count_errors'].format(user[3]), parse_mode=ParseMode.HTML)
        await state.set_state(GameStates.COUNT)
    except Exception as e:
        logging.error(f"Error in get_all_errors: {e}")
        await message.answer(text=lexicon['document_error'])


async def get_count_errors(message: Message, state: FSMContext):
    try:
        user = await db.get_users_by_id(message.chat.id)
        await state.update_data(count_errors=message.text)
        await message.answer(text=lexicon['finish_get_reports'].format(user[3]))
        # Удаление дедлайна для исполнителя после отправки ТЗ
        await delete_deadline_timer(user[0])

        data = await state.get_data()

        if 'user_id' in data.keys():
            del data['user_id']
        res = await db.insert_new_game(message.chat.id, **data)
        if not res:
            await message.answer(text=lexicon['not_users_game'].format(user[3]))
            await asyncio.sleep(0.5)
            await message.answer(text=lexicon["start_else"].format(capitalize(message.from_user.first_name)),
                                 reply_markup=await start_keyboard(user[6]))
            return

        game = await db.get_last_game()
        admin = await db.get_users_by_id(game[4])

        await bot.send_message(chat_id=game[4], text=lexicon['report_to_admin'].format(admin[3], user[3], game[5], game[6]),
                               reply_markup=await admin_solve_keyboard(game[0], 1), disable_web_page_preview=True)

        await state.set_state(None)
    except Exception as e:
        logging.error(f"Error in get_count_errors: {e}")
        await message.answer(text=lexicon['document_error'])
```

Этот код включает обработку исключений и логирование, что улучшит его надежность и упростит отладку.


#  REVIEW OF NOTIFICATION FILE
В этом коде есть несколько потенциальных ошибок и проблем, которые могут привести к некорректной работе или исключениям. Вот основные из них:

1. **Неопределенное поведение при исключениях:**
   В функции `appointment_new_judge` есть ошибка в строке форматирования текста:
   ```python
   text = lexicon["judge_start"].format(judge[3],
                                        f"{executor[2]} {executor[3]} {
                                        executor[4]}",
                                        f"{inspector[2]} {inspector[3]} {
                                        inspector[4]}",
                                        time_delta)
   ```
   Это приведет к синтаксической ошибке из-за неправильного использования многострочных строк.

   **Исправление:**
   Исправить форматирование строки:
   ```python
   text = lexicon["judge_start"].format(judge[3],
                                        f"{executor[2]} {executor[3]} {executor[4]}",
                                        f"{inspector[2]} {inspector[3]} {inspector[4]}",
                                        time_delta)
   ```

2. **Отсутствие обработки ошибок при асинхронных вызовах:**
   Во многих местах кода отсутствует обработка возможных исключений при асинхронных вызовах к базе данных или отправке сообщений. Например:
   ```python
   user_data = await get_users_by_id(new_user_id)
   ```
   **Исправление:**
   Добавить обработку исключений для асинхронных вызовов.

3. **Использование индексов для доступа к элементам кортежа:**
   В нескольких местах используются индексы для доступа к элементам кортежа (например, `user_data[3]`, `game[2]`). Это снижает читаемость кода и может привести к ошибкам, если структура данных изменится.

   **Исправление:**
   Использовать именованные атрибуты или словари для доступа к данным.

4. **Отсутствие логирования:**
   В коде отсутствует логирование, что затрудняет отладку и мониторинг работы приложения.

   **Исправление:**
   Добавить логирование для ключевых операций и исключений.

5. **Использование глобальной переменной `sent_notifications`:**
   Глобальная переменная `sent_notifications` может вызвать проблемы при параллельном выполнении или в многопоточной среде.

   **Исправление:**
   Рассмотреть использование более подходящих структур данных или механизмов синхронизации.

Пример исправленного кода с учетом вышеобозначенных замечаний:

```python
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from datetime import datetime, timedelta
from database.commands import (get_users_by_id,
                               find_free_user,
                               change_in_game,
                               get_last_game_id_by_user_id,
                               get_game_by_id,
                               update_role_in_game,
                               get_arg,
                               update_stats)
from database.timers_deadline import (get_deadline_users,
                                      get_timer_value,
                                      delete_deadline_timer,
                                      increment_overdue_count,
                                      insert_deadline_timer)
from lexicon.lexicon_ru import lexicon
from states.game import GameStates
from keyboards.ins_report import ins_start_keyboard
from keyboards.argument import judge_argument
from keyboards.start_keyboard import start_keyboard

logging.basicConfig(level=logging.ERROR)

async def appointment_new_executor(bot: Bot, dp: Dispatcher, old_user_id: int, new_user_id: int, role: str,
                                   old_user_info: list) -> None:
    try:
        # Если новый исполнитель не является старым
        if new_user_id != old_user_id:
            await bot.send_message(chat_id=old_user_id, text=lexicon["start_else"].format(old_user_info[3]),
                                   reply_markup=await start_keyboard(role))
        user_data = await get_users_by_id(new_user_id)
        time_delta = await get_timer_value("TZ")
        deadline_time = datetime.now() + timedelta(hours=time_delta)
        formatted_deadline_time = deadline_time.strftime("%d-%m-%Y %H:%M")
        await bot.send_message(new_user_id, text=lexicon['start_game'].format(user_data[3], formatted_deadline_time))
        await asyncio.sleep(1)
        await bot.send_message(new_user_id, text=lexicon['report_ts'].format(user_data[3]))
        await insert_deadline_timer(new_user_id, role, time_delta, "tz")
        # Создание ключа для пользователя
        user_key = StorageKey(
            user_id=new_user_id, chat_id=new_user_id, bot_id=bot.id)
        # Инициализация FSMContext с этим ключом
        user_state = FSMContext(storage=dp.fsm.storage, key=user_key)
        await user_state.update_data()  # обновить дату для пользователя
        # Установка состояния GameStates.TS для Исполнителя
        await user_state.set_state(GameStates.TS)
    except Exception as e:
        logging.error(f"Error in appointment_new_executor: {e}")


async def appointment_new_inspector(bot: Bot, old_user_id: int, new_user_id: int, role: str) -> None:
    try:
        # Получаем текущую игру в которой участвует Проверяющий
        game_id = await get_last_game_id_by_user_id(old_user_id)
        # Назначение нового игрока Проверяющим
        await update_role_in_game(game_id, "inspector", new_user_id)
        # Получение игры в которой участвовал Проверяющий
        game = await get_game_by_id(game_id)
        time_delta = await get_timer_value("Default")
        await bot.send_message(chat_id=game[2], text=lexicon["report_exc"].format(game[6], game[7], time_delta),
                               reply_markup=await ins_start_keyboard(game[1], game_id))
        # Добавление таймера для проверяющего на рассмотрение ТЗ
        await insert_deadline_timer(game[2], role, time_delta, "tz")
    except Exception as e:
        logging.error(f"Error in appointment_new_inspector: {e}")


async def appointment_new_judge(bot: Bot, old_user_id: int, new_user_id: int, role: str) -> None:
    try:
        # Получаем текущую игру в которой участвует Судья
        game_id = await get_last_game_id_by_user_id(old_user_id)
        # Назначение нового игрока Судьей
        await update_role_in_game(game_id, "judge", new_user_id)
        game = await get_game_by_id(game_id)
        args = await get_arg(game_id)
        # Поучаем данные об участниках игры
        executor = await get_users_by_id(game[1])
        inspector = await get_users_by_id(game[2])
        judge = await get_users_by_id(new_user_id)
        time_delta = await get_timer_value("Default")
        # Отправка сообщения новому Судье
        text = lexicon["judge_start"].format(judge[3],
                                             f"{executor[2]} {executor[3]} {executor[4]}",
                                             f"{inspector[2]} {inspector[3]} {inspector[4]}",
                                             time_delta)
        await bot.send_message(new_user_id, text=text)
        # Установка таймера дедлайна на принятие новым судьей решения
        await insert_deadline_timer(new_user_id, "Судья", time_delta, "solve")
        text = lexicon["judge_task"].format(
            game[5], game[6], game[8], args[2], args[3])
        keyboard_judge = await judge_argument(game_id)
        await bot.send_message(chat_id=game[3], text=text, reply_markup=keyboard_judge)
    except Exception as e:
        logging.error(f"Error in appointment_new_judge: {e}")


async def clear_status(user_id: int, bot: Bot, dp: Dispatcher) -> None:
    """Очистка состояния пользователя, при дедлайне"""
    try:
        user_key = StorageKey(user_id=user_id, chat_id=user_id, bot_id=bot.id)
        user_state = FSMContext(storage=dp.fsm.storage, key=user_key)
        await user_state.clear()
    except Exception as e:
        logging.error(f"Error in clear_status: {e}")


sent_notifications = set()
async def check_deadlines(bot: Bot, dp: Dispatcher) -> None:
    """Проверка дедлайнов и отправка уведомлений"""
    while True:
        try:
            now = datetime.now()
            now = now.replace(second=0, microsecond=0)
            deadlines = await get_deadline_users()
            for deadline in deadlines:
                user_id, role, deadline_time, stage = deadline
                deadline_time = datetime.strptime(
                    deadline_time, '%Y-%m-%d %H:%M:%S.%f')
                deadline_time = deadline_time.replace(second=0, microsecond=0)
                # добавлаем ключи
                notification_key_2h = (user_id, role, deadline_time, stage, '2h')
                notification_key_1h = (user_id, role, deadline_time, stage, '1h')
                if now > deadline_time:
                    await delete_deadline_timer(user_id)
                    # сброс уведомления
                    sent_notifications.discard(notification_key_2h)
                    sent_notifications.discard(notification_key_1h)
                    user_info = await get_users_by_id(user_id)
                    # Отменяем участие пользователя в игре в таблице users
                    await change_in_game(user_id, 0)
                    match stage:
                        # В случае этапа ТЗ
                        case "tz":
                            text = lexicon['delay_tz']
                            await bot.send_message(chat_id=user_id, text=text)
                            if role == "Испольнитель":
                                # Очищаем его состояние
                                await clear_status(user_id, bot, dp)
                                # Находим нового исполнителя
                                new_user = await find_free_user(role)
                                # Назначаем нового исполнителя
                                await appointment_new_executor(bot, dp, user_id, new_user, role, user_info)
                            if role == "Проверяющий":
                                # Очищаем его состояние
                                await clear_status(user_id, bot, dp)
                                # Находим нового проверяющего
                                new_user = await find_free_user(role)
                                # Назначаем нового инспектора
                                await appointment_new_inspector(bot, user_id, new_user, role)
                        # В случае при просрочке судьи
                        case "solve":
                            await bot.send_message(chat_id=user_id, text=text)
                            text = lexicon['delay_solve']
                            # Находим нового Судью
                            new_user = await find_free_user(role)
                            # Назначаем нового инспектора
                            await appointment_new_judge(bot, user_id, new_user, role)
                        case _:
                            text = lexicon['delay_answer']
                            # Получаем текущую игру в которой участвует игроки
                            game_id = await get_last_game_id_by_user_id(user_id)
                            # Получение данных о игроках в игре
                            game = await get_game_by_id(game_id)
                            wins_ins = 0
                            # Отравляем уведомления о завершении игры
                            if role == "Исполнитель":
                                await bot.send_message(chat_id=game[2],
                                                       text=f"{lexicon['win']}\n{lexicon['win_deadline_exe']}")
                                await bot.send_message(chat_id=game[1],
                                                       text=f"{lexicon['loose']}\n{lexicon['delay_answer']}")
                                await bot.send_message(chat_id=game[1], text=lexicon["start_else"].format(user_info[3]),
                                                       reply_markup=await start_keyboard(role))
                            else:
                                wins_ins = 1
                                await bot.send_message(chat_id=game[1],
                                                       text=f"{lexicon['win']}\n{lexicon['win_deadline_ins']}")
                                await bot.send_message(chat_id=game[2],
                                                       text=f"{lexicon['loose']}\n{lexicon['delay_answer']}")
                            # Обновление статистики игры
                            await update_stats(game, 0, wins_ins, overdue_role=role)
                            await clear_status(game[1], bot, dp)
                            await clear_status(game[2], bot, dp)
                    # Добавление в БД просрочки пользователя
                    await increment_overdue_count(user_id)

                # Уведомления за 2 часа до дедлайна
                elif now >= deadline_time - timedelta(hours=2) and now < deadline_time - timedelta(hours=1):
                    if notification_key_2h not in sent_notifications:
                        await bot.send_message(chat_id=user_id, text=lexicon['two_hour_left'])
                        sent_notifications.add(notification_key_2h)

                # Уведомления за 1 часа до дедлайна
                elif now >= deadline_time - timedelta(hours=1) and now < deadline_time:
                    if notification_key_1h not in sent_notifications:
                        await bot.send_message(chat_id=user_id, text=lexicon['one_hour_left'])
                        sent_notifications.add(notification_key_1h)

            await asyncio.sleep(60)
        except Exception as e:
            logging.error(f"Error in check_deadlines: {e}")
```

Этот код включает обработку исключений и логирование, что улучшит его надежность и упростит отладку.


# REVIEW OF CHANGE ROLE FILE
В коде есть несколько потенциальных ошибок и проблем, которые могут привести к некорректной работе или исключениям. Вот основные из них:

1. **Неопределенное поведение при исключениях:**
   В функциях `select_role` и `changed_role` отсутствует обработка возможных исключений при асинхронных вызовах к базе данных или отправке сообщений. Например:
   ```python
   user = await db.get_users_by_id(user_id)
   ```
   **Исправление:**
   Добавить обработку исключений для асинхронных вызовов.

2. **Использование индексов для доступа к элементам кортежа:**
   В нескольких местах используются индексы для доступа к элементам кортежа (например, `user[3]`, `user[0]`). Это снижает читаемость кода и может привести к ошибкам, если структура данных изменится.

   **Исправление:**
   Использовать именованные атрибуты или словари для доступа к данным.

3. **Отсутствие логирования:**
   В коде отсутствует логирование, что затрудняет отладку и мониторинг работы приложения.

   **Исправление:**
   Добавить логирование для ключевых операций и исключений.

4. **Неправильное использование `extra_param` в `StorageKey`:**
   В функции `changed_role` используется `extra_param="error"` в `StorageKey`, что может привести к неожиданному поведению.

   **Исправление:**
   Удалить `extra_param="error"` из `StorageKey`.

Пример исправленного кода с учетом этих замечаний:

```python
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message, CallbackQuery
from database.timers_deadline import insert_deadline_timer, delete_deadline_timer, get_timer_value
from lexicon.lexicon_ru import lexicon
from states.admins import AdminsStates
from keyboards.select_role import select_role_keyboard
import database.commands as db
from states.game import GameStates

logging.basicConfig(level=logging.ERROR)

async def changing_role(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(text=lexicon['changing_role'])
    await state.set_state(AdminsStates.ID)

# Для reply menu клавиатуры
async def handle_change_role_reply(message: Message, state: FSMContext):
    # Отправляет сообщение о начале процесса смены роли и переводит бота в состояние ожидания ID пользователя
    await message.answer(text=lexicon['changing_role'])
    await state.set_state(AdminsStates.ID)

async def select_role(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        user = await db.get_users_by_id(user_id)
        if user:
            await state.update_data(user_id=user_id)
            await message.answer(text=lexicon['select_role'], reply_markup=await select_role_keyboard())
            await state.set_state(None)
        else:
            await message.answer(text=lexicon['err_select_role'])
    except ValueError:
        await message.answer(text="Пожалуйста, введите корректный ID пользователя.")
    except Exception as e:
        logging.error(f"Error in select_role: {e}")
        await message.answer(text=lexicon['err_select_role'])

async def changed_role(callback: CallbackQuery, state: FSMContext):
    try:
        await callback.answer()
        data = await state.get_data()
        clb_data = callback.data
        user_role = await db.get_user_role(data['user_id'])  # Получаем текущую роль пользователя
        user = await db.get_users_by_id(data["user_id"])
        if clb_data in ["Судья", "Проверяющий", "Исполнитель", 'исключить', 'Админ'] and user[10]:
            await callback.message.edit_text(text=lexicon['err_user_in_game' if clb_data != 'исключить' else 'err_user_exclude_in_game'].format(data['user_id']))
        elif user_role == clb_data and (user_role in [None, ''] and clb_data not in ['Админ', 'Исполнитель', 'Судья',
                                                                                  'Проверяющий']):  # Проверяем, совпадает ли новая роль с текущей
            text = lexicon['role_exists'].format(data['user_id'], user_role) if user_role else \
                lexicon['role_exists_exclude'].format(data['user_id'])
            await callback.message.edit_text(text=text)
        else:
            await db.change_role(data['user_id'], clb_data)
            # Формируем текст сообщения в зависимости от значения clb_data (обычная смена роли или исключение)
            text = (lexicon['changed_role'].replace("{}", str(data['user_id']), 1).replace("{}", callback.data, 1)
                    if clb_data != 'исключить' else lexicon['exclude_role'].replace("{}", str(data['user_id'])))
            await callback.message.edit_text(text=text)
            if clb_data == "Судья":
                await db.add_jud(data["user_id"])
                await callback.bot.send_message(chat_id=data['user_id'], text=lexicon['set_judge_role'])  # noqa
            elif clb_data == "Проверяющий":
                await db.add_ins(data["user_id"])
                await callback.bot.send_message(chat_id=data['user_id'], text=lexicon['set_inspector_role'])  # noqa
            elif clb_data == "Исполнитель":
                user = await db.get_users_by_id(data["user_id"])
                time_delta = await get_timer_value("TZ")
                deadline_time = datetime.now() + timedelta(hours=time_delta)
                formatted_deadline_time = deadline_time.strftime("%d-%m-%Y %H:%M")
                await callback.bot.send_message(chat_id=data['user_id'], text=lexicon['set_executor_role'].format(user[3],
                                                                                                                  formatted_deadline_time))  # noqa
                await asyncio.sleep(1)
                # Исправлена отправка сообщения Исполнителю
                await callback.bot.send_message(user[0], text=lexicon['report_ts'].format(user[3]))
                await insert_deadline_timer(user[0], clb_data, time_delta, "tz")
                # Исправлена установка состояния Исполнителю
                # Создание ключа для пользователя
                user_key = StorageKey(user_id=user[0], chat_id=user[0], bot_id=callback.bot.id)
                # Инициализация FSMContext с этим ключом
                user_state = FSMContext(storage=state.storage, key=user_key)
                await user_state.update_data()  # обновить дату для пользователя
                # Установка состояния GameStates.TS для Исполнителя
                await user_state.set_state(GameStates.TS)

            # Добавляем обработку для исключения
            elif clb_data == 'исключить':
                # Удаляем все таймеры, связанные с пользователем
                await delete_deadline_timer(data['user_id'])
                await db.change_role(data['user_id'], "")
                await db.change_in_game(data['user_id'], 0)  # Убираем пользователя из игры
                await callback.bot.send_message(chat_id=data['user_id'], text=lexicon['exclude'])
                await state.clear()
    except Exception as e:
        logging.error(f"Error in changed_role: {e}")
```

Этот код включает обработку исключений и логирование, что улучшит его надежность и упростит отладку.

# REVIEW OF ADMINS FILE
В коде есть несколько потенциальных ошибок и проблем, которые могут привести к некорректной работе или исключениям. Вот основные из них:

1. **Отсутствие обработки ошибок при асинхронных вызовах:**
   Во многих местах кода отсутствует обработка возможных исключений при асинхронных вызовах к базе данных или отправке сообщений. Например:
   ```python
   game = await db.get_game_by_id(game_id)
   ```
   **Исправление:**
   Добавить обработку исключений для асинхронных вызовов.

2. **Использование индексов для доступа к элементам кортежа:**
   В нескольких местах используются индексы для доступа к элементам кортежа (например, `game[2]`, `user[1]`). Это снижает читаемость кода и может привести к ошибкам, если структура данных изменится.

   **Исправление:**
   Использовать именованные атрибуты или словари для доступа к данным.

3. **Отсутствие логирования:**
   В коде отсутствует логирование, что затрудняет отладку и мониторинг работы приложения.

   **Исправление:**
   Добавить логирование для ключевых операций и исключений.

4. **Неправильное использование `bot.send_document`:**
   В функции `handle_export_users` используется синхронный вызов `bot.send_document`, а должен быть асинхронным.

   **Исправление:**
   Использовать асинхронный вызов `await bot.send_document`.

Пример исправленного кода с учетом этих замечаний:

```python
import os
import logging
from aiogram.types import CallbackQuery, FSInputFile
from config.bot_config import bot
from lexicon.lexicon_ru import lexicon
from keyboards.admin_solve import admin_solve_keyboard
from keyboards.ins_report import ins_start_keyboard
import database.commands as db
from database.timers_deadline import insert_deadline_timer, get_timer_value

logging.basicConfig(level=logging.ERROR)

async def get_good_solve(callback: CallbackQuery):
    try:
        await callback.answer()
        game_id = int(callback.data.rsplit("-")[-1])
        game = await db.get_game_by_id(game_id)
        time_delta = await get_timer_value("Default")
        await bot.send_message(chat_id=game[2], text=lexicon["report_exc"].format(game[6], game[7], time_delta),
                               reply_markup=await ins_start_keyboard(game[1], game_id))
        # Добавление таймера для проверяющего на рассмотрение ТЗ
        await insert_deadline_timer(game[2], "Проверяющий", time_delta, "tz")
        await callback.message.edit_text(text=lexicon['good_solve'], reply_markup=None)
    except Exception as e:
        logging.error(f"Error in get_good_solve: {e}")

async def get_bad_solve(callback: CallbackQuery):
    try:
        await callback.answer()
        game_id = int(callback.data.rsplit("-")[-1])
        game = await db.get_game_by_id(game_id)
        user = await db.get_users_by_id(game[1])
        await callback.message.edit_text(text=lexicon['bad_solve'].format(user[1]),
                                         reply_markup=await admin_solve_keyboard(game_id, 0))
    except Exception as e:
        logging.error(f"Error in get_bad_solve: {e}")

async def handle_export_users(callback_query: CallbackQuery):
    try:
        file_path = './exports' # Путь для сохранения файлов экспорта
        os.makedirs(file_path, exist_ok=True)
        # Экспортирует данные из таблицы "users" в файлы форматов CSV и Excel.
        await db.export_users_to_csv_and_excel(file_path)

        # Создание и отправка CSV файла пользователю
        csv_file = FSInputFile(f"{file_path}/users.csv", filename='users_data.csv')
        await bot.send_document(chat_id=callback_query.from_user.id, document=csv_file)

        # Создание и отправка Excel файла пользователю
        excel_file = FSInputFile(f"{file_path}/users.xlsx", filename='users_data.xlsx')
        await bot.send_document(chat_id=callback_query.from_user.id, document=excel_file)
    except Exception as e:
        logging.error(f"Error in handle_export_users: {e}")

async def handle_export_all_tables(callback_query: CallbackQuery):
    try:
        file_path = './exports/all_tables' # Путь для сохранения файлов экспорта
        await db.export_all_tables_to_csv_and_excel(file_path)  # Экспорт данных из всех таблиц
        # Отправка всех файлов
        for table in ["games", "args", "stats_task", "stats_judge", "stats_inspector", "stats_executor", "stats_player", "overdue_count", "timer_deadline", 'timer_values']:
            # Создание и отправка CSV файла для каждой таблицы
            csv_file = FSInputFile(f"{file_path}/{table}.csv", filename=f"{table}.csv")
            await bot.send_document(chat_id=callback_query.from_user.id, document=csv_file)
            # Создание и отправка Excel файла для каждой таблицы
            excel_file = FSInputFile(f"{file_path}/{table}.xlsx", filename=f"{table}.xlsx")
            await bot.send_document(chat_id=callback_query.from_user.id, document=excel_file)
    except Exception as e:
        logging.error(f"Error in handle_export_all_tables: {e}")
```

Этот код включает обработку исключений и логирование, что улучшит его надежность и упростит отладку.
