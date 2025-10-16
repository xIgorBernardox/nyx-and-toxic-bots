import os
import time
import requests
import sqlite3
import traceback
import praw
import threading

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
REDDIT_CLIENT_ID = os.environ["REDDIT_CLIENT_ID"]
REDDIT_CLIENT_SECRET = os.environ["REDDIT_CLIENT_SECRET"]
REDDIT_USER_AGENT = os.environ["REDDIT_USER_AGENT"]

# ==============================

# Banco de dados para evitar posts duplicados
DB = "sent_posts.db"
conn = sqlite3.connect(DB)
conn.execute("CREATE TABLE IF NOT EXISTS sent (id TEXT PRIMARY KEY)")
conn.commit()

# Inicializa o Reddit
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

def already_sent(post_id):
    cur = conn.execute("SELECT 1 FROM sent WHERE id=?", (post_id,))
    return cur.fetchone() is not None

def mark_sent(post_id):
    conn.execute("INSERT OR IGNORE INTO sent(id) VALUES(?)", (post_id,))
    conn.commit()

def post_to_discord(webhook_url, title, url, author, subreddit):
    content = f"📢 **Novo post em r/{subreddit}**\n**{title}**\n{url}\n👤 por u/{author}"
    data = {"content": content}
    r = requests.post(webhook_url, json=data)
    if r.status_code != 204:
        print(f"Erro ao enviar para Discord ({subreddit}):", r.text)

def monitor_subreddit(subreddit_name, webhook_url):
    subreddit = reddit.subreddit(subreddit_name)
    print(f"Monitorando r/{subreddit_name}...")
    for submission in subreddit.stream.submissions(skip_existing=True):
        post_id = submission.id
        if already_sent(post_id):
            continue

        title = submission.title
        url = "https://reddit.com" + submission.permalink
        author = submission.author.name if submission.author else "[deleted]"
        print(f"Novo post em r/{subreddit_name}: {title}")

        post_to_discord(webhook_url, title, url, author, subreddit_name)
        mark_sent(post_id)

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