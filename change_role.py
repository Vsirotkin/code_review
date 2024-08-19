import asyncio
from datetime import datetime, timedelta
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message, CallbackQuery
from database.timers_deadline import (
    insert_deadline_timer,
    delete_deadline_timer,
    get_timer_value,
)
from lexicon.lexicon_ru import lexicon
from states.admins import AdminsStates
from keyboards.select_role import select_role_keyboard
import database.commands as db
from states.game import GameStates


# Функция для начала процесса смены роли
async def changing_role(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(text=lexicon["changing_role"])
    await state.set_state(AdminsStates.ID)


# Функция для обработки reply меню
async def handle_change_role_reply(message: Message, state: FSMContext):
    # Отправляет сообщение о начале процесса смены роли и переводит бота в состояние ожидания ID пользователя
    await message.answer(text=lexicon["changing_role"])
    await state.set_state(AdminsStates.ID)


# Функция для выбора роли
async def select_role(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        user = await db.get_users_by_id(user_id)
        if user:
            await state.update_data(user_id=user_id)
            await message.answer(
                text=lexicon["select_role"], reply_markup=await select_role_keyboard()
            )
            await state.set_state(None)
        else:
            await message.answer(text=lexicon["err_select_role"])
    except ValueError:
        await message.answer(text="Пожалуйста, введите корректный ID пользователя.")


# Функция для смены роли
async def changed_role(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    clb_data = callback.data
    user_role = await db.get_user_role(
        data["user_id"]
    )  # Получаем текущую роль пользователя
    user = await db.get_users_by_id(data["user_id"])
    if (
        clb_data in ["Судья", "Проверяющий", "Исполнитель", "исключить", "Админ"]
        and user[10]
    ):
        await callback.message.edit_text(
            text=lexicon[
                (
                    "err_user_in_game"
                    if clb_data != "исключить"
                    else "err_user_exclude_in_game"
                )
            ].format(data["user_id"])
        )
    elif user_role == clb_data and (
        user_role in [None, ""]
        and clb_data not in ["Админ", "Исполнитель", "Судья", "Проверяющий"]
    ):  # Проверяем, совпадает ли новая роль с текущей
        text = (
            lexicon["role_exists"].format(data["user_id"], user_role)
            if user_role
            else lexicon["role_exists_exclude"].format(data["user_id"])
        )
        await callback.message.edit_text(text=text)
    else:
        await db.change_role(data["user_id"], clb_data)
        # Формируем текст сообщения в зависимости от значения clb_data (обычная смена роли или исключение)
        text = (
            lexicon["changed_role"]
            .replace("{}", str(data["user_id"]), 1)
            .replace("{}", callback.data, 1)
            if clb_data != "исключить"
            else lexicon["exclude_role"].replace("{}", str(data["user_id"]))
        )
        await callback.message.edit_text(text=text)
        if clb_data == "Судья":
            await db.add_jud(data["user_id"])
            await callback.bot.send_message(
                chat_id=data["user_id"], text=lexicon["set_judge_role"]
            )  # noqa
        elif clb_data == "Проверяющий":
            await db.add_ins(data["user_id"])
            await callback.bot.send_message(
                chat_id=data["user_id"], text=lexicon["set_inspector_role"]
            )  # noqa
        elif clb_data == "Исполнитель":
            user = await db.get_users_by_id(data["user_id"])
            time_delta = await get_timer_value("TZ")
            deadline_time = datetime.now() + timedelta(hours=time_delta)
            formatted_deadline_time = deadline_time.strftime("%d-%m-%Y %H:%M")
            await callback.bot.send_message(
                chat_id=data["user_id"],
                text=lexicon["set_executor_role"].format(
                    user[3], formatted_deadline_time
                ),
            )  # noqa
            await asyncio.sleep(1)
            # Исправлена отправка сообщения Исполнителю
            await callback.bot.send_message(
                user[0], text=lexicon["report_ts"].format(user[3])
            )
            await insert_deadline_timer(user[0], clb_data, time_delta, "tz")
            # Исправлена установка состояния Исполнителю
            # Создание ключа для пользователя
            user_key = StorageKey(
                user_id=user[0],
                chat_id=user[0],
                bot_id=callback.bot.id,
                extra_param="error",
            )
            # Инициализация FSMContext с этим ключом
            user_state = FSMContext(storage=state.storage, key=user_key)
            await user_state.update_data()  # обновить дату для пользователя
            # Установка состояния GameStates.TS для Исполнителя
            await user_state.set_state(GameStates.TS)

        # Добавляем обработку для исключения
        elif clb_data == "исключить":
            # Удаляем все таймеры, связанные с пользователем
            await delete_deadline_timer(data["user_id"])
            await db.change_role(data["user_id"], "")
            await db.change_in_game(data["user_id"], 0)  # Убираем пользователя из игры
            await callback.bot.send_message(
                chat_id=data["user_id"], text=lexicon["exclude"]
            )
            await state.clear()
