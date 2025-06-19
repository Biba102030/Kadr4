import requests
from bs4 import BeautifulSoup

def parse_article_text(url: str) -> str:
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
    except Exception as e:
        return "Ошибка при загрузке статьи."
    soup = BeautifulSoup(response.text, 'html.parser')
    content = []
    for tag in soup.find_all(['h1', 'h2', 'h3', 'p']):
        text = tag.get_text(strip=True)
        if text:
            content.append(text)
    return "\n\n".join(content)
