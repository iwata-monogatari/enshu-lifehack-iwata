#!/usr/bin/env python3
"""Submit all URLs in sitemap.xml to IndexNow."""
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOST = "iwata.enshu-lifehack.com"
KEY = "9aacdc8ce3b94cb9ba20a4b29fe99f59"

urls = re.findall(r"<loc>([^<]+)</loc>", (ROOT / "sitemap.xml").read_text(encoding="utf-8"))
payload = json.dumps({
    "host": HOST,
    "key": KEY,
    "keyLocation": f"https://{HOST}/{KEY}.txt",
    "urlList": urls,
}).encode("utf-8")
request = urllib.request.Request(
    "https://api.indexnow.org/indexnow",
    data=payload,
    headers={"Content-Type": "application/json; charset=utf-8"},
    method="POST",
)
with urllib.request.urlopen(request, timeout=60) as response:
    print(f"IndexNow accepted {len(urls)} URLs (HTTP {response.status}).")
