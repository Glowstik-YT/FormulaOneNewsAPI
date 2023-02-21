import time
from fastapi import BackgroundTasks, FastAPI, Header, HTTPException
import requests
from bs4 import BeautifulSoup
from typing import Dict
from dotenv import load_dotenv
import os

app = FastAPI()
load_dotenv()
cache = {}

GUEST_KEY = os.getenv('GUEST_KEY')
PERSONAL_KEY = os.getenv('MAIN_KEY')
API_KEYS = [GUEST_KEY, PERSONAL_KEY]

def check_api_key(api_key: str = Header(...)):
    if api_key not in API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API key")

@app.get('/api/get/articles/{api_key}')
def get_news(background_tasks: BackgroundTasks, api_key: str):
    check_api_key(api_key)
    if 'articles' in cache:
        return {"articles": cache['articles']}

    articles = scrape_news()
    cache['articles'] = articles

    background_tasks.add_task(update_cache, 5 * 60)

    return {"articles": articles}

@app.get("/api/get/article/{api_key}")
def get_article_info(url: str, api_key: str):
    check_api_key(api_key)
    if 'formula1.com' not in url:
        return {'error': 'Invalid URL. Only URLs from formula1.com are allowed.'}

    article_info = fetch_article_info(url)
    return {"article_info": article_info}

def fetch_article_info(url: str) -> Dict[str, str]:

    response = requests.get(url)
    content = response.content

    soup = BeautifulSoup(content, 'html.parser')

    article_title = soup.find('h1', {'class': 'f1--xl'})
    article_text = soup.find_all('div', {'class': 'f1-article--rich-text'})
    article_tags = soup.find_all('a', {'class': 'tag'})
    article_image = soup.find('figure', {'class': 'f1-image breakout-left'})

    title = article_title.text if article_title else None
    tags = list(set([tag.text for tag in article_tags]))

    content = ''
    for text in article_text:
        for paragraph in text.find_all('p'):
            content += paragraph.text

    image = article_image.find('img')['data-src'] if article_image and article_image.find('img').has_attr('data-src') else None

    article_info = {'title': title, 'content': content, 'tags': tags, 'image': image}
    return article_info

def scrape_news():
    url = 'https://www.formula1.com/en/latest/all.html'

    response = requests.get(url)

    soup = BeautifulSoup(response.content, 'html.parser')

    article_links = soup.find_all('a', {'class': 'f1-cc f1-cc--reg-primary f1-cc--white-solid f1-image--hover-zoom'})
    article_names = soup.find_all('p', {'class': 'f1--s no-margin'})

    articles = []
    for i in range(len(article_links)):
        article_url = "https://www.formula1.com" + article_links[i]['href']
        article_title = article_names[i].text.strip()
        article_info = fetch_article_info(article_url)
        articles.append({'title': article_title, 'url': article_url, 'info': article_info})

    return articles

def update_cache(sleep_time: int):
    while True:
        time.sleep(sleep_time)
        cache['articles'] = scrape_news()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get('PORT', 8000)), reload=True)
