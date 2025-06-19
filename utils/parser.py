import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
from utils.storage import load_cache, save_cache

async def fetch_articles_from_site(query=None, lang="ru", limit=10):
      """Получение списка статей с сайта Kadrovik.uz"""
      start_time = time.time()
      base_url = "https://kadrovik.uz/" if lang == "ru" else "https://kadrovik.uz/uz/"
      url = base_url if not query else f"{base_url}search?q={query}"
      print(f"{datetime.now()}: Начало парсинга URL: {url}")
      
      try:
          headers = {
              "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
          }
          async with aiohttp.ClientSession() as session:
              async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=6)) as response:
                  response.raise_for_status()
                  text = await response.text()
                  soup = BeautifulSoup(text, "html.parser")

          articles = []
          posts_section = soup.select_one("section.posts-block ul.posts-list")
          if posts_section:
              for item in posts_section.select("li.post-card-wrapper")[:limit]:
                  article_link = item.select_one("a[href]")
                  if article_link:
                      title = item.select_one("h4.post-card__title")
                      date_elem = item.select_one("time.longread-post__time-published")
                      title_text = title.text.strip() if title else "Без заголовка"
                      date_text = date_elem["datetime"] if date_elem else datetime.now().isoformat()
                      link = article_link["href"]
                      if not link.startswith("http"):
                          link = base_url.rstrip("/") + "/" + link.lstrip("/")
                      
                      articles.append({
                          "title": title_text,
                          "content": "",  # Убираем вызов fetch_article_content
                          "date": date_text,
                          "emoji": "📰",
                          "url": link
                      })

          print(f"{datetime.now()}: Найдено статей перед срезом: {len(posts_section.select('li.post-card-wrapper')) if posts_section else 0}")
          print(f"{datetime.now()}: Возвращено статей после среза: {len(articles)}")
          
          if not articles:
              print(f"{datetime.now()}: Не удалось найти статьи по URL: {url}")
          print(f"{datetime.now()}: Парсинг завершен. Время: {time.time() - start_time:.2f} сек. Найдено статей: {len(articles)}")
          
          # Сохраняем в кэш
          cache = load_cache()
          cache_key = f"latest_{lang}" if not query else f"search_{query}_{lang}"
          cache[cache_key] = {
              "timestamp": datetime.now().isoformat(),
              "data": articles
          }
          save_cache(cache)
          return articles
      except Exception as e:
          print(f"{datetime.now()}: Ошибка при парсинге сайта: {e}. Время: {time.time() - start_time:.2f} сек")
          cache = load_cache()
          cache_key = f"latest_{lang}" if not query else f"search_{query}_{lang}"
          return cache.get(cache_key, {}).get("data", [])

async def fetch_article_content(url):
      """Парсер с правильными переносами строк после emoji и абзацев"""
      try:
          headers = {
              "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
          }
          
          async with aiohttp.ClientSession() as session:
              async with session.get(url, headers=headers, timeout=10) as response:
                  response.raise_for_status()
                  html = await response.text()
          
          soup = BeautifulSoup(html, 'html.parser')
          
          # 1. Заголовок и дата (без #)
          title = soup.find('h1').get_text(strip=True) if soup.find('h1') else "Без заголовка"
          date_elem = soup.find('time', {'class': 'longread-post__time-published'})
          date = date_elem['datetime'] if date_elem else ""
          
          # 2. Ищем контейнер с контентом
          content_block = soup.find('section', {'class': 'longread-block'}) or soup.find('body')
          
          if not content_block:
              return f"📰 {title}\n📅 {date}\n\nНе удалось найти контент."
          
          # 3. Собираем только <p> и <strong>
          elements = content_block.find_all(['p', 'strong'])
          result = []
          
          for element in elements:
              text = element.get_text(' ', strip=True)
              if text:
                  if element.name == 'strong':
                      result.append(f"\n \n🔹 {text}\n")  # Новый абзац для 🔹
                  else:
                      result.append(f"{text}")       # Новый абзац для обычного текста
          
          # 4. Объединяем и удаляем дубликаты
          content = ''.join(dict.fromkeys(result))
          
          return content if len(content) > 50 else "Не удалось извлечь текст."
      
      except Exception as e:
          print(f"Ошибка: {e}")
          return None

async def search_articles(query, lang):
      """Поиск статей по запросу"""
      cache = load_cache()
      cache_key = f"search_{query}_{lang}"
      
      # Проверяем кэш
      if cache_key in cache:
          entry = cache[cache_key]
          timestamp = entry.get("timestamp")
          if timestamp and (datetime.now() - datetime.fromisoformat(timestamp)) < timedelta(hours=24):
              print(f"{datetime.now()}: Используем кэшированные данные для запроса: {query}")
              return entry["data"]

      print(f"{datetime.now()}: Парсинг сайта для запроса: {query}")
      articles = await fetch_articles_from_site(query, lang)
      return articles

async def get_latest_articles(lang):
      """Получение последних статей"""
      cache = load_cache()
      cache_key = f"latest_{lang}"
      
      # Проверяем кэш
      if cache_key in cache:
          entry = cache[cache_key]
          timestamp = entry.get("timestamp")
          if timestamp and (datetime.now() - datetime.fromisoformat(timestamp)) < timedelta(hours=24):
              print(f"{datetime.now()}: Используем кэшированные данные для последних статей ({lang})")
              return entry["data"]

      print(f"{datetime.now()}: Парсинг сайта для последних статей ({lang})")
      articles = await fetch_articles_from_site(lang=lang)
      return articles