import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime
from typing import List, Dict
import re

async def get_categories_from_main_page() -> Dict[str, str]:
    """Извлекает категории с главной страницы kadrovik.uz"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get("https://kadrovik.uz/", headers=headers, timeout=15) as response:
                response.raise_for_status()
                html = await response.text()

        soup = BeautifulSoup(html, 'html.parser')
        categories = {}
        
        # Ищем категории на главной странице
        # Сначала ищем ссылки "Смотреть все" которые ведут к категориям
        see_all_links = soup.find_all('a', string=re.compile(r'Смотреть все|смотреть все', re.IGNORECASE))
        
        for link in see_all_links:
            href = link.get('href', '')
            if href:
                # Находим заголовок категории (обычно находится рядом с ссылкой)
                parent = link.parent
                if parent:
                    # Ищем заголовок в том же блоке
                    title_elem = parent.find_previous(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                    if not title_elem:
                        # Пробуем найти в родительском элементе
                        title_elem = parent.parent.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']) if parent.parent else None
                    
                    if title_elem:
                        category_name = title_elem.get_text(strip=True)
                        full_url = href if href.startswith('http') else f"https://kadrovik.uz{href}"
                        categories[category_name] = full_url
        
        # Дополнительно ищем основные разделы через навигацию
        nav_links = soup.find_all('a', href=True)
        for link in nav_links:
            href = link.get('href', '')
            text = link.get_text(strip=True)
            
            # Фильтруем основные категории
            if (text and len(text) > 3 and len(text) < 50 and
                any(keyword in text.lower() for keyword in ['консультации', 'новости', 'рекомендации', 'формы', 'законодательство', 'обучение', 'отвечаем']) and
                href and not href.startswith('#')):
                
                full_url = href if href.startswith('http') else f"https://kadrovik.uz{href}"
                categories[text] = full_url
        
        # Добавляем найденные на главной странице категории
        main_categories = {
            "Новые публикации": "https://kadrovik.uz/recent_publications/?group=6899",
            "Новости": "https://kadrovik.uz/recent_publications/?group=6899", 
            "Лайфхаки кадровика": "https://kadrovik.uz/publish/group7347_lifehack_for_kadrovik",
            "Справочники": "https://kadrovik.uz/services",
            "My mehnat": "https://kadrovik.uz/publish/group7318_my_mehnat_uz_k4",
            "Прием на работу": "https://kadrovik.uz/publish/group6525_priem_na_rabotu112",
            "Отпуска и отгулы": "https://kadrovik.uz/publish/group6566_6"
        }
        
        # Объединяем найденные категории с основными
        categories.update(main_categories)
        
        return categories
        
    except Exception as e:
        print(f"Ошибка при получении категорий: {e}")
        return {}

async def fetch_rubrika_articles(rubrika_url: str) -> List[Dict]:
    """Парсит статьи из конкретной рубрики"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(rubrika_url, headers=headers, timeout=15) as response:
                response.raise_for_status()
                html = await response.text()

        soup = BeautifulSoup(html, 'html.parser')
        articles = []

        # Специальная обработка для главной страницы
        if rubrika_url == "https://kadrovik.uz/" or rubrika_url == "https://kadrovik.uz":
            # На главной странице ищем статьи в текстовом контенте
            text_content = soup.get_text()
            
            # Находим все ссылки на статьи
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                title_text = link.get_text(strip=True)
                
                # Фильтруем ссылки на статьи
                if (href and title_text and 
                    len(title_text) > 30 and  # Длинные заголовки статей
                    '/publish/' in href and
                    not any(skip in title_text.lower() for skip in ['смотреть все', 'подробнее', 'читать далее', 'показать'])):
                    
                    full_url = href if href.startswith('http') else f"https://kadrovik.uz{href}"
                    
                    articles.append({
                        'title': title_text,
                        'url': full_url,
                        'date': datetime.now().isoformat()
                    })
                    
                    if len(articles) >= 10:
                        break
            
            return articles
        
        # Для других страниц используем обычный парсинг
        # Ищем различные возможные структуры статей
        possible_selectors = [
            'div.publication-item',
            'div.post-item', 
            'article',
            'div[class*="article"]',
            'div[class*="post"]',
            'div[class*="publication"]',
            '.content-item',
            '.news-item',
            '.item',
            '[class*="item"]'
        ]
        
        articles_found = []
        
        for selector in possible_selectors:
            articles_found = soup.select(selector)
            if articles_found:
                break
        
        # Если не нашли через селекторы, ищем все ссылки в контенте
        if not articles_found:
            all_links = soup.find_all('a', href=True)
            for link in all_links:
                href = link.get('href', '')
                title_text = link.get_text(strip=True)
                
                # Фильтруем ссылки на статьи
                if (href and title_text and 
                    len(title_text) > 20 and
                    '/publish/' in href and
                    not any(skip in href.lower() for skip in ['javascript:', 'mailto:', '#', 'tel:']) and
                    not any(skip in title_text.lower() for skip in ['смотреть все', 'подробнее', 'читать', 'главная', 'контакты', 'показать'])):
                    
                    full_url = href if href.startswith('http') else f"https://kadrovik.uz{href}"
                    
                    # Проверяем, не добавляли ли уже эту статью
                    if not any(art['url'] == full_url for art in articles):
                        articles.append({
                            'title': title_text,
                            'url': full_url,
                            'date': datetime.now().isoformat()
                        })
                        
                        if len(articles) >= 10:
                            break
        else:
            # Если нашли статьи через селекторы
            for item in articles_found[:15]:
                title_elem = item.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']) or item.find('a')
                link_elem = item.find('a', href=True)
                
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    href = link_elem.get('href', '')
                    
                    if title and href and len(title) > 10:
                        full_url = href if href.startswith('http') else f"https://kadrovik.uz{href}"
                        
                        articles.append({
                            'title': title,
                            'url': full_url,
                            'date': datetime.now().isoformat()
                        })
                        
                        if len(articles) >= 10:
                            break

        return articles[:10]

    except Exception as e:
        print(f"Ошибка при парсинге рубрики {rubrika_url}: {e}")
        return []

async def fetch_article_content(url: str) -> str:
    """Парсит содержимое конкретной статьи"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=15) as response:
                response.raise_for_status()
                html = await response.text()

        soup = BeautifulSoup(html, 'html.parser')
        
        # Заголовок статьи
        title = ""
        title_selectors = ['h1', 'h2.title', '.article-title', '.post-title', '.content-title']
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem:
                title = title_elem.get_text(strip=True)
                break
        
        if not title:
            title = "Статья с сайта kadrovik.uz"
        
        # Дата публикации
        date = ""
        date_selectors = ['time', '.date', '.published-date', '[datetime]']
        for selector in date_selectors:
            date_elem = soup.select_one(selector)
            if date_elem:
                date = date_elem.get('datetime') or date_elem.get_text(strip=True)
                break
        
        # Основной контент
        content_selectors = [
            '.article-content',
            '.post-content', 
            '.content',
            'main',
            '.main-content',
            '#content',
            '.text-content'
        ]
        
        content_block = None
        for selector in content_selectors:
            content_block = soup.select_one(selector)
            if content_block:
                break
        
        # Если не нашли основной контент, берем body, исключая навигацию
        if not content_block:
            content_block = soup.find('body')
            if content_block:
                # Удаляем навигационные элементы
                for unwanted in content_block.find_all(['nav', 'header', 'footer', 'aside', 'script', 'style']):
                    unwanted.decompose()
        
        if not content_block:
            return f"📰 {title}\n📅 {date}\n\nНе удалось найти содержимое статьи."

        # Извлекаем текстовый контент
        content_parts = [f"📰 {title}"]
        if date:
            content_parts.append(f"📅 {date}")
        content_parts.append("")  # Пустая строка для разделения
        
        # Получаем все текстовые элементы
        text_elements = content_block.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div'])
        
        processed_texts = set()  # Для избежания дублирования
        
        for element in text_elements:
            text = element.get_text(' ', strip=True)
            
            # Фильтруем короткие и повторяющиеся тексты
            if (text and len(text) > 20 and 
                text not in processed_texts and
                not any(skip in text.lower() for skip in ['javascript', 'loading', 'menu', 'навигация', 'войти', 'регистрация'])):
                
                processed_texts.add(text)
                
                # Форматируем в зависимости от типа элемента
                if element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    content_parts.append(f"\n🔸 {text}\n")
                elif element.name == 'li':
                    content_parts.append(f"• {text}")
                else:
                    content_parts.append(text)
        
        result = '\n'.join(content_parts)
        
        # Если контент слишком короткий, пробуем альтернативный способ
        if len(result) < 200:
            all_text = content_block.get_text(' ', strip=True)
            if len(all_text) > 100:
                result = f"📰 {title}\n📅 {date}\n\n{all_text[:2000]}..."
        
        return result

    except Exception as e:
        print(f"Ошибка при парсинге статьи {url}: {e}")
        return f"Не удалось загрузить содержимое статьи. Ошибка: {str(e)}"

# Функция для получения актуальных рубрик с сайта
async def get_all_categories():
    """Получает все категории с главной страницы"""
    categories = await get_categories_from_main_page()
    
    # Если не удалось получить с главной страницы, используем базовые
    if not categories:
        categories = {
            "Главная страница": "https://kadrovik.uz/",
            "Новые публикации": "https://kadrovik.uz/recent_publications/?group=6899",
            "Лайфхаки кадровика": "https://kadrovik.uz/publish/group7347_lifehack_for_kadrovik",
            "My mehnat": "https://kadrovik.uz/publish/group7318_my_mehnat_uz_k4",
            "Прием на работу": "https://kadrovik.uz/publish/group6525_priem_na_rabotu112",
            "Отпуска и отгулы": "https://kadrovik.uz/publish/group6566_6",
            "Справочники": "https://kadrovik.uz/services"
        }
    
    return categories

# Функция для тестирования парсера
async def test_parser():
    """Тестирует работу парсера"""
    print("🔍 Тестирование парсера kadrovik.uz...")
    
    # Сначала получаем все категории с сайта
    print("\n📋 Получаем категории с главной страницы...")
    categories = await get_all_categories()
    
    if categories:
        print(f"✅ Найдено {len(categories)} категорий:")
        for name, url in categories.items():
            print(f"  • {name}: {url}")
    else:
        print("❌ Категории не найдены")
        return
    
    # Тестируем парсинг статей из каждой категории
    for category_name, category_url in list(categories.items())[:5]:  # Тестируем первые 5 категорий
        print(f"\n📂 Тестируем категорию: {category_name}")
        articles = await fetch_rubrika_articles(category_url)
        
        if articles:
            print(f"✅ Найдено {len(articles)} статей")
            for i, article in enumerate(articles[:3], 1):  # Показываем первые 3
                print(f"  {i}. {article['title'][:80]}...")
                print(f"     URL: {article['url']}")
            
            # Тестируем парсинг содержимого первой статьи
            if articles:
                print(f"\n📄 Тестируем парсинг содержимого первой статьи...")
                content = await fetch_article_content(articles[0]['url'])
                print(f"✅ Получено содержимое ({len(content)} символов)")
                print(f"Превью: {content[:200]}...")
        else:
            print("❌ Статьи не найдены")
    
    print("\n🏁 Тестирование завершено!")

# Функция для парсинга конкретной категории по названию
async def parse_category_by_name(category_name: str):
    """Парсит статьи из конкретной категории по её названию"""
    categories = await get_all_categories()
    
    if category_name in categories:
        print(f"📂 Парсим категорию: {category_name}")
        articles = await fetch_rubrika_articles(categories[category_name])
        return articles
    else:
        print(f"❌ Категория '{category_name}' не найдена")
        print("Доступные категории:")
        for name in categories.keys():
            print(f"  • {name}")
        return []

# Запуск тестирования (раскомментируйте для тестирования):
# import asyncio
# asyncio.run(test_parser())