from fastapi import FastAPI
from pydantic import BaseModel
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller
import time
import pickle
import os
from dotenv import load_dotenv

app = FastAPI()

load_dotenv()
EMAIL = os.getenv("LINKEDIN_EMAIL")
PASSWORD = os.getenv("LINKEDIN_PASSWORD")
COOKIE_FILE = "linkedin_cookies.pkl"

class PostRequest(BaseModel):
    post_content: str

def create_driver():
    chromedriver_autoinstaller.install()
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # run without GUI
    chrome_options.add_argument("--no-sandbox")  # required for some cloud platforms
    chrome_options.add_argument("--disable-dev-shm-usage")  # overcome limited resource problems
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    return webdriver.Chrome(options=chrome_options)

def login(driver):
    driver.get("https://www.linkedin.com/login")
    time.sleep(3)
    email_field = driver.find_element(By.ID, "username")
    password_field = driver.find_element(By.ID, "password")
    email_field.send_keys(EMAIL)
    password_field.send_keys(PASSWORD)
    password_field.send_keys(Keys.RETURN)
    time.sleep(5)
    pickle.dump(driver.get_cookies(), open(COOKIE_FILE, "wb"))

def load_cookies(driver):
    if not os.path.exists(COOKIE_FILE):
        login(driver)
    cookies = pickle.load(open(COOKIE_FILE, "rb"))
    driver.get("https://www.linkedin.com/feed/")
    time.sleep(3)
    for cookie in cookies:
        driver.add_cookie(cookie)
    driver.refresh()
    time.sleep(5)

def post_on_linkedin(post_content):
    driver = create_driver()
    try:
        try:
            load_cookies(driver)
        except Exception:
            login(driver)
            load_cookies(driver)

        driver.get("https://www.linkedin.com/feed/")

        try:
            post_button = driver.find_element(By.XPATH, ".//span[contains(@class,'artdeco-button__text')]//strong[text()='Start a post']]")
            post_button.click()
        except Exception as e:
            print("\u274c Failed to click 'Start a post' button:", e)
            return False

        try:
            post_text_area = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((
                    By.XPATH,
                    "//div[contains(@class, 'ql-editor') and @contenteditable='true' and @role='textbox']"
                ))
            )
            post_text_area.click()
            post_text_area.send_keys(post_content)
        except Exception as e:
            print("\u274c Failed to type post content:", e)
            return False

        try:
            post_button_final = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((
                    By.XPATH,
                    "//button[contains(@class,'share-actions__primary-action') and not(@disabled)]"
                ))
            )
            post_button_final.click()
        except Exception as e:
            print("\u274c Failed to click Post button:", e)
            return False

        return True
    finally:
        driver.quit()

@app.post("/post_content")
def post_to_linkedin(req: PostRequest):
    success = post_on_linkedin(req.post_content)
    return {"status": "success" if success else "failed"}

@app.get("/")
def read_root():
    return {"message": "LinkedIn Automation API is running 🚀"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
