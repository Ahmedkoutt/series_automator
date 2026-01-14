import sqlite3

def init_db():
    conn = sqlite3.connect('series.db')
    c = conn.cursor()
    # إنشاء الجدول إذا لم يكن موجوداً
    c.execute('''CREATE TABLE IF NOT EXISTS episodes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  series_name TEXT,
                  episode_title TEXT,
                  clean_link TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def add_episode(series_name, title, link):
    conn = sqlite3.connect('series.db')
    c = conn.cursor()
    # التحقق من عدم وجود الرابط مسبقاً لمنع التكرار
    c.execute("SELECT id FROM episodes WHERE clean_link = ?", (link,))
    if not c.fetchone():
        c.execute("INSERT INTO episodes (series_name, episode_title, clean_link) VALUES (?, ?, ?)",
                  (series_name, title, link))
        conn.commit()
    conn.close()

def get_all_episodes():
    conn = sqlite3.connect('series.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    # جلب الحلقات مرتبة من الأحدث للأقدم
    c.execute("SELECT * FROM episodes ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def episode_exists(series_name, title):
    """دالة للتحقق السريع هل الحلقة موجودة مسبقاً أم لا"""
    conn = sqlite3.connect('series.db')
    c = conn.cursor()
    # البحث باستخدام اسم المسلسل واسم الحلقة
    c.execute("SELECT id FROM episodes WHERE series_name = ? AND episode_title = ?", (series_name, title))
    result = c.fetchone()
    conn.close()
    return result is not None

