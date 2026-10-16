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
    "https://feeds.bloomberg.com/markets/news.rss",               # Bloomberg Markets 
    "https://www.ft.com/rss/markets",                             # Financial Times Markets 
    "https://www.economist.com/finance-and-economics/rss.xml",    # The Economist Finance 
    "https://eulerpool.com/news/feed.xml",                        # Eulerpool News Agency 
    "https://www.investing.com/rss/news.rss",                     # Investing.com 
    "https://www.forbes.com/investing/feed/",                     # Forbes Investing 
]

MAX_HEADLINES = 30

# ---------- TICKER MAP ----------
# Maps ticker symbol to a list of keywords to match in headlines
TICKER_MAP = {
    "JPM":   ["JPMorgan", "JP Morgan", "JPM"],
    "SPCX":  ["SpaceX", "Space Exploration", "SPCX"],
    "TSLA":  ["Tesla", "TSLA"],
    "BYDDY": ["BYD", "BYDDY"],
    "LGFRY": ["Longfor", "LGFRY"],
    "ORCL":  ["Oracle", "ORCL"],
    "CRM":   ["Salesforce", "CRM"],
    "GOOG":  ["Google", "Alphabet", "GOOG"],
    "AAPL":  ["Apple", "AAPL"],
    "AMZN":  ["Amazon", "AMZN"],
    "NVDA":  ["NVIDIA", "Nvidia", "NVDA"],
    "AMD":   ["Advanced Micro Devices", "AMD"],
    "INTC":  ["Intel", "INTC"],
    "BA":    ["Boeing", "BA"],
    "SNOW":  ["Snowflake", "SNOW"],
    "PLTR":  ["Palantir", "PLTR"],
    "QS":    ["QuantumScape", "QS"],
    "BABA":  ["Alibaba", "BABA"],
    "UNH":   ["UnitedHealth", "United Health", "UNH"],
    "RBLX":  ["Roblox", "RBLX"],
    "RKLB":  ["Rocket Lab", "RKLB"],
    "SMR":   ["NuScale", "SMR"],
    "SOFI":  ["SoFi", "SOFI"],
    "JOBY":  ["Joby", "JOBY"],
    "ACHR":  ["Archer", "ACHR"],
}


def fetch_headlines():
    """Pull recent headlines from RSS feeds."""
    headlines = []
    seen = set()
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
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


def filter_by_tickers(headlines):
    """Return only headlines that mention any of our tracked tickers."""
    matched = []
    for h in headlines:
        title_lower = h["title"].lower()
        for ticker, keywords in TICKER_MAP.items():
            if any(kw.lower() in title_lower for kw in keywords):
                matched.append({
                    "ticker": ticker,
                    "title": h["title"],
                    "link": h["link"],
                    "source": h["source"],
                })
                break  # only tag once per headline
    return matched


def build_html_table(matches):
    """Build an HTML table of matched headlines, grouped by ticker."""
    if not matches:
        return "<p>No headlines matched your tracked tickers today.</p>"

    # Group by ticker
    grouped = {}
    for m in matches:
        grouped.setdefault(m["ticker"], []).append(m)

    rows = ""
    for ticker in sorted(grouped.keys()):
        items = grouped[ticker]
        # Ticker header row
        rows += (
            f"<tr style='background-color: #e8f0fe;'>"
            f"<td colspan='3'><b>{ticker}</b> — {len(items)} headline(s)</td>"
            f"</tr>"
        )
        for m in items:
            rows += (
                f"<tr>"
                f"<td width='60'>{m['ticker']}</td>"
                f"<td><a href='{m['link']}'>{m['title']}</a></td>"
                f"<td width='140'>{m['source']}</td>"
                f"</tr>"
            )

    html = f"""
    <html>
    <body>
    <h2>Tracked Stock News — {datetime.now().strftime('%A, %B %d, %Y')}</h2>
    <p>{len(matches)} headlines matched your {len(TICKER_MAP)} tracked tickers.</p>
    <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; font-family: Arial, sans-serif; font-size: 14px;">
      <tr style="background-color: #f0f0f0;">
        <th align="left">Ticker</th>
        <th align="left">Headline</th>
        <th align="left">Source</th>
      </tr>
      {rows}
    </table>
    </body>
    </html>
    """
    return html


def send_email(subject, html_body):
    """Send the briefing via Gmail SMTP."""
    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = GMAIL_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)


def main():
    print("Fetching headlines...")
    headlines = fetch_headlines()
    print(f"Got {len(headlines)} headlines.")

    matches = filter_by_tickers(headlines)
    print(f"Matched {len(matches)} headlines to tracked tickers.")

    html = build_html_table(matches)

    subject = f"Tracked Stock News — {datetime.now().strftime('%b %d %Y')}"
    send_email(subject, html)
    print("Sent!")


if __name__ == "__main__":
    main()
