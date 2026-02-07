from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
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
        
        # Чекаємо завантаження сторінки
        print("Чекаємо завантаження сторінки...")
        time.sleep(5)
        
        # Зберігаємо HTML для діагностики
        page_source = driver.page_source
        print(f"Завантажено {len(page_source)} символів HTML")
        
        # Спробуємо різні селектори для знаходження форми
        try:
            # Варіант 1: Пошук через NAME атрибут
            print("Спроба 1: Пошук через name='city'")
            city_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "select[name='city'], input[name='city']")))
            print(f"Знайдено елемент: {city_element.tag_name}")
        except:
            try:
                # Варіант 2: Пошук через ID
                print("Спроба 2: Пошук через id містить 'city'")
                city_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[id*='city']")))
                print(f"Знайдено елемент: {city_element.tag_name}")
            except:
                try:
                    # Варіант 3: Пошук будь-якого select в формі
                    print("Спроба 3: Пошук всіх select елементів")
                    selects = driver.find_elements(By.TAG_NAME, "select")
                    print(f"Знайдено {len(selects)} select елементів")
                    
                    if len(selects) >= 3:
                        city_select = selects[0]
                        street_select = selects[1]
                        building_select = selects[2]
                        
                        # Використовуємо Select
                        print(f"Вибираємо місто: {city}")
                        Select(city_select).select_by_visible_text(f"м. {city}")
                        time.sleep(2)
                        
                        print(f"Вибираємо вулицю: {street}")
                        Select(street_select).select_by_visible_text(f"вул. {street}")
                        time.sleep(2)
                        
                        print(f"Вибираємо будинок: {building}")
                        Select(building_select).select_by_visible_text(building)
                        time.sleep(4)
                        
                        # Шукаємо результат
                        print("Шукаємо результат...")
                        result_text = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Орієнтовний час')]")))
                        
                        parent = result_text.find_element(By.XPATH, "./ancestor::div[contains(@class, 'alert') or contains(@class, 'info') or contains(@class, 'result')]")
                        full_info = parent.text
                        
                        lines = full_info.split('\n')
                        restoration_time = ""
                        
                        for line in lines:
                            if "Орієнтовний час відновлення" in line:
                                restoration_time = line
                                break
                        
                        return {
                            "success": True,
                            "restoration_time": restoration_time if restoration_time else full_info.split('\n')[0],
                            "full_info": full_info,
                            "address": f"м. {city}, вул. {street}, {building}",
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                    else:
                        raise Exception(f"Очікувалось 3 select елементи, знайдено {len(selects)}")
                        
                except Exception as e:
                    # Якщо нічого не спрацювало, повертаємо діагностичну інформацію
                    print(f"Помилка: {e}")
                    
                    # Шукаємо будь-яку інформацію про форму
                    forms = driver.find_elements(By.TAG_NAME, "form")
                    inputs = driver.find_elements(By.TAG_NAME, "input")
                    
                    return {
                        "success": False,
                        "error": str(e),
                        "debug_info": {
                            "forms_found": len(forms),
                            "inputs_found": len(inputs),
                            "selects_found": len(driver.find_elements(By.TAG_NAME, "select")),
                            "page_title": driver.title,
                            "current_url": driver.current_url
                        },
                        "address": f"м. {city}, вул. {street}, {building}",
                        "suggestion": "Сайт ДТЕК можливо змінив структуру. Потрібно оновити селектори."
                    }
        
        # Якщо дійшли сюди через перший варіант (знайшли через name/id)
        # Тут була б логіка для цього випадку
        return {
            "success": False,
            "error": "Неочікуваний шлях виконання",
            "address": f"м. {city}, вул. {street}, {building}"
        }
            
    except Exception as e:
        print(f"Критична помилка: {e}")
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
        "version": "1.1.0",
        "status": "running on Render.com",
        "endpoints": {
            "/": "GET - Інформація про API",
            "/health": "GET - Перевірка роботи API",
            "/check": "GET - Перевірити відключення",
            "/debug": "GET - Діагностична інформація"
        },
        "parameters": {
            "city": "Назва міста (за замовчуванням: Одеса)",
            "street": "Назва вулиці (за замовчуванням: Марсельська)",
            "building": "Номер будинку (за замовчуванням: 60)"
        },
        "examples": [
            "/check",
            "/check?city=Одеса&street=Марсельська&building=60"
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

@app.route('/debug')
def debug():
    """Діагностичний endpoint для перевірки що саме на сайті"""
    driver = None
    try:
        chrome_options = get_chrome_options()
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://www.dtek-oem.com.ua/ua/shutdowns")
        
        time.sleep(5)
        
        forms = driver.find_elements(By.TAG_NAME, "form")
        selects = driver.find_elements(By.TAG_NAME, "select")
        inputs = driver.find_elements(By.TAG_NAME, "input")
        
        return jsonify({
            "page_title": driver.title,
            "url": driver.current_url,
            "forms_count": len(forms),
            "selects_count": len(selects),
            "inputs_count": len(inputs),
            "selects_info": [
                {
                    "name": s.get_attribute("name"),
                    "id": s.get_attribute("id"),
                    "class": s.get_attribute("class")
                } for s in selects
            ] if selects else "No select elements found"
        })
    except Exception as e:
        return jsonify({
            "error": str(e)
        })
    finally:
        if driver:
            driver.quit()

@app.route('/check')
def check_outage():
    """Endpoint для перевірки відключень"""
    
    city = request.args.get('city', 'Одеса')
    street = request.args.get('street', 'Марсельська')
    building = request.args.get('building', '60')
    
    print(f"Запит на перевірку: {city}, {street}, {building}")
    
    result = get_power_outage_info(city, street, building)
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
