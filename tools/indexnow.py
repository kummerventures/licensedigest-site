#!/usr/bin/env python3
"""Ping IndexNow (Bing, Yandex, Seznam, Naver, Yep) about changed pages.

Usage:
  indexnow.py --base OLD --head NEW   URLs for .html/.xml files changed between commits
  indexnow.py --all                   every URL in sitemap.xml
  add --dry-run to print the payload and send nothing (also runs a self-check).
"""
import argparse, json, re, subprocess, sys, urllib.request, urllib.error

HOST = "licensedigest.com"
KEY = "337bc4cb8ab58100a006c3d8f02ac5fc"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
ENDPOINT = "https://api.indexnow.org/indexnow"


def sitemap_urls(path="sitemap.xml"):
    with open(path, encoding="utf-8") as f:
        return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", f.read())


def file_to_url(path):
    """Map a changed repo file to its public URL, or None."""
    if path.endswith("index.html"):
        d = path[: -len("index.html")]
        return f"https://{HOST}/{d}"
    if path.endswith(".html"):
        return f"https://{HOST}/{path}"  # e.g. privacy.html
    return None


def changed_urls(base, head, sitemap):
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=AMR", base, head],
        check=True, capture_output=True, text=True).stdout.split()
    known = set(sitemap)
    urls = []
    for p in out:
        if p == "sitemap.xml":
            urls.append(f"https://{HOST}/sitemap.xml")
            continue
        u = file_to_url(p)
        if u:
            urls.append(u)
    # keep only our host; privacy/terms may not be in the sitemap, that is fine
    urls = [u for u in urls if u.startswith(f"https://{HOST}/")]
    return sorted(set(urls)), known


def self_check():
    assert file_to_url("index.html") == f"https://{HOST}/"
    assert file_to_url("fl/lee/index.html") == f"https://{HOST}/fl/lee/"
    assert file_to_url("privacy.html") == f"https://{HOST}/privacy.html"
    assert file_to_url("media/x.png") is None
    assert file_to_url("robots.txt") is None
    assert len(KEY) == 32 and re.fullmatch(r"[0-9a-f]{32}", KEY)
    print("self-check ok", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--base")
    ap.add_argument("--head", default="HEAD")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.dry_run:
        self_check()
    sm = sitemap_urls()
    if a.all:
        urls = sm
    elif a.base:
        urls, _ = changed_urls(a.base, a.head, sm)
    else:
        ap.error("give --all or --base")
    if not urls:
        print("no URLs to submit")
        return 0
    payload = {"host": HOST, "key": KEY, "keyLocation": KEY_LOCATION, "urlList": urls}
    if a.dry_run:
        print(json.dumps(payload, indent=2))
        return 0
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            status = r.status
    except urllib.error.HTTPError as e:
        status = e.code
    print(f"IndexNow status {status} for {len(urls)} URLs")
    return 0 if status in (200, 202) else 1


if __name__ == "__main__":
    sys.exit(main())
