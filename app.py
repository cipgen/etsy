from flask import Flask, render_template, request, jsonify
from etsy_parser import EtsyParser  # Импортируем наш существующий парсер
import csv
from datetime import datetime
import threading
import queue
import time

app = Flask(__name__)

# Очередь для хранения результатов парсинга
parsing_queue = queue.Queue()
# Глобальные переменные для отслеживания прогресса
current_progress = {"total": 0, "current": 0, "status": "idle"}

def parse_urls(urls):
    """Функция для парсинга списка URL-адресов"""
    parser = EtsyParser()
    current_progress["total"] = len(urls)
    current_progress["current"] = 0
    current_progress["status"] = "processing"
    
    results = []
    for url in urls:
        try:
            current_progress["current"] += 1
            data = parser.parse_product(url.strip())
            if data:
                results.append(data)
        except Exception as e:
            print(f"Error parsing {url}: {str(e)}")
    
    # Сохраняем результаты в CSV
    if results:
        output_filename = f'etsy_products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        with open('etsy-import-template.csv', 'r', newline='', encoding='utf-8') as template_file:
            headers = next(csv.reader(template_file))
        
        with open(output_filename, 'w', newline='', encoding='utf-8') as output_file:
            writer = csv.DictWriter(output_file, fieldnames=headers)
            writer.writeheader()
            for result in results:
                writer.writerow(result)
        
        current_progress["status"] = "completed"
        parsing_queue.put({"success": True, "filename": output_filename, "count": len(results)})
    else:
        current_progress["status"] = "error"
        parsing_queue.put({"success": False, "error": "No products were successfully parsed"})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/parse', methods=['POST'])
def parse():
    urls = request.form.get('urls', '').split('\n')
    urls = [url.strip() for url in urls if url.strip()]
    
    if not urls:
        return jsonify({"error": "No valid URLs provided"})
    
    # Сбрасываем прогресс
    current_progress["total"] = len(urls)
    current_progress["current"] = 0
    current_progress["status"] = "starting"
    
    # Запускаем парсинг в отдельном потоке
    threading.Thread(target=parse_urls, args=(urls,), daemon=True).start()
    
    return jsonify({"status": "started", "total": len(urls)})

@app.route('/progress')
def progress():
    return jsonify(current_progress)

@app.route('/result')
def result():
    try:
        result = parsing_queue.get_nowait()
        return jsonify(result)
    except queue.Empty:
        return jsonify({"status": "waiting"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)