import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from database import add_episode

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

class ThreeIskScraper:
    def __init__(self):
        chrome_options = Options()
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--incognito")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        # chrome_options.add_argument("--headless") # تفعيل هذا الخيار لاحقاً لإخفاء المتصفح
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)

    def close_popups(self, main_handle):
        try:
            handles = self.driver.window_handles
            if len(handles) > 1:
                for handle in handles:
                    if handle != main_handle:
                        self.driver.switch_to.window(handle)
                        self.driver.close()
                self.driver.switch_to.window(main_handle)
        except Exception as e:
            logging.warning(f"⚠️ خطأ أثناء إغلاق النوافذ: {e}")

    def extract_video_iframe(self, episode_url):
        main_handle = self.driver.current_window_handle
        try:
            self.driver.get(episode_url)
            # انتظار ذكي بدل الانتظار الثابت
            time.sleep(4) 
            self.close_popups(main_handle)

            # محاولة العثور على iframe أو video tag
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                src = iframe.get_attribute("src")
                # توسيع دائرة البحث لتشمل كلمات دلالية أكثر
                if src and any(x in src for x in ["3isk", "embed", "video", "watch"]):
                    logging.info(f"✅ تم العثور على رابط: {src[:50]}...")
                    return src
            return None
        except Exception as e:
            logging.error(f"❌ خطأ في صفحة الحلقة: {e}")
            return None

    def monitor_all_series(self):
        for series in SERIES_TO_WATCH:
            logging.info(f"🔄 فحص: {series['name']}")
            try:
                self.driver.get(series['url'])
                time.sleep(2)
                main_handle = self.driver.current_window_handle
                self.close_popups(main_handle)

                # البحث عن أول عنصر فيديو في القائمة
                # ملاحظة: الكلاس video-item قد يتغير، يفضل التأكد منه يدوياً إذا لم يعمل
                latest_box = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, "video-item")))
                
                ep_link_el = latest_box.find_element(By.TAG_NAME, "a")
                ep_title = latest_box.text.strip().split('\n')[0]
                ep_url = ep_link_el.get_attribute("href")

                # نقوم بالدخول فقط إذا لم تكن الحلقة موجودة مسبقاً (لتوفير الوقت)
                # *ملاحظة:* هنا نحتاج منطق بسيط في قاعدة البيانات للتحقق قبل الدخول، 
                # ولكن حالياً سيعمل الكود و add_episode ستمنع التكرار.

                clean_link = self.extract_video_iframe(ep_url)
                if clean_link:
                    add_episode(series['name'], ep_title, clean_link)
                
            except Exception as e:
                logging.warning(f"⚠️ تجاوز {series['name']}: {e}")
            
    def shutdown(self):
        try:
            self.driver.quit()
        except:
            pass

def run_scraper_loop():
    """تشغيل البوت وإعادة تشغيله كل دورة لتفريغ الرامات"""
    while True:
        logging.info("🚀 بدء دورة الفحص...")
        bot = None
        try:
            # إنشاء كائن جديد (متصفح جديد) في كل دورة
            bot = ThreeIskScraper()
            bot.monitor_all_series()
        except Exception as e:
            logging.error(f"💥 خطأ مفاجئ في الدورة: {e}")
        finally:
            if bot:
                bot.shutdown()
                logging.info("🔒 تم إغلاق المتصفح.")
        
        logging.info("💤 انتظار ساعة قبل الدورة القادمة...")
        time.sleep(3600)

if __name__ == "__main__":
    run_scraper_loop()

