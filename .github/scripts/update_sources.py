import feedparser, json, os
from datetime import datetime

# === Pfade relativ zum Repo ===
BMF_PATH = "bmf/latest.json"
BFH_PATH = "bfh/cases.json"

# === RSS-Feeds ===
BMF_FEED = "https://www.bundesfinanzministerium.de/SiteGlobals/Forms/BMF_Schreiben/Steuerrecht/BMF_Schreiben_RSS.xml"
BFH_FEED = "https://www.rechtsprechung-im-internet.de/RSS/BFH.xml"

def update_feed(feed_url, max_items=10):
    parsed = feedparser.parse(feed_url)
    data = []
    for entry in parsed.entries[:max_items]:
        data.append({
            "title": entry.get("title", ""),
            "date": entry.get("published", ""),
            "url": entry.get("link", ""),
            "source": feed_url.split("/")[2]
        })
    return data

def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    print("📡 Updating BMF and BFH data...")
    bmf_data = update_feed(BMF_FEED)
    bfh_data = update_feed(BFH_FEED)
    write_json(BMF_PATH, bmf_data)
    write_json(BFH_PATH, bfh_data)
    print("✅ Updated successfully at", datetime.now())
