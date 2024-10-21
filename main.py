import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import random
import re

def parse_etsy_product(url, session):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    
    time.sleep(random.uniform(1, 3))
    
    response = session.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Failed to retrieve the page. Status code: {response.status_code}")
        return None
    
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract title
    title_element = soup.find('h1', attrs={"data-buy-box-listing-title": "true"})
    title = title_element.text.strip() if title_element else "Title not found"
    
    # Extract price
    price_element = soup.find('p', class_='wt-text-title-larger')
    if price_element:
        price_text = price_element.get_text(strip=True)
        price_match = re.search(r'CA\$\s*(\d+\.?\d*)', price_text)
        price = price_match.group(1) if price_match else "Price not found"
    else:
        price = "Price not found"
    
    # Extract description
    script = soup.find('script', type='application/ld+json')
    if script:
        data = json.loads(script.string)
        description = data.get('description', 'Description not found')
    else:
        description = "Description not found"
    
    # Get URLs of all images
    carousel_images = soup.find_all('img', class_='carousel-image')
    image_urls = []
    for img in carousel_images:
        if 'src' in img.attrs:
            image_url = img.get('data-src-zoom-image', img.get('src', ''))
            if image_url and image_url not in image_urls:
                image_urls.append(image_url)
    
    # Get tags
    tags = [tag.text.strip() for tag in soup.find_all('li', class_='wt-action-group__item-container')]
    
    # Создаем словарь с базовой информацией
    product_data = {
        'title': title,
        'price': price,
        'description': description,
        'tags': ', '.join(tags)
    }
    
    # Добавляем фотографии в отдельные колонки
    for i, url in enumerate(image_urls, 1):
        product_data[f'Photo {i}'] = url
    
    # Если фотографий меньше 10, добавляем пустые колонки
    for i in range(len(image_urls) + 1, 11):
        product_data[f'Photo {i}'] = ''
        
    return product_data

def save_to_csv(data, filename='etsy_product.csv'):
    # Определяем порядок колонок
    columns = ['title', 'price', 'description', 'tags']
    columns.extend([f'Photo {i}' for i in range(1, 11)])  # Добавляем колонки для фото
    
    with open(filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerow(data)
    print(f"Data saved to {filename}")

# URL of the product
url = "https://www.etsy.com/ca/listing/290849671/modern-contemporary-property-number-door"

# Create a session
session = requests.Session()

# Parse the page and save data
product_data = parse_etsy_product(url, session)
if product_data:
    save_to_csv(product_data)
    print("Successfully parsed the product page.")
    print(f"Title: {product_data['title']}")
    print(f"Price: {product_data['price']}")
    
    # Выводим URL каждой фотографии
    for i in range(1, 11):
        photo_key = f'Photo {i}'
        if product_data[photo_key]:
            print(f"{photo_key}: {product_data[photo_key]}")
else:
    print("Failed to parse the product page.")