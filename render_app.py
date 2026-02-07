from flask import Flask, jsonify, request
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
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

def close_popups(driver, wait):
    """Закриває всі popup/modal вікна на сторінці"""
    print("Перевіряємо наявність popup вікон...")
    
    try:
        # Шукаємо кнопки закриття popup (різні варіанти селекторів)
        close_buttons_selectors = [
            "button.close",
            "button[class*='close']",
            "[class*='modal'] button",
            "[class*='popup'] button",
            "button[aria-label='Close']",
            ".modal-close",
            "[data-dismiss='modal']"
        ]
        
        for selector in close_buttons_selectors:
            try:
                close_button = driver.find_element(By.CSS_SELECTOR, selector)
                if close_button.is_displayed():
                    print(f"Знайдено кнопку закриття popup: {selector}")
                    close_button.click()
                    time.sleep(1)
                    print("Popup закрито")
                    return True
            except:
                continue
        
        # Якщо не знайшли кнопку, спробуємо натиснути ESC
        print("Кнопка закриття не знайдена, натискаємо ESC...")
        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
        
        # Або клікнути поза модальним вікном
        try:
            modal_overlay = driver.find_element(By.CSS_SELECTOR, "[class*='modal-backdrop'], [class*='overlay']")
            if modal_overlay:
                print("Клікаємо на overlay...")
                modal_overlay.click()
                time.sleep(1)
        except:
            pass
            
        return True
        
    except Exception as e:
        print(f"Помилка при закритті popup: {e}")
        return False

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
        
        # Закриваємо popup якщо є
        close_popups(driver, wait)
        time.sleep(2)
        
        # Шукаємо input поля
        print(f"Шукаємо input поля...")
        text_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
        
        print(f"Знайдено {len(text_inputs)} текстових полів")
        
        if len(text_inputs) >= 3:
            city_input = text_inputs[0]
            street_input = text_inputs[1]
            building_input = text_inputs[2]
            
            # Місто
            print(f"Вводимо місто: {city}")
            try:
                # Скролимо до елемента
                driver.execute_script("arguments[0].scrollIntoView(true);", city_input)
                time.sleep(1)
                
                # Клікаємо через JavaScript якщо звичайний клік не працює
                try:
                    city_input.click()
                except ElementClickInterceptedException:
                    print("Звичайний клік не спрацював, використовуємо JavaScript...")
                    driver.execute_script("arguments[0].click();", city_input)
                
                time.sleep(1)
                city_input.clear()
                city_input.send_keys(city)
                time.sleep(3)
                
                # Шукаємо autocomplete список
                try:
                    autocomplete = wait.until(EC.presence_of_all_elements_located((
                        By.CSS_SELECTOR, 
                        "[id*='autocomplete'] li, [class*='autocomplete'] li, [role='option']"
                    )))
                    
                    if autocomplete:
                        print(f"Знайдено {len(autocomplete)} варіантів autocomplete")
                        # Клікаємо на перший варіант що містить наше місто
                        for item in autocomplete:
                            if city.lower() in item.text.lower():
                                print(f"Вибираємо: {item.text}")
                                item.click()
                                break
                        else:
                            # Якщо не знайшли точний збіг, клікаємо перший
                            autocomplete[0].click()
                except TimeoutException:
                    print("Autocomplete не з'явився, натискаємо Enter")
                    city_input.send_keys(Keys.ENTER)
                
                time.sleep(2)
                
            except Exception as e:
                print(f"Помилка при введенні міста: {e}")
                return {
                    "success": False,
                    "error": f"Не вдалось ввести місто: {str(e)}",
                    "address": f"м. {city}, вул. {street}, {building}"
                }
            
            # Вулиця
            print(f"Вводимо вулицю: {street}")
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", street_input)
                time.sleep(1)
                
                try:
                    street_input.click()
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", street_input)
                
                time.sleep(1)
                street_input.clear()
                street_input.send_keys(street)
                time.sleep(3)
                
                try:
                    autocomplete = wait.until(EC.presence_of_all_elements_located((
                        By.CSS_SELECTOR,
                        "[id*='autocomplete'] li, [class*='autocomplete'] li, [role='option']"
                    )))
                    
                    if autocomplete:
                        print(f"Знайдено {len(autocomplete)} варіантів для вулиці")
                        for item in autocomplete:
                            if street.lower() in item.text.lower():
                                print(f"Вибираємо: {item.text}")
                                item.click()
                                break
                        else:
                            autocomplete[0].click()
                except TimeoutException:
                    street_input.send_keys(Keys.ENTER)
                
                time.sleep(2)
                
            except Exception as e:
                print(f"Помилка при введенні вулиці: {e}")
            
            # Будинок
            print(f"Вводимо будинок: {building}")
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", building_input)
                time.sleep(1)
                
                try:
                    building_input.click()
                except ElementClickInterceptedException:
                    driver.execute_script("arguments[0].click();", building_input)
                
                time.sleep(1)
                building_input.clear()
                building_input.send_keys(building)
                time.sleep(3)
                
                try:
                    autocomplete = wait.until(EC.presence_of_all_elements_located((
                        By.CSS_SELECTOR,
                        "[id*='autocomplete'] li, [class*='autocomplete'] li, [role='option']"
                    )))
                    
                    if autocomplete:
                        print(f"Знайдено {len(autocomplete)} варіантів для будинку")
                        for item in autocomplete:
                            if building in item.text:
                                print(f"Вибираємо: {item.text}")
                                item.click()
                                break
                        else:
                            autocomplete[0].click()
                except TimeoutException:
                    building_input.send_keys(Keys.ENTER)
                
                time.sleep(4)
                
            except Exception as e:
                print(f"Помилка при введенні будинку: {e}")
            
            # Шукаємо результат
            print("Шукаємо результат...")
            
            try:
                result_element = wait.until(EC.presence_of_element_located((
                    By.XPATH,
                    "//*[contains(text(), 'Орієнтовний час') or contains(text(), 'відсутня електроенергія') or contains(text(), 'відключення')]"
                )))
                
                parent = result_element.find_element(By.XPATH, "./ancestor::div[1]")
                full_info = parent.text
                
                lines = full_info.split('\n')
                restoration_time = ""
                
                for line in lines:
                    if "Орієнтовний час відновлення" in line:
                        restoration_time = line
                        break
                
                if not restoration_time and lines:
                    restoration_time = lines[0]
                
                return {
                    "success": True,
                    "restoration_time": restoration_time,
                    "full_info": full_info,
                    "address": f"м. {city}, вул. {street}, {building}",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                
            except TimeoutException:
                print("Результат не знайдено за 20 секунд")
                return {
                    "success": False,
                    "error": "Не вдалось знайти результат на сторінці. Можливо адреса введена некоректно.",
                    "address": f"м. {city}, вул. {street}, {building}"
                }
        else:
            return {
                "success": False,
                "error": f"Знайдено {len(text_inputs)} input полів, очікувалось щонайменше 3",
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
        "version": "1.3.0",
        "status": "running on Render.com",
        "note": "Fixed popup blocking and element click issues",
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
