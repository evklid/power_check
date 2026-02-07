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

def close_popups(driver):
    """Закриває всі popup/modal вікна"""
    print("Закриваємо popup...")
    
    try:
        # Натискаємо ESC
        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(1)
        
        # Шукаємо і клікаємо кнопки закриття
        close_selectors = [
            "button.close", "button[class*='close']",
            "[class*='modal'] button", ".modal-close"
        ]
        
        for selector in close_selectors:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, selector)
                for btn in buttons:
                    if btn.is_displayed():
                        try:
                            btn.click()
                        except:
                            driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
            except:
                pass
                
    except Exception as e:
        print(f"Помилка при закритті popup: {e}")

def get_power_outage_info(city="Одеса", street="Марсельська", building="60"):
    """Функція для отримання інформації про відключення з сайту ДТЕК"""
    
    driver = None
    try:
        chrome_options = get_chrome_options()
        driver = webdriver.Chrome(options=chrome_options)
        
        print(f"Відкриваємо сайт ДТЕК...")
        driver.get("https://www.dtek-oem.com.ua/ua/shutdowns")
        
        wait = WebDriverWait(driver, 30)  # Збільшили timeout до 30 секунд
        
        print("Чекаємо завантаження...")
        time.sleep(5)
        
        # Закриваємо popup
        close_popups(driver)
        time.sleep(2)
        
        # Шукаємо текстові поля
        print("Шукаємо поля форми...")
        text_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
        print(f"Знайдено {len(text_inputs)} текстових полів")
        
        if len(text_inputs) < 3:
            return {
                "success": False,
                "error": f"Знайдено лише {len(text_inputs)} полів замість 3",
                "address": f"м. {city}, вул. {street}, {building}"
            }
        
        city_input = text_inputs[0]
        street_input = text_inputs[1]
        building_input = text_inputs[2]
        
        # Функція для безпечного введення тексту
        def safe_input(element, text, field_name):
            print(f"Вводимо {field_name}: {text}")
            try:
                # Скролимо до елемента
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                time.sleep(0.5)
                
                # Клікаємо через JS
                driver.execute_script("arguments[0].click();", element)
                time.sleep(0.5)
                
                # Очищаємо і вводимо текст
                element.clear()
                element.send_keys(text)
                time.sleep(2)
                
                # Чекаємо autocomplete
                try:
                    autocomplete_items = WebDriverWait(driver, 5).until(
                        EC.presence_of_all_elements_located((
                            By.CSS_SELECTOR,
                            "[id*='autocomplete'] li, [class*='autocomplete'] li, " +
                            "[id*='cityautocomplete'] div, [role='option'], .autocomplete-item"
                        ))
                    )
                    
                    if autocomplete_items:
                        print(f"Знайдено {len(autocomplete_items)} варіантів autocomplete")
                        # Клікаємо на перший видимий
                        for item in autocomplete_items:
                            if item.is_displayed():
                                print(f"Вибираємо: {item.text[:50]}")
                                try:
                                    item.click()
                                except:
                                    driver.execute_script("arguments[0].click();", item)
                                break
                        time.sleep(1)
                        return True
                except TimeoutException:
                    print(f"Autocomplete не з'явився для {field_name}")
                    # Просто натискаємо Tab для переходу до наступного поля
                    element.send_keys(Keys.TAB)
                    time.sleep(1)
                    return True
                    
            except Exception as e:
                print(f"Помилка при введенні {field_name}: {e}")
                return False
        
        # Заповнюємо поля
        if not safe_input(city_input, city, "міста"):
            return {"success": False, "error": "Не вдалось ввести місто"}
        
        if not safe_input(street_input, street, "вулиці"):
            return {"success": False, "error": "Не вдалось ввести вулицю"}
        
        if not safe_input(building_input, building, "будинку"):
            return {"success": False, "error": "Не вдалось ввести будинок"}
        
        # Чекаємо на результат (збільшили час очікування)
        print("Чекаємо на результат (до 30 секунд)...")
        time.sleep(5)  # Додаткова пауза
        
        try:
            # Різні варіанти пошуку результату
            result_selectors = [
                "//*[contains(text(), 'Орієнтовний час')]",
                "//*[contains(text(), 'відсутня електроенергія')]",
                "//*[contains(text(), 'За вашою адресою')]",
                "//div[contains(@class, 'alert')]",
                "//div[contains(@class, 'result')]",
                "//div[contains(@class, 'info')]"
            ]
            
            result_element = None
            for selector in result_selectors:
                try:
                    print(f"Пробуємо селектор: {selector}")
                    result_element = wait.until(
                        EC.presence_of_element_located((By.XPATH, selector))
                    )
                    if result_element and result_element.is_displayed():
                        print(f"Знайдено результат через: {selector}")
                        break
                except TimeoutException:
                    continue
            
            if not result_element:
                # Якщо нічого не знайшли, беремо весь текст сторінки
                print("Результат не знайдено через селектори, беремо body text")
                body_text = driver.find_element(By.TAG_NAME, "body").text
                
                # Шукаємо ключові фрази в тексті
                if "Орієнтовний час" in body_text or "відсутня електроенергія" in body_text:
                    lines = body_text.split('\n')
                    result_lines = []
                    capture = False
                    
                    for line in lines:
                        if "За вашою адресою" in line or "Орієнтовний" in line:
                            capture = True
                        if capture:
                            result_lines.append(line)
                            if len(result_lines) > 10:  # Максимум 10 рядків
                                break
                    
                    full_info = '\n'.join(result_lines)
                    
                    # Шукаємо рядок з часом
                    restoration_time = ""
                    for line in result_lines:
                        if "Орієнтовний час відновлення" in line:
                            restoration_time = line
                            break
                    
                    return {
                        "success": True,
                        "restoration_time": restoration_time if restoration_time else result_lines[0] if result_lines else "Інформація знайдена",
                        "full_info": full_info if full_info else "Перевірте сайт ДТЕК",
                        "address": f"м. {city}, вул. {street}, {building}",
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    }
                else:
                    return {
                        "success": False,
                        "error": "Результат не знайдено на сторінці",
                        "debug": body_text[:500],  # Перші 500 символів для діагностики
                        "address": f"м. {city}, вул. {street}, {building}"
                    }
            
            # Якщо знайшли через селектор
            parent = result_element.find_element(By.XPATH, "./ancestor::div[contains(@class, 'alert') or contains(@class, 'info')][1]")
            full_info = parent.text
            
            lines = full_info.split('\n')
            restoration_time = ""
            
            for line in lines:
                if "Орієнтовний час відновлення" in line:
                    restoration_time = line
                    break
            
            return {
                "success": True,
                "restoration_time": restoration_time if restoration_time else (lines[0] if lines else ""),
                "full_info": full_info,
                "address": f"м. {city}, вул. {street}, {building}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
                
        except TimeoutException:
            print("Timeout при очікуванні результату")
            # Зберігаємо скріншот для діагностики (в headless це не працює, але залишимо)
            try:
                screenshot = driver.get_screenshot_as_base64()
                print(f"Screenshot captured: {len(screenshot)} bytes")
            except:
                pass
            
            return {
                "success": False,
                "error": "Результат не з'явився за 30 секунд. Можливо адреса некоректна або сайт працює повільно.",
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

@app.route('/')
def home():
    return jsonify({
        "message": "DTEK Power Outage API",
        "version": "1.4.0",
        "status": "running",
        "endpoints": {
            "/health": "GET - Health check",
            "/check": "GET - Check power outage"
        }
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    })

@app.route('/check')
def check_outage():
    city = request.args.get('city', 'Одеса')
    street = request.args.get('street', 'Марсельська')
    building = request.args.get('building', '60')
    
    print(f"\n=== Новий запит ===")
    print(f"Адреса: {city}, {street}, {building}")
    
    result = get_power_outage_info(city, street, building)
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
