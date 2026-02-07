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
        wait = WebDriverWait(driver, 15)
        
        print("Відкриваємо сайт...")
        driver.get("https://www.dtek-oem.com.ua/ua/shutdowns")
        time.sleep(7)  # Збільшили час очікування
        
        # Закриваємо popup через ESC
        print("Закриваємо popup...")
        from selenium.webdriver.common.action_chains import ActionChains
        for _ in range(3):
            ActionChains(driver).send_keys(Keys.ESCAPE).perform()
            time.sleep(0.5)
        
        # Словник полів з їх ID
        steps = [
            {"id": "city", "value": city, "name": "місто"},
            {"id": "street", "value": street, "name": "вулиця"},
            {"id": "house_num", "value": building, "name": "будинок"}
        ]

        for step in steps:
            print(f"Обробка поля: {step['name']}")
            
            # Чекаємо, поки поле стане клікабельним 
            el = wait.until(EC.element_to_be_clickable((By.ID, step['id'])))
            
            # Прокрутка до поля
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
            time.sleep(0.5)
            
            # Введення тексту
            el.clear()
            for char in step['value']:
                el.send_keys(char)
                time.sleep(0.1)
            
            # Чекаємо випадаючий список та обираємо перший варіант
            time.sleep(2) 
            el.send_keys(Keys.ARROW_DOWN)
            time.sleep(0.5)
            el.send_keys(Keys.ENTER)
            
            # Даємо час скриптам сайту розблокувати наступне поле
            time.sleep(2)

        # 2. Очікування результату
        print("Шукаємо блок з результатом...")
        # Шукаємо жовтий блок або текст про відключення
        time.sleep(5)
        
        try:
            # Спроба знайти фінальний текст результату
            result_element = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "is-open")))
            res_text = result_element.text
        except:
            # Якщо специфічний клас не знайдено, беремо весь текст
            res_text = driver.find_element(By.TAG_NAME, "body").text

        if "відсутня електроенергія" in res_text or "Екстрені відключення" in res_text:
            return {
                "success": True,
                "status": "OFF",
                "info": res_text.split("Увага!")[0].strip(), # Беремо основну частину до примітки
                "address": f"{city}, {street}, {building}"
            }
        else:
            return {
                "success": True,
                "status": "ON",
                "info": "За цією адресою відключень не знайдено (або графіки не діють)",
                "address": f"{city}, {street}, {building}"
            }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        if driver: driver.quit()

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
