import os
import feedparser
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ---------- CONFIG FROM ENVIRONMENT ----------
GMAIL_ADDRESS      = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
FINANCE_NEWS_TO    = os.environ["FINANCE_NEWS_TO"]

# Google News RSS: general finance news from the last 24 hours
FEEDS = [
    "https://news.google.com/rss/search?q=finance+when:1d&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=stock+market+when:1d&hl=en-US&gl=US&ceid=US:en",
]

MAX_ARTICLES = 40


def fetch_articles():
    """Fetch general finance news from Google News."""
    articles = []
    seen = set()
    for url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:25]:
                title = entry.title.strip()
                if title in seen:
                    continue
                seen.add(title)

                # Google News puts the publisher name in entry.source
                source_name = "Google News"
                if hasattr(entry, "source") and entry.source:
                    source_name = entry.source.get("title", "Google News")

                articles.append({
                    "title": title,
                    "link": entry.link,
                    "source": source_name,
                })
        except Exception as e:
            print(f"Feed failed {url}: {e}")
    return articles[:MAX_ARTICLES]


def build_html_table(articles):
    """Build an HTML table of all finance news."""
    if not articles:
        return (
            f"<html><body>"
            f"<h2>General Finance News — {datetime.now().strftime('%A, %B %d, %Y')}</h2>"
            f"<p>No articles found today.</p>"
            f"</body></html>"
        )

    rows = ""
    for a in articles:
        rows += (
            f"<tr>"
            f"<td><a href='{a['link']}'>{a['title']}</a></td>"
            f"<td width='180' style='vertical-align: top; color: #666;'>{a['source']}</td>"
            f"</tr>"
        )

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; font-size: 14px;">
    <h2>General Finance News — {datetime.now().strftime('%A, %B %d, %Y')}</h2>
    <p>{len(articles)} headlines from the last 24 hours.</p>
    <table border="1" cellpadding="8" cellspacing="0"
           style="border-collapse: collapse; font-family: Arial, sans-serif; font-size: 14px; width: 100%;">
      <tr style="background-color: #f0f0f0;">
        <th align="left">Headline</th>
        <th align="left">Source</th>
      </tr>
      {rows}
    </table>
    <p style="font-size: 12px; color: #888; margin-top: 20px;">
      Links are Google News redirects. Clicking will take you to the publisher's site.
    </p>
    </body>
    </html>
    """
    return html


def send_email(subject, html_body):
    """Send via Gmail SMTP."""
    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_ADDRESS
    msg["To"] = FINANCE_NEWS_TO
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.send_message(msg)


def main():
    print("Fetching general finance news...")
    articles = fetch_articles()
    print(f"Got {len(articles)} articles.")

    html = build_html_table(articles)
    subject = f"General Finance News — {datetime.now().strftime('%b %d %Y')}"
    send_email(subject, html)
    print("Sent!")


if __name__ == "__main__":
    main()
