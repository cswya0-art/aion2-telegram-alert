import os
import json
import urllib.request
import urllib.parse

API_URL = (
    "https://api-community.plaync.com/aion2/board/cm_story_ko/"
    "article/search/moreArticle"
    "?isVote=true"
    "&moreSize=18"
    "&moreDirection=BEFORE"
    "&previousArticleId=0"
)

BASE_URL = "https://aion2.plaync.com/ko-kr/board/cm_story/view?articleId="
STATE_FILE = "last_cm_story.json"

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


def get_json(url):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/154.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": "https://aion2.plaync.com/",
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(
            response.read().decode("utf-8", errors="ignore")
        )


def find_articles(data):
    """
    API 응답에서 게시글 목록을 찾아낸다.
    API 응답 구조가 조금 달라져도 최대한 자동으로 탐색한다.
    """

    articles = []

    def walk(obj):
        if isinstance(obj, dict):

            # 게시글 객체로 보이는 경우
            article_id = (
                obj.get("articleId")
                or obj.get("id")
                or obj.get("articleID")
            )

            title = (
                obj.get("title")
                or obj.get("articleTitle")
                or obj.get("subject")
            )

            if article_id and title:
                articles.append({
                    "id": str(article_id),
                    "title": str(title)
                })

            for value in obj.values():
                walk(value)

        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(data)

    # 중복 제거
    result = []
    seen = set()

    for article in articles:
        article_id = article["id"]

        if article_id in seen:
            continue

        seen.add(article_id)
        result.append(article)

    return result


def get_cm_articles():
    print("CM 아지트 API 확인 중...")
    print(API_URL)

    try:
        data = get_json(API_URL)

    except Exception as e:
        print("❌ API 접속 실패:")
        print(e)
        return []

    articles = find_articles(data)

    if not articles:
        print("❌ API에서 게시글을 찾지 못했습니다.")
        print("API 응답:")
        print(json.dumps(data, ensure_ascii=False)[:5000])
        return []

    result = []

    for article in articles:
        article_id = article["id"]
        title = article["title"]

        url = BASE_URL + urllib.parse.quote(article_id)

        result.append({
            "id": article_id,
            "title": title,
            "url": url
        })

    return result


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
                "id": article["id"],
                "title": article["title"],
                "url": article["url"]
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

    api_url = (
        f"https://api.telegram.org/bot"
        f"{BOT_TOKEN}/sendMessage"
    )

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
        result = response.read().decode()

    print("텔레그램 전송 결과:")
    print(result)


def main():
    articles = get_cm_articles()

    if not articles:
        print("❌ CM 아지트 게시글을 가져오지 못했습니다.")
        return

    newest = articles[0]

    print()
    print("========================================")
    print("현재 최신 CM 아지트 글")
    print("ID:", newest["id"])
    print("제목:", newest["title"])
    print("주소:", newest["url"])
    print("========================================")
    print()

    old = load_state()

    # 최초 실행
    if old is None:
        save_state(newest)

        print(
            "✅ 최초 실행 완료."
            " 현재 최신 글을 기준점으로 저장했습니다."
        )
        print("📢 최초 실행에서는 Telegram 알림을 보내지 않습니다.")

        return

    old_id = str(old.get("id", ""))

    # 새로운 글
    if old_id != newest["id"]:

        print("🚨 새 CM 아지트 글 발견!")

        send_telegram(
            newest["title"],
            newest["url"]
        )

        save_state(newest)

        print("✅ Telegram 알림 전송 완료.")

    else:
        print("새 글이 없습니다.")


if __name__ == "__main__":
    main()
