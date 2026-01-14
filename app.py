import streamlit as st
import time
from database import init_db, get_all_episodes
# نضع هذا الاستيراد داخل دالة لتجنب تشغيل المتصفح فور فتح التطبيق
from scraper import ThreeIskScraper 

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="مراقب المسلسلات التركية",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. التأكد من وجود قاعدة البيانات
init_db()

# 3. عنوان التطبيق وتنسيق بسيط
st.title("🎬 Series Automator & Viewer")
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        background-color: #ff4b4b;
        color: white;
        font-weight: bold;
    }
    .reportview-container {
        background: #0e1117;
    }
</style>
""", unsafe_allow_html=True)

# 4. قسم التحديث (Scraping)
st.sidebar.header("لوحة التحكم")
if st.sidebar.button("🔄 ابحث عن حلقات جديدة الآن"):
    status_placeholder = st.empty()
    status_placeholder.info("⏳ جاري تشغيل المتصفح المخفي والبحث عن الحلقات... قد يستغرق الأمر دقيقة.")
    
    try:
        # تشغيل البوت
        bot = ThreeIskScraper()
        bot.monitor_all_series()
        bot.quit()
        
        status_placeholder.success("✅ تم الانتهاء من الفحص وتحديث القائمة!")
        time.sleep(2)
        st.rerun()  # إعادة تحميل الصفحة لإظهار الحلقات الجديدة فوراً
        
    except Exception as e:
        status_placeholder.error(f"❌ حدث خطأ أثناء الفحص: {e}")

# 5. عرض الحلقات (The Viewer)
st.header("أحدث الحلقات المضافة")

episodes = get_all_episodes()

if not episodes:
    st.info("📭 لا توجد حلقات مسجلة في قاعدة البيانات حتى الآن. اضغط على الزر في القائمة الجانبية للبحث.")
else:
    # عرض الحلقات في شكل بطاقات قابلة للتوسيع
    for ep in episodes:
        # تنسيق العنوان: اسم المسلسل - الحلقة
        label = f"{ep['series_name']} | {ep['episode_title']}"
        
        with st.expander(label, expanded=False):
            st.caption(f"تاريخ الإضافة: {ep['created_at']}")
            
            # التأكد من وجود رابط
            if ep['clean_link']:
                # استخدام مكون iframe لعرض الفيديو
                st.components.v1.iframe(ep['clean_link'], height=450, scrolling=True)
                st.markdown(f"[🔗 فتح الرابط في نافذة خارجية]({ep['clean_link']})")
            else:
                st.warning("الرابط غير متوفر لهذه الحلقة.")

# تذييل الصفحة
st.markdown("---")
st.caption("تم التطوير بواسطة مساعد الذكاء الاصطناعي - نسخة Streamlit Cloud")


