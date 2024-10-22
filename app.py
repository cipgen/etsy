from flask import Flask, render_template, request, jsonify
from etsy_parser import EtsyParser
import csv
from datetime import datetime
import threading
import queue
import time
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Настройка загрузки файлов
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'csv'}

# Создаем папку для загрузок, если её нет
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Максимальный размер файла 16MB

# Очередь для хранения результатов парсинга
parsing_queue = queue.Queue()
# Глобальные переменные для отслеживания прогресса
current_progress = {"total": 0, "current": 0, "status": "idle"}

def allowed_file(filename):
    """Проверка допустимого расширения файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_urls_from_file(file_path):
    """Извлекает URLs из файла"""
    urls = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            url = line.strip()
            if url and url.startswith('http'):
                urls.append(url)
    return urls

def parse_urls(urls):
    """Функция для парсинга списка URL-адресов"""
    parser = EtsyParser()
    current_progress["total"] = len(urls)
    current_progress["current"] = 0
    current_progress["status"] = "processing"
    
    results = []
    for url in urls:
        try:
            print(f"Парсинг URL: {url}")  # Отладочная информация
            current_progress["current"] += 1
            data = parser.parse_product(url.strip())
            if data:
                results.append(data)
        except Exception as e:
            print(f"Ошибка при парсинге {url}: {str(e)}")
    
    # Сохраняем результаты в CSV
    if results:
        output_filename = f'etsy_products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        try:
            with open('etsy-import-template.csv', 'r', newline='', encoding='utf-8') as template_file:
                headers = next(csv.reader(template_file))
            
            with open(output_filename, 'w', newline='', encoding='utf-8') as output_file:
                writer = csv.DictWriter(output_file, fieldnames=headers)
                writer.writeheader()
                for result in results:
                    writer.writerow(result)
            
            current_progress["status"] = "completed"
            parsing_queue.put({
                "success": True, 
                "filename": output_filename, 
                "count": len(results),
                "total_processed": current_progress["current"]
            })
        except Exception as e:
            print(f"Ошибка при сохранении результатов: {str(e)}")
            current_progress["status"] = "error"
            parsing_queue.put({"success": False, "error": str(e)})
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

@app.route('/parse-file', methods=['POST'])
def parse_file():
    # Проверяем, есть ли файл в запросе
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"})
    
    file = request.files['file']
    
    # Проверяем, выбран ли файл
    if file.filename == '':
        return jsonify({"error": "No file selected"})
    
    # Проверяем расширение файла
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Only .txt and .csv files are allowed"})
    
    try:
        # Безопасно сохраняем файл
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Извлекаем URLs из файла
        urls = extract_urls_from_file(file_path)
        
        # Удаляем временный файл
        os.remove(file_path)
        
        if not urls:
            return jsonify({"error": "No valid URLs found in file"})
        
        print(f"Найдено {len(urls)} URL-адресов в файле")  # Отладочная информация
        
        # Сбрасываем прогресс
        current_progress["total"] = len(urls)
        current_progress["current"] = 0
        current_progress["status"] = "starting"
        
        # Запускаем парсинг в отдельном потоке
        threading.Thread(target=parse_urls, args=(urls,), daemon=True).start()
        
        return jsonify({
            "status": "started", 
            "total": len(urls),
            "message": f"Starting to parse {len(urls)} URLs"
        })
        
    except Exception as e:
        print(f"Ошибка при обработке файла: {str(e)}")  # Отладочная информация
        return jsonify({"error": f"Error processing file: {str(e)}"})

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