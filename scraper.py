import time
import logging
import random
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from selenium_stealth import stealth
from database import add_episode, episode_exists

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

SERIES_TO_WATCH = [
    {"name": "صلاح الدين الأيوبي", "url": "https://bn.3isk.ink/watch/tvshows/serie-kudus-fatihi-selahaddin-eyyubi-1oct5/"},
    {"name": "جلال الدين خوارزم شاه", "url": "https://bn.3isk.ink/watch/tvshows/serie-jalal-aldiyn-khawarzum-shah-6jun6/"},
    {"name": "محمد سلطان الفتوحات", "url": "https://bn.3isk.ink/watch/tvshows/serie-mehmed-fetihler-sultani-1oct5/"},
    {"name": "المؤسس عثمان", "url": "https://bn.3isk.ink/watch/tvshows/serie-kurulus-osman-27sep5/"},
    {"name": "قيامة أرطغرل", "url": "https://bn.3isk.ink/watch/tvshows/serie-dirilis-ertugrul-1oct5/"},
    {"name": "بربروس: سيف البحر الأبيض", "url": "https://bn.3isk.ink/watch/tvshows/serie-barbaroslar-akdenizde-kilici-1oct5/"},
    {"name": "نهضة السلاجقة العظمى", "url": "https://bn.3isk.ink/watch/tvshows/serie-uyanis-buyudek-selcuklu-2oct5/"},
    {"name": "ألب أرسلان: السلجوقي العظيم", "url": "https://bn.3isk.ink/watch/tvshows/serie-alparslan-buyuk-selcuklu-1oct5/"}
]

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # خيارات إضافية لإخفاء الأتمتة
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # 🎭 تفعيل وضع التخفي الاحترافي (Selenium Stealth)
    # هذا يقوم بتغيير خصائص المتصفح الداخلية ليخدع Cloudflare
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )
    
    return driver

class ThreeIskScraper:
    def __init__(self):
        self.driver = get_driver()
        self.wait = WebDriverWait(self.driver, 20)

    def extract_video_iframe(self, episode_url):
        try:
            self.driver.get(episode_url)
            time.sleep(3) 
            
            # محاولة العثور على أي Iframe
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                src = iframe.get_attribute("src")
                if src and any(x in src for x in ["3isk", "embed", "video", "watch", "ok.ru", "dailymotion", "media"]):
                    return src
            return None
        except Exception as e:
            logging.error(f"❌ Error extracting iframe: {e}")
            return None

    def monitor_all_series(self):
        for series in SERIES_TO_WATCH:
            logging.info(f"🔄 جاري فحص: {series['name']}")
            try:
                self.driver.get(series['url'])
                
                # انتظار ذكي: ننتظر حتى يختفي عنوان Cloudflare أو تظهر عناصر الصفحة
                try:
                    WebDriverWait(self.driver, 20).until(
                        lambda d: "Just a moment" not in d.title and "Attention Required" not in d.title
                    )
                except:
                    logging.warning("⚠️ ما زال عالقاً في Cloudflare، سنحاول الاستمرار...")

                page_title = self.driver.title
                logging.info(f"📄 العنوان الحالي: {page_title}")

                # إذا ما زلنا في صفحة الحماية، هذا يعني أن الـ IP محظور تماماً
                if "Just a moment" in page_title:
                    logging.error(f"⛔ الحظر مستمر لـ {series['name']}. الموقع يرفض سيرفرات Streamlit.")
                    continue

                # البحث عن الحلقات (تم تحديث الـ Selectors)
                video_items = []
                try:
                    # محاولة البحث بأكثر من طريقة
                    video_items = self.driver.find_elements(By.CSS_SELECTOR, ".video-item, article, .post-details")
                except:
                    pass

                # محاولة بديلة شاملة
                if not video_items:
                    links = self.driver.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        href = link.get_attribute("href")
                        if href and ("watch" in href or "episode" in href):
                             video_items.append(link)

                if not video_items:
                    logging.warning(f"⚠️ لم يتم العثور على حلقات في الصفحة. قد يكون التصميم تغير.")
                    continue

                logging.info(f"✅ نجحنا! وجدنا {len(video_items)} رابط.")

                episodes_to_process = []
                for item in video_items:
                    try:
                        title = item.text.strip().split('\n')[0]
                        if not title: title = item.get_attribute("title")
                        
                        if item.tag_name == 'a':
                            url = item.get_attribute("href")
                        else:
                            url = item.find_element(By.TAG_NAME, "a").get_attribute("href")
                            
                        if title and url:
                            episodes_to_process.append({"title": title, "url": url})
                    except:
                        continue

                # معالجة أول 3 حلقات فقط للتجربة وتفادي الضغط
                for ep in episodes_to_process[:3]: 
                    if episode_exists(series['name'], ep['title']):
                        continue 
                    
                    logging.info(f"⚡ معالجة: {ep['title']}")
                    clean_link = self.extract_video_iframe(ep['url'])
                    
                    if clean_link:
                        add_episode(series['name'], ep['title'], clean_link)
                        logging.info(f"💾 تم الحفظ: {ep['title']}")
                        time.sleep(2)

            except Exception as e:
                logging.warning(f"⚠️ خطأ: {e}")

    def quit(self):
        try:
            self.driver.quit()
        except:
            pass

if __name__ == "__main__":
    bot = ThreeIskScraper()
    bot.monitor_all_series()
    bot.quit()


