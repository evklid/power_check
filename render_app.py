from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import time
import os
import base64

app = Flask(__name__)

def get_chrome_options():
    """Налаштування Chrome"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    return chrome_options

def get_power_outage_info(city="Одеса", street="Марсельська", building="60"):
    """Спрощена версія з мінімальною логікою"""
    
    driver = None
    try:
        chrome_options = get_chrome_options()
        driver = webdriver.Chrome(options=chrome_options)
        
        print("Відкриваємо сайт...")
        driver.get("https://www.dtek-oem.com.ua/ua/shutdowns")
        time.sleep(7)  # Збільшили час очікування
        
        # Закриваємо popup через ESC
        print("Закриваємо popup...")
        from selenium.webdriver.common.action_chains import ActionChains
        for _ in range(3):
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(0.5)
        
        # Знаходимо ВСІ input поля
        print("Шукаємо input поля...")
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        text_inputs = [inp for inp in all_inputs if inp.get_attribute("type") == "text"]
        
        print(f"Всього inputs: {len(all_inputs)}, текстових: {len(text_inputs)}")
        
        if len(text_inputs) < 3:
            # Можливо поля ще не завантажились
            time.sleep(3)
            all_inputs = driver.find_elements(By.TAG_NAME, "input")
            text_inputs = [inp for inp in all_inputs if inp.get_attribute("type") == "text"]
            print(f"Після додаткового очікування: {len(text_inputs)} текстових полів")
        
        if len(text_inputs) >= 3:
            # ПРОСТИЙ ПІДХІД: просто вводимо текст і натискаємо Enter/Tab
            fields = [
                (text_inputs[0], city, "місто"),
                (text_inputs[1], street, "вулиця"),  
                (text_inputs[2], building, "будинок")
            ]
            
            for field, value, name in fields:
                print(f"\n--- Поле: {name} ---")
                try:
                    # Скролимо
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", field)
                    time.sleep(0.5)
                    
                    # Фокус через JS
                    driver.execute_script("arguments[0].focus();", field)
                    time.sleep(0.3)
                    
                    # Очищаємо
                    field.clear()
                    time.sleep(0.3)
                    
                    # Вводимо по одному символу (імітуємо людину)
                    for char in value:
                        field.send_keys(char)
                        time.sleep(0.1)
                    
                    print(f"Введено: {value}")
                    time.sleep(2)  # Чекаємо появу dropdown
                    
                    # Просто натискаємо стрілку вниз і Enter
                    field.send_keys(Keys.ARROW_DOWN)
                    time.sleep(0.5)
                    field.send_keys(Keys.ENTER)
                    time.sleep(1)
                    
                    print(f"✓ {name} заповнено")
                    
                except Exception as e:
                    print(f"✗ Помилка для {name}: {e}")
                    return {
                        "success": False,
                        "error": f"Не вдалось ввести {name}: {str(e)}",
                        "address": f"м. {city}, вул. {street}, {building}"
                    }
            
            # Після заповнення всіх полів чекаємо на результат
            print("\nЧекаємо на результат...")
            time.sleep(8)  # Даємо більше часу на завантаження
            
            # Отримуємо весь текст сторінки
            body_text = driver.find_element(By.TAG_NAME, "body").text
            print(f"Отримано {len(body_text)} символів тексту")
            
            # Шукаємо ключові фрази
            keywords = ["Орієнтовний час", "відсутня електроенергія", "За вашою адресою", 
                       "відключення", "електроенергія", "відновлення"]
            
            found_keywords = [kw for kw in keywords if kw in body_text]
            print(f"Знайдено ключові слова: {found_keywords}")
            
            if found_keywords:
                # Витягуємо релевантні рядки
                lines = body_text.split('\n')
                result_lines = []
                
                for i, line in enumerate(lines):
                    if any(kw in line for kw in keywords):
                        # Беремо 5 рядків до і 5 після
                        start = max(0, i-2)
                        end = min(len(lines), i+8)
                        result_lines = lines[start:end]
                        break
                
                full_info = '\n'.join(result_lines)
                
                # Шукаємо час відновлення
                restoration_time = ""
                for line in result_lines:
                    if "Орієнтовний час відновлення" in line or "до" in line and ":" in line:
                        restoration_time = line
                        break
                
                return {
                    "success": True,
                    "restoration_time": restoration_time if restoration_time else result_lines[0] if result_lines else "Знайдено інформацію",
                    "full_info": full_info if full_info else body_text[:500],
                    "address": f"м. {city}, вул. {street}, {building}",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                return {
                    "success": False,
                    "error": "Ключові слова не знайдені на сторінці",
                    "debug_text": body_text[:800],
                    "address": f"м. {city}, вул. {street}, {building}"
                }
        else:
            return {
                "success": False,
                "error": f"Знайдено {len(text_inputs)} текстових полів (потрібно 3)",
                "address": f"м. {city}, вул. {street}, {building}"
            }
            
    except Exception as e:
        print(f"ПОМИЛКА: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    finally:
        if driver:
            driver.quit()

@app.route('/')
def home():
    return jsonify({
        "message": "DTEK API",
        "version": "1.5.0 - Simplified",
        "endpoints": {
            "/health": "Health check",
            "/check": "Check outage (params: city, street, building)",
            "/test": "Test page access and form fields"
        }
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")})

@app.route('/test')
def test():
    """Тестовий endpoint - просто відкриває сторінку і дивиться що там є"""
    driver = None
    try:
        chrome_options = get_chrome_options()
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://www.dtek-oem.com.ua/ua/shutdowns")
        time.sleep(5)
        
        # Закриваємо popup
        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
        
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        text_inputs = [inp for inp in all_inputs if inp.get_attribute("type") == "text"]
        
        return jsonify({
            "page_title": driver.title,
            "total_inputs": len(all_inputs),
            "text_inputs": len(text_inputs),
            "text_inputs_details": [
                {
                    "placeholder": inp.get_attribute("placeholder"),
                    "name": inp.get_attribute("name"),
                    "id": inp.get_attribute("id"),
                    "visible": inp.is_displayed(),
                    "enabled": inp.is_enabled()
                }
                for inp in text_inputs[:5]
            ],
            "page_text_preview": driver.find_element(By.TAG_NAME, "body").text[:500]
        })
    except Exception as e:
        return jsonify({"error": str(e)})
    finally:
        if driver:
            driver.quit()

@app.route('/check')
def check_outage():
    city = request.args.get('city', 'Одеса')
    street = request.args.get('street', 'Марсельська')
    building = request.args.get('building', '60')
    
    print(f"\n{'='*50}")
    print(f"ЗАПИТ: {city}, {street}, {building}")
    print(f"{'='*50}\n")
    
    result = get_power_outage_info(city, street, building)
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
