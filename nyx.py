import os
import time
import requests
import sqlite3
import traceback
import praw
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ======== CONFIGURAÇÃO ========

WEBHOOKS = {
    "wuthering-leaks": os.environ["WEBHOOK_WUTHERING_LEAKS"],
    "zenless-leaks": os.environ["WEBHOOK_ZENLESS_LEAKS"],
    "genshin-leaks": os.environ["WEBHOOK_GENSHIN_LEAKS"],
    "honkai-leaks": os.environ["WEBHOOK_HONKAI_LEAKS"],
    "fortnite-leaks": os.environ["WEBHOOK_FORTNITE_LEAKS"],
    "memes": os.environ["WEBHOOK_MEMES"]
}

SUBREDDITS = {
    "WutheringWavesLeaks": "wuthering-leaks",
    "Zenlesszonezeroleaks_": "zenless-leaks",
    "Genshin_Impact_Leaks": "genshin-leaks",
    "HonkaiStarRail_leaks": "honkai-leaks",
    "FortniteLeaks": "fortnite-leaks",
    "MemesBrasil": "memes"
}

# Mensagens personalizadas
MESSAGES = {
    "HonkaiStarRail_leaks": "📢 **Olá seu P0BR3 N3C3SS1T4D0(A), já viu o novo vazamento do Honkai? r/{subreddit}**\n**{title}**\n{url}\n👤 por u/{author}",
    "Genshin_Impact_Leaks": "📢 **Ei viajante, tem um novo vazamento do Genshin Impact em r/{subreddit}!**\n**{title}**\n{url}\n👤 por u/{author}",
    "WutheringWavesLeaks": "📢 **O vento sussurra novos segredos de Wuthering Waves! r/{subreddit}**\n**{title}**\n{url}\n👤 por u/{author}",
    "Zenlesszonezeroleaks_": "📢 **Boas-vindas à Nova Eridu — vazamento fresquinho de r/{subreddit}!**\n**{title}**\n{url}\n👤 por u/{author}",
    "FortniteLeaks": "📢 **⚡ Novidades caindo do céu! Novo leak de Fortnite em r/{subreddit}**\n**{title}**\n{url}\n👤 por u/{author}",
    "MemesBrasil": "😂 **Novo post em r/{subreddit}!**\n**{title}**\n{url}\n👤 por u/{author}"
}

REDDIT_CLIENT_ID = os.environ["REDDIT_CLIENT_ID"]
REDDIT_CLIENT_SECRET = os.environ["REDDIT_CLIENT_SECRET"]
REDDIT_USER_AGENT = os.environ["REDDIT_USER_AGENT"]

# ==============================

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot rodando!")

def run_server():
    server = HTTPServer(("0.0.0.0", 10000), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# Inicializa o Reddit
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

def post_to_discord(webhook_url, title, url, author, subreddit):
    template = MESSAGES.get(subreddit, "📢 **Novo post em r/{subreddit}**\n**{title}**\n{url}\n👤 por u/{author}")
    content = template.format(subreddit=subreddit, title=title, url=url, author=author)
    r = requests.post(webhook_url, json={"content": content})
    if r.status_code != 204:
        print(f"Erro ao enviar para Discord ({subreddit}):", r.text)

def preload_recent_posts(conn, subreddit, webhook_url):
    """Envia os 20 posts mais recentes e marca os antigos como enviados"""
    print(f"Pré-carregando posts de r/{subreddit}...")
    posts = list(reddit.subreddit(subreddit).new(limit=100))  # pega até 100 posts recentes
    posts_to_send = posts[:50]  # os 20 mais recentes serão enviados
    posts_to_mark = posts[50:]   # o restante será marcado como já enviado

    # Marca os posts antigos como enviados
    for submission in posts_to_mark:
        conn.execute("INSERT OR IGNORE INTO sent(id) VALUES(?)", (submission.id,))
    conn.commit()

    # Envia os 20 mais recentes para o Discord
    for submission in reversed(posts_to_send):  # envia do mais antigo para o mais novo
        post_id = submission.id
        cur = conn.execute("SELECT 1 FROM sent WHERE id=?", (post_id,))
        if cur.fetchone():
            continue

        title = submission.title
        url = "https://reddit.com" + submission.permalink
        author = submission.author.name if submission.author else "[deleted]"
        print(f"Enviando post inicial em r/{subreddit}: {title}")

        post_to_discord(webhook_url, title, url, author, subreddit)
        conn.execute("INSERT OR IGNORE INTO sent(id) VALUES(?)", (post_id,))
        conn.commit()

def monitor_subreddit(subreddit_name, webhook_url):
    conn = sqlite3.connect("sent_posts.db")
    conn.execute("CREATE TABLE IF NOT EXISTS sent (id TEXT PRIMARY KEY)")
    conn.commit()

    preload_recent_posts(conn, subreddit_name, webhook_url)  # envia os 20 primeiros na primeira execução
    print(f"Monitorando r/{subreddit_name}...")

    subreddit = reddit.subreddit(subreddit_name)
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

    while True:
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Encerrando bot...")
