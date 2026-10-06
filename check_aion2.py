import os
import json
import re
import urllib.request
import urllib.parse
from html.parser import HTMLParser

LIST_URL = "https://aion2.plaync.com/ko-kr/board/cm_story/list"
STATE_FILE = "last_cm_story.json"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.iframes = []
        self.current = None
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "iframe":
            src = attrs.get("src")
            if src:
                self.iframes.append(src)

        if tag == "a":
            href = attrs.get("href", "")
            if "articleId=" in href:
                self.current = href
                self.text = []

    def handle_data(self, data):
        if self.current:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current:
            title = " ".join("".join(self.text).split())

            if title:
                self.links.append((title, self.current))

            self.current = None
            self.text = []


def get_html(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/154.0 Safari/537.36"
            )
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def absolute_url(url):
    return urllib.parse.urljoin(LIST_URL, url)


def find_articles(html):
    parser = Parser()
    parser.feed(html)

    articles = []

    for title, url in parser.links:
        url = absolute_url(url)

        if "/board/cm_story/" not in url:
            continue

        if not any(x[1] == url for x in articles):
            articles.append((title, url))

    return articles


def get_cm_articles():
    print("CM 아지트 확인 중...")

    main_html = get_html(LIST_URL)

    # 먼저 메인 페이지에서 직접 게시글을 찾는다.
    articles = find_articles(main_html)

    if articles:
        return articles

    # CM 아지트가 iframe으로 구성되어 있으면 iframe도 확인한다.
    parser = Parser()
    parser.feed(main_html)

    for iframe in parser.iframes:
        iframe_url = absolute_url(iframe)

        print("iframe 확인:", iframe_url)

        try:
            iframe_html = get_html(iframe_url)
            articles = find_articles(iframe_html)

            if articles:
                return articles

        except Exception as e:
            print("iframe 확인 실패:", e)

    return []


def load_state():
    if not os.path.exists(STATE_FILE):
        return None

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_state(article):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "title": article[0],
                "url": article[1]
            },
            f,
            ensure_ascii=False,
            indent=2
        )


def send_telegram(title, url):
    message = (
        "🔔 AION2 CM 아지트 새 글\n\n"
        f"📌 {title}\n\n"
        f"🔗 {url}"
    )

    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": False
    }).encode()

    request = urllib.request.Request(
        api_url,
        data=data,
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        print("텔레그램 전송 결과:")
        print(response.read().decode())


def main():
    articles = get_cm_articles()

    if not articles:
        print("❌ CM 아지트 게시글을 찾지 못했습니다.")
        return

    newest = articles[0]

    print("현재 최신 CM 아지트 글:")
    print("제목:", newest[0])
    print("주소:", newest[1])

    old = load_state()

    # 최초 실행
    if old is None:
        save_state(newest)
        print("✅ 최초 실행 완료. 현재 글을 기준점으로 저장했습니다.")
        return

    # 새 글 발견
    if old.get("url") != newest[1]:

        print("🚨 새 CM 아지트 글 발견!")

        send_telegram(
            newest[0],
            newest[1]
        )

        save_state(newest)

    else:
        print("새 글이 없습니다.")


if __name__ == "__main__":
    main()
