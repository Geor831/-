import asyncio
from vkbottle.bot import Bot, Message
from vkbottle import API
from openai import AsyncOpenAI
from duckduckgo_search import DDGS

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

async def search_web(query: str):
    """Поиск в интернете через DuckDuckGo"""
    def _search():
        try:
            # Ищем строго на сайте Wildberries
            search_query = f"{query} site:wildberries.ru"
            
            with DDGS() as ddgs:
                results = list(ddgs.text(search_query, max_results=5))
                return results
        except Exception as e:
            print(f"Ошибка поиска: {e}")
            return None

    return await asyncio.to_thread(_search)

@bot.on.message()
async def handle_message(message: Message):
    user_text = message.text.strip()
    if not user_text: return

    await message.answer("🧠 Анализирую запрос...")
    query = await extract_query(user_text)
    await message.answer(f"🔍 Ищу в интернете: {query}\n⏳ Секунду...")

    results = await search_web(query)
    if not results:
        await message.answer("Ничего не нашёл. Попробуйте переформулировать запрос.")
        return

    for r in results:
        title = r.get("title", "Без названия")
        url = r.get("href", "")
        body = r.get("body", "Нет описания")
        
        if len(body) > 150:
            body = body[:150] + "..."
            
        text = (
            f"📦 {title}\n"
            f"📝 {body}\n"
            f"🔗 {url}"
        )
        await message.answer(text)
        await asyncio.sleep(0.5)

if __name__ == "__main__":
    print("VK бот (Bothost) запущен...")
    bot.run_forever()
