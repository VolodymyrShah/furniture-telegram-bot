import os
import psycopg2
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DATABASE_URL = os.environ.get("DATABASE_URL")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cursor = conn.cursor()

ALLOWED_USERS = []  # сюди додаси Telegram ID

class NewOrder(StatesGroup):
    order_number = State()
    client_name = State()
    phone = State()
    furniture_type = State()
    total_price = State()
    advance = State()
    cost = State()

@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer(
        "🪑 Меблевий бот (EUR €)\n\n"
        "/new_order — нове замовлення\n"
        "/month_profit — прибуток за місяць"
    )

@dp.message_handler(commands=["new_order"])
async def new_order(msg: types.Message):
    await msg.answer("Введіть номер замовлення:")
    await NewOrder.order_number.set()

@dp.message_handler(state=NewOrder.order_number)
async def step1(msg: types.Message, state: FSMContext):
    await state.update_data(order_number=msg.text)
    await msg.answer("Імʼя клієнта:")
    await NewOrder.client_name.set()

@dp.message_handler(state=NewOrder.client_name)
async def step2(msg: types.Message, state: FSMContext):
    await state.update_data(client_name=msg.text)
    await msg.answer("Телефон клієнта:")
    await NewOrder.phone.set()

@dp.message_handler(state=NewOrder.phone)
async def step3(msg: types.Message, state: FSMContext):
    await state.update_data(phone=msg.text)
    await msg.answer("Тип меблів:")
    await NewOrder.furniture_type.set()

@dp.message_handler(state=NewOrder.furniture_type)
async def step4(msg: types.Message, state: FSMContext):
    await state.update_data(furniture_type=msg.text)
    await msg.answer("Загальна сума (€):")
    await NewOrder.total_price.set()

@dp.message_handler(state=NewOrder.total_price)
async def step5(msg: types.Message, state: FSMContext):
    await state.update_data(total_price=float(msg.text))
    await msg.answer("Аванс (€):")
    await NewOrder.advance.set()

@dp.message_handler(state=NewOrder.advance)
async def step6(msg: types.Message, state: FSMContext):
    await state.update_data(advance=float(msg.text))
    await msg.answer("Собівартість (€):")
    await NewOrder.cost.set()

@dp.message_handler(state=NewOrder.cost)
async def finish(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    cost = float(msg.text)
    profit = data["total_price"] - cost

    cursor.execute(
        "INSERT INTO clients (name, phone) VALUES (%s, %s) RETURNING id",
        (data["client_name"], data["phone"])
    )
    client_id = cursor.fetchone()[0]

    cursor.execute(
        """INSERT INTO orders
        (order_number, client_id, furniture_type, date_created,
         total_price, advance, cost, profit, status)
        VALUES (%s,%s,%s,CURRENT_DATE,%s,%s,%s,%s,'Прийнято')""",
        (
            data["order_number"],
            client_id,
            data["furniture_type"],
            data["total_price"],
            data["advance"],
            cost,
            profit
        )
    )

    conn.commit()
    await msg.answer(f"✅ Замовлення збережено\nПрибуток: {profit} €")
    await state.finish()

if __name__ == "__main__":
    executor.start_polling(dp)

