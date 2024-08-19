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


async def start_game(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
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


async def get_report_with_error(message: Message, state: FSMContext):
    try:
        document_id = message.text
    except:
        await message.answer(text=lexicon['document_error'])
        return
    user = await db.get_users_by_id(message.chat.id)
    await state.update_data(with_error=document_id)
    await message.answer(text=lexicon['report_without_error'].format(user[3]))
    await state.set_state(GameStates.WITHOUT_ERROR)


async def get_report_without_error(message: Message, state: FSMContext):
    try:
        document_id = message.text
    except:
        await message.answer(text=lexicon['document_error'])
        return
    user = await db.get_users_by_id(message.chat.id)
    await state.update_data(without_error=document_id)
    await message.answer(text=lexicon['all_errors'].format(user[3]))
    await state.set_state(GameStates.ERRORS)


async def get_all_errors(message: Message, state: FSMContext):
    user = await db.get_users_by_id(message.chat.id)
    await state.update_data(all_errors=message.text)
    await message.answer(text=lexicon['count_errors'].format(user[3]), parse_mode=ParseMode.HTML)
    await state.set_state(GameStates.COUNT)


async def get_count_errors(message: Message, state: FSMContext):
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

