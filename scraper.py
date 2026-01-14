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
    
    # تحسينات إضافية لتسريع الصفحة
    chrome_options.add_argument("--blink-settings=imagesEnabled=false") # عدم تحميل الصور (توفير رهيب للسرعة)
    
    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # ---------------------------------------------------------
    # 🛡️ تفعيل نظام حجب الإعلانات (The AdBlock Logic)
    # ---------------------------------------------------------
    driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": [
        "*.doubleclick.net", 
        "*.googlesyndication.com", 
        "*.google-analytics.com", 
        "*.facebook.net", 
        "*pop*", 
        "*ads*", 
        "*tracker*", 
        "*stat*",
        "*pixel*",
        "*.cloudflare.com/cdn-cgi/challenge-platform/*" # محاولة لتخفيف سكربتات التتبع
    ]})
    driver.execute_cdp_cmd('Network.enable', {})
    # ---------------------------------------------------------
    
    return driver

class ThreeIskScraper:
    def __init__(self):
        self.driver = get_driver()
        self.wait = WebDriverWait(self.driver, 20)

    def extract_video_iframe(self, episode_url):
        try:
            logging.info(f"🕵️ فحص الرابط: {episode_url}")
            self.driver.get(episode_url)
            # قللنا وقت الانتظار لأن الموقع بقى أخف بكتير بدون إعلانات
            time.sleep(2) 
            
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
                
                # طباعة العنوان للتأكد
                page_title = self.driver.title
                logging.info(f"📄 العنوان: {page_title}")

                if "Just a moment" in page_title:
                    logging.warning("🛡️ Cloudflare check detected. Waiting...")
                    time.sleep(10)

                # البحث عن الحلقات بطرق ذكية
                video_items = []
                try:
                    # الطريقة الأولى: البحث عن العناصر الشائعة
                    video_items = self.driver.find_elements(By.CSS_SELECTOR, ".video-item, .post-item, .ep-item")
                except:
                    pass

                # الطريقة الثانية: البحث عن أي رابط يحتوي على كلمة "حلقة"
                if not video_items:
                    links = self.driver.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        text = link.text
                        href = link.get_attribute("href")
                        if href and ("حلقة" in text or "episode" in href or "watch" in href):
                             video_items.append(link)

                logging.info(f"✅ وجدنا {len(video_items)} رابط محتمل.")

                # تجميع البيانات
                episodes_to_process = []
                for item in video_items:
                    try:
                        title = item.text.strip().split('\n')[0]
                        # لو العنوان فاضي، نحاول نجيبه من الـ alt أو الـ title attribute
                        if not title:
                            title = item.get_attribute("title")
                        
                        # الحصول على الرابط
                        if item.tag_name == 'a':
                            url = item.get_attribute("href")
                        else:
                            url = item.find_element(By.TAG_NAME, "a").get_attribute("href")
                            
                        if title and url:
                            episodes_to_process.append({"title": title, "url": url})
                    except:
                        continue

                # المعالجة
                for ep in episodes_to_process:
                    # تحقق سريع من قاعدة البيانات
                    if episode_exists(series['name'], ep['title']):
                        continue 
                    
                    logging.info(f"⚡ معالجة جديدة: {ep['title']}")
                    clean_link = self.extract_video_iframe(ep['url'])
                    
                    if clean_link:
                        add_episode(series['name'], ep['title'], clean_link)
                        logging.info(f"💾 تم الحفظ: {ep['title']}")
                        time.sleep(1) # استراحة قصيرة

            except Exception as e:
                logging.warning(f"⚠️ تجاوز {series['name']}: {e}")

    def quit(self):
        try:
            self.driver.quit()
        except:
            pass

if __name__ == "__main__":
    bot = ThreeIskScraper()
    bot.monitor_all_series()
    bot.quit()


