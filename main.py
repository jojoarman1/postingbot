import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramAPIError

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота
API_TOKEN = '8151740706:AAEENzJm45ussvfgt0pAv7BUHbrxV-HLX_E'
# ID разрешенного пользователя
ALLOWED_USER_ID = 1042568370  # Замените на реальный ID пользователя

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Хранилище каналов для каждого пользователя
channels = {}  # {user_id: {channel_link: channel_id}}


class PostStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_image = State()
    waiting_for_button = State()
    waiting_for_button_text = State()
    waiting_for_button_type = State()
    waiting_for_button_url = State()
    waiting_for_alert_text = State()
    waiting_for_channel = State()
    waiting_for_channel_link = State()


def check_user_access(user_id: int) -> bool:
    return user_id == ALLOWED_USER_ID


async def main_menu(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить пост", callback_data="add_post")],
        [InlineKeyboardButton(text="Добавить паблик", callback_data="add_channel")],
        [InlineKeyboardButton(text="Мои паблики", callback_data="my_channels")]
    ])
    await message.answer("Главное меню. Выберите действие:", reply_markup=keyboard)


@dp.message(Command(commands=['start', 'help']))
async def send_welcome(message: types.Message):
    if not check_user_access(message.from_user.id):
        await message.answer("Извините, у вас нет доступа к этому боту.")
        return
    await main_menu(message)


@dp.callback_query(F.data == "add_post")
async def add_post(callback_query: types.CallbackQuery, state: FSMContext):
    if not check_user_access(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет доступа к этому боту.", show_alert=True)
        return
    await state.set_state(PostStates.waiting_for_text)
    await state.update_data(buttons=[])  # Initialize empty list for buttons
    await callback_query.message.edit_text("Напишите текст поста:")


@dp.message(PostStates.waiting_for_text)
async def process_post_text(message: types.Message, state: FSMContext):
    if not check_user_access(message.from_user.id):
        return
    await state.update_data(post_text=message.text)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить изображение", callback_data="add_image")],
        [InlineKeyboardButton(text="Пропустить", callback_data="skip_image")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
    ])
    await message.answer("Хотите добавить изображение к посту?", reply_markup=keyboard)


@dp.callback_query(F.data == "add_image")
async def request_image(callback_query: types.CallbackQuery, state: FSMContext):
    if not check_user_access(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет доступа к этому боту.", show_alert=True)
        return
    await state.set_state(PostStates.waiting_for_image)
    await callback_query.message.edit_text("Отправьте изображение:")


@dp.message(PostStates.waiting_for_image, F.content_type == types.ContentType.PHOTO)
async def process_image(message: types.Message, state: FSMContext):
    if not check_user_access(message.from_user.id):
        return
    await state.update_data(image=message.photo[-1].file_id)
    await add_button(message, state)


@dp.callback_query(F.data == "skip_image")
async def skip_image(callback_query: types.CallbackQuery, state: FSMContext):
    if not check_user_access(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет доступа к этому боту.", show_alert=True)
        return
    await add_button(callback_query.message, state)


async def add_button(message: types.Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить кнопку", callback_data="add_button")],
        [InlineKeyboardButton(text="Завершить", callback_data="finish_post")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
    ])
    await message.answer("Хотите добавить инлайн кнопку?", reply_markup=keyboard)


@dp.callback_query(F.data == "add_button")
async def process_button_choice(callback_query: types.CallbackQuery, state: FSMContext):
    if not check_user_access(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет доступа к этому боту.", show_alert=True)
        return
    await state.set_state(PostStates.waiting_for_button_text)
    await callback_query.message.edit_text("Введите текст для кнопки:")


@dp.message(PostStates.waiting_for_button_text)
async def process_button_text(message: types.Message, state: FSMContext):
    if not check_user_access(message.from_user.id):
        return
    await state.update_data(current_button_text=message.text)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Ссылка", callback_data="button_url")],
        [InlineKeyboardButton(text="Алерт", callback_data="button_alert")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_add_button")]
    ])
    await state.set_state(PostStates.waiting_for_button_type)
    await message.answer("Выберите тип кнопки:", reply_markup=keyboard)


@dp.callback_query(F.data.in_(["button_url", "button_alert"]))
async def process_button_type(callback_query: types.CallbackQuery, state: FSMContext):
    if not check_user_access(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет доступа к этому боту.", show_alert=True)
        return
    button_type = callback_query.data
    await state.update_data(current_button_type=button_type)
    if button_type == "button_url":
        await state.set_state(PostStates.waiting_for_button_url)
        await callback_query.message.edit_text("Введите URL для кнопки:")
    else:
        await state.set_state(PostStates.waiting_for_alert_text)
        await callback_query.message.edit_text("Введите текст для алерта:")


@dp.message(PostStates.waiting_for_button_url)
async def process_button_url(message: types.Message, state: FSMContext):
    if not check_user_access(message.from_user.id):
        return
    user_data = await state.get_data()
    buttons = user_data.get('buttons', [])
    buttons.append({
        'text': user_data['current_button_text'],
        'type': 'url',
        'url': message.text
    })
    await state.update_data(buttons=buttons)
    await add_button(message, state)


@dp.message(PostStates.waiting_for_alert_text)
async def process_alert_text(message: types.Message, state: FSMContext):
    if not check_user_access(message.from_user.id):
        return
    user_data = await state.get_data()
    buttons = user_data.get('buttons', [])
    buttons.append({
        'text': user_data['current_button_text'],
        'type': 'alert',
        'alert_text': message.text
    })
    await state.update_data(buttons=buttons)
    await add_button(message, state)


@dp.callback_query(F.data == "finish_post")
async def finish_post(callback_query: types.CallbackQuery, state: FSMContext):
    if not check_user_access(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет доступа к этому боту.", show_alert=True)
        return
    await choose_channel(callback_query.message, state)


async def choose_channel(message: types.Message, state: FSMContext):
    user_id = str(message.chat.id)
    logging.info(f"Entering choose_channel for user {user_id}")
    logging.info(f"All channels: {channels}")
    user_channels = channels.get(user_id, {})
    if not user_channels:
        await message.answer("Нет доступных пабликов. Сначала добавьте паблик.")
        await state.clear()
        await main_menu(message)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=channel, callback_data=f"channel_{channel}") for channel in user_channels],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_add_button")]
    ])

    await state.set_state(PostStates.waiting_for_channel)
    await message.answer("Выберите паблик для публикации:", reply_markup=keyboard)


@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback_query: types.CallbackQuery, state: FSMContext):
    if not check_user_access(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет доступа к этому боту.", show_alert=True)
        return
    await state.clear()
    await main_menu(callback_query.message)


@dp.callback_query(F.data == "back_to_add_button")
async def back_to_add_button(callback_query: types.CallbackQuery, state: FSMContext):
    if not check_user_access(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет доступа к этому боту.", show_alert=True)
        return
    await add_button(callback_query.message, state)


@dp.callback_query(PostStates.waiting_for_channel)
async def process_channel_choice(callback_query: types.CallbackQuery, state: FSMContext):
    if not check_user_access(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет доступа к этому боту.", show_alert=True)
        return
    user_id = str(callback_query.message.chat.id)
    user_channels = channels.get(user_id, {})
    user_data = await state.get_data()
    post_text = user_data['post_text']
    image = user_data.get('image')
    buttons = user_data.get('buttons', [])

    keyboard = []
    for button in buttons:
        if button['type'] == 'url':
            url = button['url']
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            keyboard.append([InlineKeyboardButton(text=button['text'], url=url)])
        else:
            keyboard.append([InlineKeyboardButton(text=button['text'], callback_data=f"alert_{button['alert_text']}")])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard) if keyboard else None

    try:
        if callback_query.data == "all_channels":
            for channel in user_channels.values():
                if image:
                    await bot.send_photo(chat_id=channel, photo=image, caption=post_text, reply_markup=reply_markup)
                else:
                    await bot.send_message(chat_id=channel, text=post_text, reply_markup=reply_markup)
        elif callback_query.data.startswith("channel_"):
            channel = callback_query.data.split("_")[1]
            channel_id = user_channels[channel]
            if image:
                await bot.send_photo(chat_id=channel_id, photo=image, caption=post_text, reply_markup=reply_markup)
            else:
                await bot.send_message(chat_id=channel_id, text=post_text, reply_markup=reply_markup)

        await callback_query.message.edit_text("Пост опубликован!")
    except Exception as e:
        await callback_query.message.edit_text(f"Ошибка при публикации поста: {str(e)}")
    finally:
        await state.clear()
        await main_menu(callback_query.message)


@dp.callback_query(F.data == "add_channel")
async def add_channel(callback_query: types.CallbackQuery, state: FSMContext):
    if not check_user_access(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет доступа к этому боту.", show_alert=True)
        return
    user_id = str(callback_query.message.chat.id)
    if user_id in channels and channels[user_id]:
        await callback_query.message.edit_text("У вас уже есть добавленные каналы. Хотите добавить еще один?")
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data="add_another_channel")],
            [InlineKeyboardButton(text="Нет, вернуться в главное меню", callback_data="back_to_main")]
        ])
        await callback_query.message.edit_reply_markup(reply_markup=keyboard)
    else:
        await state.set_state(PostStates.waiting_for_channel_link)
        await callback_query.message.edit_text("Отправьте публичную ссылку на канал (например, https://t.me/username):")


@dp.message(PostStates.waiting_for_channel_link)
async def process_channel_link(message: types.Message, state: FSMContext):
    if not check_user_access(message.from_user.id):
        return
    try:
        user_id = str(message.chat.id)
        channel_link = message.text
        logging.info(f"Attempting to add channel {channel_link} for user {user_id}")
        if channel_link.startswith('https://t.me/'):
            channel_link = '@' + channel_link.split('/')[-1]
        elif not channel_link.startswith('@'):
            channel_link = '@' + channel_link

        chat = await bot.get_chat(channel_link)
        bot_member = await bot.get_chat_member(chat.id, (await bot.me()).id)

        if not isinstance(bot_member, types.ChatMemberAdministrator):
            await message.answer("Ошибка: бот должен быть администратором канала!")
            return

        channel_id = chat.id
        if str(user_id) not in channels:
            channels[str(user_id)] = {}
        channels[str(user_id)][channel_link] = channel_id
        logging.info(f"Channel {channel_link} successfully added for user {user_id}")
        logging.info(f"Current channels for user {user_id}: {channels.get(user_id, {})}")
        await message.answer(f"Канал {channel_link} успешно добавлен!")

    except TelegramAPIError as e:
        await message.answer(
            "Ошибка при добавлении канала. Убедитесь что:\n"
            "1. Бот добавлен в канал как администратор\n"
            "2. Указан правильный username канала\n"
            f"Ошибка: {str(e)}"
        )
    finally:
        await state.clear()
        await main_menu(message)


@dp.callback_query(F.data == "my_channels")
async def show_my_channels(callback_query: types.CallbackQuery):
    if not check_user_access(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет доступа к этому боту.", show_alert=True)
        return
    user_id = str(callback_query.message.chat.id)
    user_channels = channels.get(user_id, {})
    if not user_channels:
        await callback_query.message.edit_text("У вас нет добавленных каналов.")
    else:
        channels_list = "\n".join(user_channels.keys())
        await callback_query.message.edit_text(f"Ваши каналы:\n{channels_list}")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Назад в главное меню", callback_data="back_to_main")]
    ])
    await callback_query.message.edit_reply_markup(reply_markup=keyboard)


@dp.callback_query(F.data.startswith("alert_"))
async def process_alert(callback_query: types.CallbackQuery):
    if not check_user_access(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет доступа к этому боту.", show_alert=True)
        return
    alert_text = callback_query.data.split("_", 1)[1]
    await callback_query.answer(text=alert_text, show_alert=True)


@dp.callback_query(F.data == "add_another_channel")
async def add_another_channel(callback_query: types.CallbackQuery, state: FSMContext):
    if not check_user_access(callback_query.from_user.id):
        await callback_query.answer("Извините, у вас нет доступа к этому боту.", show_alert=True)
        return
    await state.set_state(PostStates.waiting_for_channel_link)
    await callback_query.message.edit_text("Отправьте публичную ссылку на канал (например, https://t.me/username):")


async def main():
    global channels
    channels = {}

    # Удаление вебхука перед запуском long polling
    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())

