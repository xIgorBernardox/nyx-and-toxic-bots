import time
import requests
import sqlite3
import traceback
import praw
import threading

# ======== CONFIGURAÇÃO ========

# Webhooks do Discord
WEBHOOKS = {
    "leaks": "https://discord.com/api/webhooks/1428455650995736688/I1ObgTZvah7ulSpeqEO-FjqWZLMlr9K4dh5wh0nhGzqmdSd0VCDFr6GzL7VQB7nPEtxS",  # para leaks
    "memes": "https://discord.com/api/webhooks/1428460902587437097/C__BTiES36HAQCn4v7vIlZ9mAw-LJwtIwX4rUwKeUEH4GzRtMzQriMW1vd366taP_CsZ"   # para memes
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
REDDIT_CLIENT_ID = "_bWQLuzphmwo1CAP5RYo8A"
REDDIT_CLIENT_SECRET = "lnyCR7wf04qqtFIGRLcZJUsI7mQRXw"
REDDIT_USER_AGENT = "reddit-discord-bot by u/Fluffy-Objective-179"

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