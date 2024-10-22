import requests
from bs4 import BeautifulSoup
import csv
import json
import time
import random
import re
from typing import Dict, Optional, List
from datetime import datetime
from colorama import init, Fore, Style

init()

class EtsyParser:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        
    def _make_request(self, url: str, retries: int = 3) -> Optional[requests.Response]:
        for attempt in range(retries):
            try:
                time.sleep(random.uniform(2, 5))
                response = self.session.get(url, headers=self.headers, timeout=30)
                response.raise_for_status()
                return response
            except requests.RequestException as e:
                print(f"{Fore.RED}Попытка {attempt + 1}/{retries} не удалась: {str(e)}{Style.RESET_ALL}")
                if attempt == retries - 1:
                    print(f"{Fore.RED}Не удалось получить {url} после {retries} попыток{Style.RESET_ALL}")
                    return None
        return None

    def _extract_price(self, soup: BeautifulSoup) -> str:
        price_selectors = [
            ('p', 'wt-text-title-larger'),
            ('span', 'wt-text-title-largest'),
            ('p', 'wt-text-title-03')
        ]
        
        for tag, class_name in price_selectors:
            price_element = soup.find(tag, class_=class_name)
            if price_element:
                price_text = price_element.get_text(strip=True)
                price_match = re.search(r'(?:CA)?\$\s*(\d+\.?\d*)', price_text)
                if price_match:
                    return price_match.group(1)
        return ""

    def _extract_images(self, soup: BeautifulSoup) -> List[str]:
        image_urls = []
        
        image_selectors = [
            ('img', 'carousel-image'),
            ('img', 'wt-max-width-full'),
            ('img', 'listing-page-image')
        ]
        
        for tag, class_name in image_selectors:
            images = soup.find_all(tag, class_=class_name)
            for img in images:
                image_url = (
                    img.get('data-src-zoom-image') or 
                    img.get('data-fullxfull') or 
                    img.get('src')
                )
                if image_url and image_url not in image_urls:
                    image_url = image_url.replace('http://', 'https://')
                    image_urls.append(image_url)
        
        return image_urls

    def parse_product(self, url: str) -> Optional[Dict]:
        print(f"\n{Fore.CYAN}Начинаем парсинг: {url}{Style.RESET_ALL}")
        
        response = self._make_request(url)
        if not response:
            return None
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Извлекаем заголовок
        title_element = soup.find('h1', attrs={"data-buy-box-listing-title": "true"})
        title = title_element.text.strip() if title_element else ""
        print(f"{Fore.GREEN}Заголовок найден: {title}{Style.RESET_ALL}")
        
        # Извлекаем цену
        price = self._extract_price(soup)
        print(f"{Fore.GREEN}Цена найдена: {price}{Style.RESET_ALL}")
        
        # Извлекаем описание
        description = ""
        script = soup.find('script', type='application/ld+json')
        if script:
            try:
                data = json.loads(script.string)
                description = data.get('description', '')
                print(f"{Fore.GREEN}Описание успешно извлечено{Style.RESET_ALL}")
            except json.JSONDecodeError:
                print(f"{Fore.YELLOW}Не удалось извлечь описание из JSON{Style.RESET_ALL}")
        
        # Извлекаем теги
        tags = []
        tags_section = soup.find('div', class_='tags-section-container')
        if tags_section:
            tag_links = tags_section.find_all('a', href=True)
            tags = [tag.get_text(strip=True) for tag in tag_links if tag.get_text(strip=True)]
            print(f"{Fore.GREEN}Найдено тегов: {len(tags)}{Style.RESET_ALL}")
        
        # Получаем URL изображений
        image_urls = self._extract_images(soup)
        print(f"{Fore.GREEN}Найдено изображений: {len(image_urls)}{Style.RESET_ALL}")
        
        # Создаем словарь со всеми полями из шаблона
        product_data = {
            'Title': title,
            'Description': description,
            'Category': '',
            'Who made it?': '',
            'What is it?': '',
            'When was it made?': '',
            'Renewal options': '',
            'Product type': '',
            'Tags': ', '.join(tags) if tags else '',
            'Materials': '',
            'Production partners': '',
            'Section': '',
            'Price': price,
            'Quantity': '',
            'SKU': '',
            'Variation 1': '',
            'V1 Option': '',
            'Variation 2': '',
            'V2 Option': '',
            'Var Price': '',
            'Var Quantity': '',
            'Var SKU': '',
            'Var Visibility': '',
            'Var Photo': '',
            'Shipping profile': '',
            'Weight': '',
            'Length': '',
            'Width': '',
            'Height': '',
            'Return policy': '',
            'Video 1': '',
            'Digital file 1': '',
            'Digital file 2': '',
            'Digital file 3': '',
            'Digital file 4': '',
            'Digital file 5': ''
        }
        
        # Добавляем фотографии
        for i in range(1, 11):
            photo_key = f'Photo {i}'
            product_data[photo_key] = image_urls[i-1] if i <= len(image_urls) else ''
        
        print(f"{Fore.GREEN}Парсинг успешно завершен!{Style.RESET_ALL}")
        return product_data

    def update_csv_template(self, data: Dict, template_path: str = 'etsy-import-template.csv', output_path: str = None):
        """Обновляет существующий CSV шаблон данными"""
        if output_path is None:
            output_path = f'etsy_products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        try:
            # Читаем заголовки из шаблона
            with open(template_path, 'r', newline='', encoding='utf-8') as template_file:
                reader = csv.reader(template_file)
                headers = next(reader)
            
            # Записываем данные в новый файл
            with open(output_path, 'w', newline='', encoding='utf-8') as output_file:
                writer = csv.DictWriter(output_file, fieldnames=headers)
                writer.writeheader()
                writer.writerow(data)
            
            print(f"\n{Fore.GREEN}Данные успешно сохранены в {output_path}{Style.RESET_ALL}")
        except Exception as e:
            print(f"\n{Fore.RED}Ошибка при сохранении в CSV: {str(e)}{Style.RESET_ALL}")

def main():
    parser = EtsyParser()
    url = "https://www.etsy.com/ca/listing/290849671/modern-contemporary-property-number-door"
    
    try:
        print(f"\n{Fore.CYAN}=== Начало работы парсера ==={Style.RESET_ALL}")
        product_data = parser.parse_product(url)
        if product_data:
            parser.update_csv_template(product_data)
            print(f"\n{Fore.GREEN}=== Парсинг успешно завершен! ==={Style.RESET_ALL}")
            
            # Вывод основной информации
            print(f"\n{Fore.CYAN}Основная информация:{Style.RESET_ALL}")
            print(f"Название: {product_data['Title']}")
            print(f"Цена: ${product_data['Price']}")
            print(f"Количество тегов: {len(product_data['Tags'].split(',')) if product_data['Tags'] else 0}")
            print(f"Количество фото: {sum(1 for k, v in product_data.items() if k.startswith('Photo') and v)}")
        else:
            print(f"\n{Fore.RED}Не удалось спарсить товар.{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}Неожиданная ошибка: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()