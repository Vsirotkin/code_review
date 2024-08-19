import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from datetime import datetime, timedelta
from database.commands import (
    get_users_by_id,
    find_free_user,
    change_in_game,
    get_last_game_id_by_user_id,
    get_game_by_id,
    update_role_in_game,
    get_arg,
    update_stats,
)
from database.timers_deadline import (
    get_deadline_users,
    get_timer_value,
    delete_deadline_timer,
    increment_overdue_count,
    insert_deadline_timer,
)
from lexicon.lexicon_ru import lexicon
from states.game import GameStates
from keyboards.ins_report import ins_start_keyboard
from keyboards.argument import judge_argument
from keyboards.start_keyboard import start_keyboard


# Функция для назначения нового исполнителя
async def appointment_new_executor(
    bot: Bot,
    dp: Dispatcher,
    old_user_id: int,
    new_user_id: int,
    role: str,
    old_user_info: list,
) -> None:
    try:
        # Если новый исполнитель не является старым
        if new_user_id != old_user_id:
            await bot.send_message(
                chat_id=old_user_id,
                text=lexicon["start_else"].format(old_user_info[3]),
                reply_markup=await start_keyboard(role),
            )
        user_data = await get_users_by_id(new_user_id)
        time_delta = await get_timer_value("TZ")
        deadline_time = datetime.now() + timedelta(hours=time_delta)
        formatted_deadline_time = deadline_time.strftime("%d-%m-%Y %H:%M")
        await bot.send_message(
            new_user_id,
            text=lexicon["start_game"].format(user_data[3], formatted_deadline_time),
        )
        await asyncio.sleep(1)
        await bot.send_message(
            new_user_id, text=lexicon["report_ts"].format(user_data[3])
        )
        await insert_deadline_timer(new_user_id, role, time_delta, "tz")
        # Создание ключа для пользователя
        user_key = StorageKey(user_id=new_user_id, chat_id=new_user_id, bot_id=bot.id)
        # Инициализация FSMContext с этим ключом
        user_state = FSMContext(storage=dp.fsm.storage, key=user_key)
        await user_state.update_data()  # обновить дату для пользователя
        # Установка состояния GameStates.TS для Исполнителя
        await user_state.set_state(GameStates.TS)
    except Exception as e:
        logging.error(f"Error in appointment_new_executor: {e}")


# Функция для назначения нового проверяющего
async def appointment_new_inspector(
    bot: Bot, old_user_id: int, new_user_id: int, role: str
) -> None:
    try:
        # Получаем текущую игру в которой участвует Проверяющий
        game_id = await get_last_game_id_by_user_id(old_user_id)
        # Назначение нового игрока Проверяющим
        await update_role_in_game(game_id, "inspector", new_user_id)
        # Получение игры в которой участвовал Проверяющий
        game = await get_game_by_id(game_id)
        time_delta = await get_timer_value("Default")
        await bot.send_message(
            chat_id=game[2],
            text=lexicon["report_exc"].format(game[6], game[7], time_delta),
            reply_markup=await ins_start_keyboard(game[1], game_id),
        )
        # Добавление таймера для проверяющего на рассмотрение ТЗ
        await insert_deadline_timer(game[2], role, time_delta, "tz")
    except Exception as e:
        logging.error(f"Error in appointment_new_inspector: {e}")


# Функция для назначения нового судьи
async def appointment_new_judge(
    bot: Bot, old_user_id: int, new_user_id: int, role: str
) -> None:
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
        text = lexicon["judge_start"].format(
            judge[3],
            f"{executor[2]} {executor[3]} {executor[4]}",
            f"{inspector[2]} {inspector[3]} {inspector[4]}",
            time_delta,
        )
        await bot.send_message(new_user_id, text=text)
        # Установка таймера дедлайна на принятие новым судьей решения
        await insert_deadline_timer(new_user_id, "Судья", time_delta, "solve")
        text = lexicon["judge_task"].format(game[5], game[6], game[8], args[2], args[3])
        keyboard_judge = await judge_argument(game_id)
        await bot.send_message(chat_id=game[3], text=text, reply_markup=keyboard_judge)
    except Exception as e:
        logging.error(f"Error in appointment_new_judge: {e}")


# Функция для очистки состояния пользователя
async def clear_status(user_id: int, bot: Bot, dp: Dispatcher) -> None:
    """Очистка состояния пользователя, при дедлайне"""
    try:
        user_key = StorageKey(user_id=user_id, chat_id=user_id, bot_id=bot.id)
        user_state = FSMContext(storage=dp.fsm.storage, key=user_key)
        await user_state.clear()
    except Exception as e:
        logging.error(f"Error in clear_status: {e}")


# Множество для отслеживания отправленных уведомлений
sent_notifications = set()


# Функция для проверки дедлайнов и отправки уведомлений
async def check_deadlines(bot: Bot, dp: Dispatcher) -> None:
    """Проверка дедлайнов и отправка уведомлений"""
    while True:
        try:
            now = datetime.now()
            now = now.replace(second=0, microsecond=0)
            deadlines = await get_deadline_users()
            for deadline in deadlines:
                user_id, role, deadline_time, stage = deadline
                deadline_time = datetime.strptime(deadline_time, "%Y-%m-%d %H:%M:%S.%f")
                deadline_time = deadline_time.replace(second=0, microsecond=0)
                # добавлаем ключи
                notification_key_2h = (user_id, role, deadline_time, stage, "2h")
                notification_key_1h = (user_id, role, deadline_time, stage, "1h")
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
                            text = lexicon["delay_tz"]
                            await bot.send_message(chat_id=user_id, text=text)
                            if role == "Испольнитель":
                                # Очищаем его состояние
                                await clear_status(user_id, bot, dp)
                                # Находим нового исполнителя
                                new_user = await find_free_user(role)
                                # Назначаем нового исполнителя
                                await appointment_new_executor(
                                    bot, dp, user_id, new_user, role, user_info
                                )
                            if role == "Проверяющий":
                                # Очищаем его состояние
                                await clear_status(user_id, bot, dp)
                                # Находим нового проверяющего
                                new_user = await find_free_user(role)
                                # Назначаем нового инспектора
                                await appointment_new_inspector(
                                    bot, user_id, new_user, role
                                )
                        # В случае при просрочке судьи
                        case "solve":
                            await bot.send_message(chat_id=user_id, text=text)
                            text = lexicon["delay_solve"]
                            # Находим нового Судью
                            new_user = await find_free_user(role)
                            # Назначаем нового инспектора
                            await appointment_new_judge(bot, user_id, new_user, role)
                        case _:
                            text = lexicon["delay_answer"]
                            # Получаем текущую игру в которой участвует игроки
                            game_id = await get_last_game_id_by_user_id(user_id)
                            # Получение данных о игроках в игре
                            game = await get_game_by_id(game_id)
                            wins_ins = 0
                            # Отравляем уведомления о завершении игры
                            if role == "Исполнитель":
                                await bot.send_message(
                                    chat_id=game[2],
                                    text=f"{lexicon['win']}\n{lexicon['win_deadline_exe']}",
                                )
                                await bot.send_message(
                                    chat_id=game[1],
                                    text=f"{lexicon['loose']}\n{lexicon['delay_answer']}",
                                )
                                await bot.send_message(
                                    chat_id=game[1],
                                    text=lexicon["start_else"].format(user_info[3]),
                                    reply_markup=await start_keyboard(role),
                                )
                            else:
                                wins_ins = 1
                                await bot.send_message(
                                    chat_id=game[1],
                                    text=f"{lexicon['win']}\n{lexicon['win_deadline_ins']}",
                                )
                                await bot.send_message(
                                    chat_id=game[2],
                                    text=f"{lexicon['loose']}\n{lexicon['delay_answer']}",
                                )
                            # Обновление статистики игры
                            await update_stats(game, 0, wins_ins, overdue_role=role)
                            await clear_status(game[1], bot, dp)
                            await clear_status(game[2], bot, dp)
                    # Добавление в БД просрочки пользователя
                    await increment_overdue_count(user_id)

                # Уведомления за 2 часа до дедлайна
                elif now >= deadline_time - timedelta(
                    hours=2
                ) and now < deadline_time - timedelta(hours=1):
                    if notification_key_2h not in sent_notifications:
                        await bot.send_message(
                            chat_id=user_id, text=lexicon["two_hour_left"]
                        )
                        sent_notifications.add(notification_key_2h)

                # Уведомления за 1 часа до дедлайна
                elif now >= deadline_time - timedelta(hours=1) and now < deadline_time:
                    if notification_key_1h not in sent_notifications:
                        await bot.send_message(
                            chat_id=user_id, text=lexicon["one_hour_left"]
                        )
                        sent_notifications.add(notification_key_1h)

            await asyncio.sleep(60)
        except Exception as e:
            logging.error(f"Error in check_deadlines: {e}")
