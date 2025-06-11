# rss_parser.py
import feedparser
import html2text
import json
from pathlib import Path

RSS_FEEDS = {
    "HerbalAcademy": "https://theherbalacademy.com/feed/",
    "LearningHerbs": "https://learningherbs.com/feed/",
    "ChestnutSchool": "https://chestnutherbs.com/feed/",
    "WellnessMama": "https://wellnessmama.com/feed/",
    "DrAxe": "https://draxe.com/feed/",
    "ChalkboardMag": "https://thechalkboardmag.com/feed",
    "PlumDeluxe": "https://www.plumdeluxe.com/blog/feed",
    "TeaEpicure": "https://www.teaepicure.com/feed/",
    "NCCIH": "https://www.nccih.nih.gov/news/rss"
}

output_dir = Path("feeds_jsonl")
output_dir.mkdir(exist_ok=True)

md_cleaner = html2text.HTML2Text()
md_cleaner.ignore_links = True
md_cleaner.ignore_images = True

def fetch_rss_to_jsonl():
    all_items = []
    for name, url in RSS_FEEDS.items():
        parsed_feed = feedparser.parse(url)
        items = []

        for entry in parsed_feed.entries:
            content = entry.get("summary", "") or entry.get("content", [{}])[0].get("value", "")
            cleaned = md_cleaner.handle(content).replace("\n", " ").strip()
            if len(cleaned) < 100:
                continue
            item = {
                "id": entry.get("id") or entry.get("link"),
                "title": entry.get("title"),
                "link": entry.get("link"),
                "published": entry.get("published", ""),
                "source": name,
                "content": cleaned
            }
            items.append(item)

        # Save per-feed JSONL
        if items:
            jsonl_path = output_dir / f"{name}.jsonl"
            with open(jsonl_path, "w", encoding="utf-8") as f:
                for item in items:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            print(f"✅ {len(items)} saved to {jsonl_path}")
            all_items.extend(items)

    return all_items
