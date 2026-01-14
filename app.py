from flask import Flask, render_template
import threading
from database import init_db, get_all_episodes
from scraper import run_scraper_loop

app = Flask(__name__)

@app.route('/')
def index():
    episodes = get_all_episodes()
    return render_template('index.html', episodes=episodes)

if __name__ == '__main__':
    init_db()

    # تشغيل السكريبر في خيط منفصل
    scraper_thread = threading.Thread(target=run_scraper_loop, daemon=True)
    scraper_thread.start()

    # use_reloader=False ضروري لمنع تشغيل السكريبر مرتين
    app.run(debug=True, port=5000, use_reloader=False)


