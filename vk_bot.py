import asyncio
from vkbottle.bot import Bot, Message
from vkbottle import API
from openai import AsyncOpenAI
from curl_cffi import requests

# ============ ВАШИ ДАННЫЕ ============
VK_TOKEN = "vk1.a.eA7csyDA8qfr_wei3CWcbzDB_AR9OrWsXOCT3BhiBFzt0EPCT8NZnNWkbmEtKjhpxjZKosBIcJv8xci8krhps05FL00_I6MfJkc2_QxUajI82AQ8is038jZdZHCuUNvhlGFUFlYuNct-bqAUbtyzDoCUsN8_B4X3U9cOwfVVLuozVFr_0CRoMef__KTHb0IhADLN09HIfyBplev5zzcw2w"
VK_GROUP_ID = 242626238
AITUNNEL_KEY = "sk-aitunnel-qvg8RC1G8erIExHdAhtos3d4C4IHoAHS"
# =====================================

api = API(VK_TOKEN)
bot = Bot(api=api)

ai_client = AsyncOpenAI(api_key=AITUNNEL_KEY, base_url="https://api.aitunnel.ru/v1/")

async def extract_query(text: str) -> str:
    try:
        resp = await ai_client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "Выдели из текста только поисковый запрос. Убери слова 'найди', 'покажи', 'сколько стоит'. Верни только ключевые слова."},
                {"role": "user", "content": text}
            ],
            temperature=0.1,
        )
        return resp.choices[0].message.content.strip() or text
    except Exception as e:
        print(f"LLM ошибка: {e}")
        return text

async def search_wb(query: str):
    """Поиск на WB через curl_cffi (маскировка под Chrome)"""
    def _search():
        url = "https://search.wb.ru/exactmatch/ru/common/v5/search"
        params = {
            "appType": "1",
            "curr": "rub",
            "dest": "-1257786",
            "query": query,
            "resultset": "catalog",
            "spp": "30",
        }
        try:
            # impersonate="chrome" маскирует TLS-отпечаток под реальный Chrome
            response = requests.get(url, params=params, impersonate="chrome", timeout=15)
            if response.status_code != 200:
                print(f"WB HTTP ошибка: {response.status_code}")
                return None
            data = response.json()
            products = data.get("data", {}).get("products", [])
            return products[:5]
        except Exception as e:
            print(f"WB ошибка: {e}")
            return None

    return await asyncio.to_thread(_search)

@bot.on.message()
async def handle_message(message: Message):
    user_text = message.text.strip()
    if not user_text: return

    await message.answer("🧠 Анализирую запрос...")
    query = await extract_query(user_text)
    await message.answer(f"🔍 Ищу на WB: {query}\n⏳ Секунду...")

    products = await search_wb(query)
    if not products:
        await message.answer("Не удалось получить товары. Попробуйте переформулировать запрос.")
        return

    for p in products:
        name = p.get("name", "Без названия")
        brand = p.get("brand", "")
        price = p.get("salePriceU", 0) / 100
        rating = p.get("reviewRating", 0)
        prod_id = p.get("id")

        text = (
            f"📦 {brand} {name}\n"
            f"💰 Цена: {price:.0f} ₽\n"
            f"⭐ Рейтинг: {rating}\n"
            f"🔗 https://www.wildberries.ru/catalog/{prod_id}/detail.aspx"
        )
        await message.answer(text)
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    print("VK бот (curl_cffi) запущен...")
    bot.run_forever()
