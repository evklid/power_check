from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
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
        
        # Шукаємо input поля (не select!)
        # За скріншотом видно що це autocomplete поля
        
        # Поле для міста
        print(f"Шукаємо поле для міста...")
        city_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
        
        if len(city_inputs) >= 3:
            city_input = city_inputs[0]  # Перше поле - місто
            street_input = city_inputs[1]  # Друге поле - вулиця
            building_input = city_inputs[2]  # Третє поле - будинок
            
            # Вводимо місто
            print(f"Вводимо місто: {city}")
            city_input.click()
            time.sleep(1)
            city_input.send_keys(city)
            time.sleep(2)
            
            # Чекаємо на випадаючий список і вибираємо перший варіант
            try:
                # Шукаємо випадаючий список autocomplete
                autocomplete_items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[class*='autocomplete'] li, [class*='dropdown'] li, .autocomplete-item")))
                if autocomplete_items:
                    print(f"Знайдено {len(autocomplete_items)} варіантів для міста")
                    # Вибираємо перший що містить наше місто
                    for item in autocomplete_items:
                        if city in item.text:
                            item.click()
                            break
                else:
                    # Якщо не знайшли список, просто натискаємо Enter
                    city_input.send_keys(Keys.ENTER)
            except:
                city_input.send_keys(Keys.ENTER)
            
            time.sleep(2)
            
            # Вводимо вулицю
            print(f"Вводимо вулицю: {street}")
            street_input.click()
            time.sleep(1)
            street_input.send_keys(street)
            time.sleep(2)
            
            try:
                autocomplete_items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[class*='autocomplete'] li, [class*='dropdown'] li, .autocomplete-item")))
                if autocomplete_items:
                    print(f"Знайдено {len(autocomplete_items)} варіантів для вулиці")
                    for item in autocomplete_items:
                        if street in item.text:
                            item.click()
                            break
                else:
                    street_input.send_keys(Keys.ENTER)
            except:
                street_input.send_keys(Keys.ENTER)
            
            time.sleep(2)
            
            # Вводимо номер будинку
            print(f"Вводимо будинок: {building}")
            building_input.click()
            time.sleep(1)
            building_input.send_keys(building)
            time.sleep(2)
            
            try:
                autocomplete_items = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[class*='autocomplete'] li, [class*='dropdown'] li, .autocomplete-item")))
                if autocomplete_items:
                    print(f"Знайдено {len(autocomplete_items)} варіантів для будинку")
                    for item in autocomplete_items:
                        if building in item.text:
                            item.click()
                            break
                else:
                    building_input.send_keys(Keys.ENTER)
            except:
                building_input.send_keys(Keys.ENTER)
            
            time.sleep(4)
            
            # Шукаємо результат
            print("Шукаємо результат...")
            
            try:
                # Шукаємо блок з інформацією
                result_element = wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Орієнтовний час') or contains(text(), 'відсутня електроенергія') or contains(text(), 'електроенергія')]")))
                
                # Знаходимо батьківський контейнер
                parent = result_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'alert') or contains(@class, 'info') or contains(@class, 'result') or contains(@class, 'message')]")
                full_info = parent.text
                
                # Витягуємо рядок з часом
                lines = full_info.split('\n')
                restoration_time = ""
                
                for line in lines:
                    if "Орієнтовний час відновлення" in line:
                        restoration_time = line
                        break
                
                if not restoration_time and lines:
                    restoration_time = lines[0] if len(lines) > 0 else "Інформація не знайдена"
                
                return {
                    "success": True,
                    "restoration_time": restoration_time,
                    "full_info": full_info,
                    "address": f"м. {city}, вул. {street}, {building}",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
            except Exception as e:
                print(f"Помилка при пошуку результату: {e}")
                
                # Спробуємо отримати весь текст сторінки
                page_text = driver.find_element(By.TAG_NAME, "body").text
                
                if "відсутня електроенергія" in page_text or "відключення" in page_text.lower():
                    return {
                        "success": True,
                        "restoration_time": "Є відключення, але не вдалось витягнути точний час",
                        "full_info": "Перевірте сайт ДТЕК вручну для деталей",
                        "address": f"м. {city}, вул. {street}, {building}",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Не вдалось знайти результат: {str(e)}",
                        "address": f"м. {city}, вул. {street}, {building}"
                    }
        else:
            return {
                "success": False,
                "error": f"Знайдено {len(city_inputs)} input полів, очікувалось щонайменше 3",
                "address": f"м. {city}, вул. {street}, {building}"
            }
            
    except Exception as e:
        print(f"Критична помилка: {e}")
        import traceback
        traceback.print_exc()
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
        "version": "1.2.0",
        "status": "running on Render.com",
        "note": "Now using autocomplete inputs instead of select dropdowns",
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
    """Діагностичний endpoint"""
    driver = None
    try:
        chrome_options = get_chrome_options()
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://www.dtek-oem.com.ua/ua/shutdowns")
        
        time.sleep(5)
        
        text_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
        all_inputs = driver.find_elements(By.TAG_NAME, "input")
        
        return jsonify({
            "page_title": driver.title,
            "url": driver.current_url,
            "text_inputs_count": len(text_inputs),
            "all_inputs_count": len(all_inputs),
            "text_inputs_info": [
                {
                    "name": inp.get_attribute("name"),
                    "id": inp.get_attribute("id"),
                    "placeholder": inp.get_attribute("placeholder"),
                    "class": inp.get_attribute("class")
                } for inp in text_inputs[:5]  # Перші 5
            ]
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
