import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType
from database import add_episode, episode_exists

# إعداد السجلات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# قائمة المسلسلات
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
    """إعداد المتصفح لبيئة Streamlit Cloud"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # وضع التخفي ضروري للسيرفر
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # استخدام Chromium المتوافق مع Linux Servers
    try:
        service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
        return webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        logging.error(f"Failed to initialize driver: {e}")
        raise e

class ThreeIskScraper:
    def __init__(self):
        self.driver = get_driver()
        self.wait = WebDriverWait(self.driver, 20)

    def close_popups(self, main_handle):
        """إغلاق النوافذ المنبثقة"""
        try:
            handles = self.driver.window_handles
            if len(handles) > 1:
                for handle in handles:
                    if handle != main_handle:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                self.driver.switch_to.window(main_handle)
        except Exception as e:
            logging.warning(f"⚠️ Popup warning: {e}")

    def extract_video_iframe(self, episode_url):
        main_handle = self.driver.current_window_handle
        try:
            self.driver.get(episode_url)
            time.sleep(3) 
            self.close_popups(main_handle)

            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                src = iframe.get_attribute("src")
                if src and any(x in src for x in ["3isk", "embed", "video", "watch", "ok.ru", "dailymotion"]):
                    logging.info(f"✅ Extracted link: {src[:50]}...")
                    return src
            return None
        except Exception as e:
            logging.error(f"❌ Error extracting iframe: {e}")
            return None

    def monitor_all_series(self):
        for series in SERIES_TO_WATCH:
            logging.info(f"🔄 جاري فحص أرشيف: {series['name']}")
            try:
                self.driver.get(series['url'])
                time.sleep(3)
                main_handle = self.driver.current_window_handle
                self.close_popups(main_handle)

                # 1. جلب كل عناصر الفيديو الموجودة في الصفحة
                try:
                    video_items = self.wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "video-item")))
                except:
                    logging.warning(f"⚠️ لم يتم العثور على حلقات لـ {series['name']}")
                    continue

                logging.info(f"وجدنا {len(video_items)} حلقة في صفحة {series['name']}")

                # 2. تخزين الروابط والعناوين في قائمة مؤقتة
                episodes_to_process = []
                for item in video_items:
                    try:
                        title = item.text.strip().split('\n')[0]
                        link_el = item.find_element(By.TAG_NAME, "a")
                        url = link_el.get_attribute("href")
                        episodes_to_process.append({"title": title, "url": url})
                    except:
                        continue
                
                # 3. معالجة الحلقات (الأحدث أولاً أو حسب ترتيب الموقع)
                for ep in episodes_to_process:
                    # تحقق سريع: هل الحلقة مسجلة لدينا؟
                    if episode_exists(series['name'], ep['title']):
                        # logging.info(f"⏩ تخطي {ep['title']} (موجودة مسبقاً)")
                        continue 
                    
                    logging.info(f"⚡ جاري معالجة حلقة جديدة: {ep['title']}")
                    
                    # استخراج الرابط
                    clean_link = self.extract_video_iframe(ep['url'])
                    
                    if clean_link:
                        add_episode(series['name'], ep['title'], clean_link)
                        logging.info(f"💾 تم الحفظ: {ep['title']}")
                    
                    # استراحة قصيرة جداً لتخفيف الحمل
                    time.sleep(1)

            except Exception as e:
                logging.warning(f"⚠️ خطأ عام في {series['name']}: {e}")

    def quit(self):
        try:
            self.driver.quit()
        except:
            pass

if __name__ == "__main__":
    bot = ThreeIskScraper()
    bot.monitor_all_series()
    bot.quit()


