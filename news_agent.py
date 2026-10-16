import os
import feedparser
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ---------- CONFIG FROM ENVIRONMENT ----------
GEMINI_API_KEY    = os.environ["GEMINI_API_KEY"]
GMAIL_ADDRESS     = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD= os.environ["GMAIL_APP_PASSWORD"]
GMAIL_TO          = os.environ["GMAIL_TO"]

# Gemini model to use
GEMINI_MODEL = "gemini-3.5-flash-lite"

# Free RSS feeds — no API key needed
FEEDS = [
    # Original feeds
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC,^DJI,^IXIC&region=US&lang=en-US",
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",   # CNBC Top News
    "https://www.cnbc.com/id/10000664/device/rss/rss.html",     # CNBC Markets
    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",            # WSJ Markets
    "https://seekingalpha.com/market_currents.xml",             # Seeking Alpha

    # New feeds added
    "https://feeds.content.dowjones.io/public/rss/mw_bulletins",  # MarketWatch Bulletins
    "https://feeds.bloomberg.com/markets/news.rss",               # Bloomberg Markets [citation:2][citation:20]
    "https://www.ft.com/rss/markets",                             # Financial Times Markets [citation:3]
    "https://www.economist.com/finance-and-economics/rss.xml",    # The Economist Finance [citation:4]
    "https://eulerpool.com/news/feed.xml",                        # Eulerpool News Agency [citation:5]
    "https://www.investing.com/rss/news.rss",                     # Investing.com [citation:15]
    "https://www.forbes.com/investing/feed/",                     # Forbes Investing [citation:7]
]

MAX_HEADLINES = 30  # Bumped up slightly to accommodate more sources


def fetch_headlines():
    """Pull recent headlines from RSS feeds."""
    headlines = []
    seen = set()
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:  # Limit per feed to avoid one source dominating
                title = entry.title.strip()
                if title not in seen:
                    seen.add(title)
                    headlines.append({
                        "title": title,
                        "link": entry.link,
                        "source": feed.feed.get("title", url),
                    })
        except Exception as e:
            print(f"Feed failed {url}: {e}")
    return headlines[:MAX_HEADLINES]


def summarize_with_gemini(headlines):
    """Ask Gemini to write the briefing."""
    today = datetime.now().strftime("%A, %B %d, %Y")

    news_text = "\n".join(
        f"{i+1}. [{h['source']}] {h['title']}"
        for i, h in enumerate(headlines)
    )

    prompt = f"""You are a financial news analyst. Today is {today}.

Here are today's top stock market headlines:

{news_text}

Write a concise morning briefing (max 300 words) for a retail investor:
1. Start with a 2-sentence "market mood" summary.
2. List the 5 most market-moving stories, each with a 1-2 sentence takeaway on why it matters.
3. End with a 1-sentence "what to watch today."
Plain English. No hype. No disclaimers."""

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )

    response = requests.post(
        url,
        headers={"Content-Type": "application/json"},
        json={
            "contents": [
                {"parts": [{"text": prompt}]}
            ]
        },
        timeout=60,
    )
    response.raise_for_status()

    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def send_email(subject, body):
    """Send the briefing via Gmail SMTP."""
    msg = MIMEMultipart()
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = GMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)


def main():
    print("Fetching headlines...")
    headlines = fetch_headlines()
    print(f"Got {len(headlines)} headlines.")

    if not headlines:
        send_email(
            "Market Briefing — no headlines",
            "No market headlines could be fetched today.",
        )
        return

    print("Summarizing with Gemini...")
    summary = summarize_with_gemini(headlines)

    subject = f"Morning Market Briefing — {datetime.now().strftime('%b %d %Y')}"
    body = (
        f"Morning Market Briefing\n"
        f"{datetime.now().strftime('%A, %B %d, %Y')}\n"
        f"{'-' * 40}\n\n"
        f"{summary}\n\n"
        f"{'-' * 40}\n"
        f"Sources: Yahoo, CNBC, WSJ, Seeking Alpha, MarketWatch, Bloomberg, FT, Economist, Eulerpool, Investing.com, Forbes\n"
    )

    send_email(subject, body)
    print("Sent!")


if __name__ == "__main__":
    main()
