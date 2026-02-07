from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import Select
import time
import os

app = Flask(__name__)

def get_chrome_options():
    """Налаштування Chrome для Render.com"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    return chrome_options

def get_power_outage_info(city="Одеса", street="Марсельська", building="60"):
    """Функція для отримання інформації про відключення з сайту ДТЕК"""
    
    driver = None
    try:
        chrome_options = get_chrome_options()
        driver = webdriver.Chrome(options=chrome_options)
        
        print(f"Відкриваємо сайт ДТЕК...")
        driver.get("https://www.dtek-oem.com.ua/ua/shutdowns")
        
        wait = WebDriverWait(driver, 20)
        
        # Чекаємо завантаження форми
        print("Чекаємо форму...")
        time.sleep(3)
        
        # Вибираємо населений пункт
        print(f"Вибираємо місто: {city}")
        city_dropdown = wait.until(EC.presence_of_element_located((By.NAME, "city")))
        city_select = Select(city_dropdown)
        city_select.select_by_visible_text(f"м. {city}")
        time.sleep(2)
        
        # Вибираємо вулицю
        print(f"Вибираємо вулицю: {street}")
        street_dropdown = wait.until(EC.presence_of_element_located((By.NAME, "street")))
        street_select = Select(street_dropdown)
        street_select.select_by_visible_text(f"вул. {street}")
        time.sleep(2)
        
        # Вибираємо номер будинку
        print(f"Вибираємо будинок: {building}")
        building_dropdown = wait.until(EC.presence_of_element_located((By.NAME, "building")))
        building_select = Select(building_dropdown)
        building_select.select_by_visible_text(building)
        time.sleep(4)
        
        # Отримуємо інформацію про відключення
        print("Отримуємо результат...")
        
        # Шукаємо блок з інформацією про відключення
        try:
            info_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Орієнтовний час відновлення')]")
            
            if info_elements:
                # Знаходимо батьківський елемент з повною інформацією
                parent = info_elements[0].find_element(By.XPATH, "./ancestor::div[contains(@class, 'alert') or contains(@class, 'info')]")
                full_info = parent.text
                
                # Витягуємо рядок з часом відновлення
                lines = full_info.split('\n')
                restoration_time = ""
                
                for line in lines:
                    if "Орієнтовний час відновлення" in line:
                        restoration_time = line
                        break
                
                return {
                    "success": True,
                    "restoration_time": restoration_time if restoration_time else "Інформація про час відновлення не знайдена",
                    "full_info": full_info,
                    "address": f"м. {city}, вул. {street}, {building}",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
            else:
                # Якщо немає інформації про відключення
                page_text = driver.find_element(By.TAG_NAME, "body").text
                
                if "відсутня електроенергія" in page_text.lower() or "відключення" in page_text.lower():
                    return {
                        "success": True,
                        "restoration_time": "Інформацію про відновлення не знайдено на сайті",
                        "full_info": "Можливо, зараз немає планових відключень або інформація ще не оновлена",
                        "address": f"м. {city}, вул. {street}, {building}",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                else:
                    return {
                        "success": True,
                        "restoration_time": "Електропостачання в нормі",
                        "full_info": "Відключень не виявлено",
                        "address": f"м. {city}, вул. {street}, {building}",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                
        except Exception as e:
            print(f"Помилка при пошуку інформації: {e}")
            return {
                "success": False,
                "error": f"Не вдалося знайти інформацію про відключення: {str(e)}",
                "address": f"м. {city}, вул. {street}, {building}"
            }
            
    except Exception as e:
        print(f"Помилка: {e}")
        return {
            "success": False,
            "error": str(e),
            "address": f"м. {city}, вул. {street}, {building}"
        }
    finally:
        if driver:
            driver.quit()
            print("Браузер закрито")

@app.route('/')
def home():
    """Головна сторінка API"""
    return jsonify({
        "message": "DTEK Power Outage API",
        "version": "1.0.0",
        "status": "running on Render.com",
        "endpoints": {
            "/": "GET - Інформація про API",
            "/health": "GET - Перевірка роботи API",
            "/check": "GET - Перевірити відключення"
        },
        "parameters": {
            "city": "Назва міста (за замовчуванням: Одеса)",
            "street": "Назва вулиці (за замовчуванням: Марсельська)",
            "building": "Номер будинку (за замовчуванням: 60)"
        },
        "examples": [
            "/check",
            "/check?city=Одеса&street=Марсельська&building=60",
            "/check?city=Київ&street=Хрещатик&building=1"
        ]
    })

@app.route('/health')
def health():
    """Перевірка роботи API"""
    return jsonify({
        "status": "healthy",
        "message": "API працює нормально",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/check')
def check_outage():
    """Endpoint для перевірки відключень"""
    
    # Отримуємо параметри з запиту
    city = request.args.get('city', 'Одеса')
    street = request.args.get('street', 'Марсельська')
    building = request.args.get('building', '60')
    
    print(f"Запит на перевірку: {city}, {street}, {building}")
    
    result = get_power_outage_info(city, street, building)
    return jsonify(result)

if __name__ == '__main__':
    # Render.com використовує змінну PORT
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
