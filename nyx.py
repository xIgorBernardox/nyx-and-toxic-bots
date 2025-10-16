import os
import time
import requests
import sqlite3
import traceback
import praw
import threading
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ======== CONFIGURAÇÃO ========

# Webhooks do Discord
WEBHOOKS = {
    "leaks": os.environ["WEBHOOK_LEAKS"],
    "memes": os.environ["WEBHOOK_MEMES"]
}

# Subreddits e qual webhook eles usam
SUBREDDITS = {
    "Genshin_Impact_Leaks": "leaks",
    "HonkaiStarRail_leaks": "leaks",
    "Zenlesszonezeroleaks_": "leaks",
    "WutheringWavesLeaks": "leaks",
    "MemesBrasil": "memes"
}

# Credenciais do Reddit
# REDDIT_USERNAME = os.environ["REDDIT_USERNAME"]
# REDDIT_PASSWORD = os.environ["REDDIT_PASSWORD"]
REDDIT_CLIENT_ID = os.environ["REDDIT_CLIENT_ID"]
REDDIT_CLIENT_SECRET = os.environ["REDDIT_CLIENT_SECRET"]
REDDIT_USER_AGENT = os.environ["REDDIT_USER_AGENT"]

# ==============================
# Servidor HTTP fake só pra Render não reclamar da porta
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot rodando!")

def run_server():
    server = HTTPServer(("0.0.0.0", 10000), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

def monitor_subreddit(subreddit_name, webhook_url):
    # Cria conexão SQLite própria para esta thread
    conn = sqlite3.connect("sent_posts.db")
    conn.execute("CREATE TABLE IF NOT EXISTS sent (id TEXT PRIMARY KEY)")
    conn.commit()

    subreddit = reddit.subreddit(subreddit_name)
    print(f"Monitorando r/{subreddit_name}...")

    for submission in subreddit.stream.submissions(skip_existing=True):
        post_id = submission.id

        # Checa se já enviou
        cur = conn.execute("SELECT 1 FROM sent WHERE id=?", (post_id,))
        if cur.fetchone():
            continue

        title = submission.title
        url = "https://reddit.com" + submission.permalink
        author = submission.author.name if submission.author else "[deleted]"
        print(f"Novo post em r/{subreddit_name}: {title}")

        post_to_discord(webhook_url, title, url, author, subreddit_name)

        # Marca como enviado
        conn.execute("INSERT OR IGNORE INTO sent(id) VALUES(?)", (post_id,))
        conn.commit()

    conn.close()

# Inicializa o Reddit
reddit = praw.Reddit(
    # username=REDDIT_USERNAME,
    # password=REDDIT_PASSWORD,
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

def post_to_discord(webhook_url, title, url, author, subreddit):
    content = f"📢 **Novo post em r/{subreddit}**\n**{title}**\n{url}\n👤 por u/{author}"
    data = {"content": content}
    r = requests.post(webhook_url, json=data)
    if r.status_code != 204:
        print(f"Erro ao enviar para Discord ({subreddit}):", r.text)

def monitor_subreddit(subreddit_name, webhook_url):
    # Conexão SQLite própria da thread
    conn = sqlite3.connect("sent_posts.db")
    conn.execute("CREATE TABLE IF NOT EXISTS sent (id TEXT PRIMARY KEY)")
    conn.commit()

    subreddit = reddit.subreddit(subreddit_name)
    print(f"Monitorando r/{subreddit_name}...")

    for submission in subreddit.stream.submissions(skip_existing=True):
        post_id = submission.id
        cur = conn.execute("SELECT 1 FROM sent WHERE id=?", (post_id,))
        if cur.fetchone():
            continue

        title = submission.title
        url = "https://reddit.com" + submission.permalink
        author = submission.author.name if submission.author else "[deleted]"
        print(f"Novo post em r/{subreddit_name}: {title}")

        post_to_discord(webhook_url, title, url, author, subreddit_name)
        conn.execute("INSERT OR IGNORE INTO sent(id) VALUES(?)", (post_id,))
        conn.commit()

    conn.close()

def main():
    threads = []
    for subreddit_name, webhook_key in SUBREDDITS.items():
        webhook_url = WEBHOOKS[webhook_key]
        t = threading.Thread(target=monitor_subreddit, args=(subreddit_name, webhook_url), daemon=True)
        threads.append(t)
        t.start()

    # Mantém o script rodando
    while True:
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Encerrando bot...")