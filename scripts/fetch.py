#!/usr/bin/env python3
"""Fetch public data from The Grove (Discourse) and the Rainmatter Foundation partners page.

Writes raw responses to data/raw/ (not committed). Only public, unauthenticated
endpoints are read, with a pause between requests.
"""
import json, os, sys, time, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
GROVE = "https://grove.rainmatter.org"
PARTNERS_URL = "https://rainmatter.org/partners"
UA = "grove-landscape/1.0 (+https://github.com/Ashwask)"
PAUSE = 0.5
UPDATES_CATEGORY = ("updates", 21)


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, text/html"})
            with urllib.request.urlopen(req, timeout=40) as r:
                return r.read()
        except Exception as e:  # retry with backoff, then give up loudly
            if i == tries - 1:
                raise
            time.sleep(4 * (i + 1))
    return b""


def get_json(url):
    data = json.loads(get(url))
    time.sleep(PAUSE)
    return data


def save(name, obj):
    path = os.path.join(RAW, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


def load(name):
    path = os.path.join(RAW, name)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    os.makedirs(RAW, exist_ok=True)
    save("about.json", get_json(GROVE + "/about.json"))
    save("categories.json", get_json(GROVE + "/categories.json"))

    # every public topic, newest first
    topics, page = {}, 0
    while True:
        d = get_json(f"{GROVE}/latest.json?order=created&no_definitions=true&page={page}")
        ts = d["topic_list"]["topics"]
        if not ts:
            break
        users = {u["id"]: u for u in d.get("users", [])}
        for t in ts:
            op = next((x for x in t.get("posters", []) if "Original Poster" in (x.get("description") or "")), None)
            u = users.get(op["user_id"]) if op else None
            t["_op"] = u["username"] if u else None
            t["_op_tl"] = u.get("trust_level") if u else None
            topics[t["id"]] = t
        page += 1
    save("topics.json", list(topics.values()))
    print("public topics:", len(topics))

    # every topic in Rainmatter Partner Updates
    upd, page = {}, 0
    slug, cid = UPDATES_CATEGORY
    while True:
        d = get_json(f"{GROVE}/c/{slug}/{cid}.json?page={page}")
        ts = d["topic_list"]["topics"]
        if not ts:
            break
        for t in ts:
            upd[t["id"]] = t
        page += 1
    save("updates_index.json", list(upd.values()))
    print("partner update topics:", len(upd))

    # full post stream of each update topic; refetch only when it has new activity
    n = 0
    for tid, t in sorted(upd.items()):
        name = f"threads/{tid}.json"
        old = load(name)
        if old and old.get("_bumped_at") == t.get("bumped_at") and old.get("_posts_count") == t.get("posts_count"):
            continue
        d = get_json(f"{GROVE}/t/{tid}.json")
        posts = d["post_stream"]["posts"]
        have = {p["id"] for p in posts}
        rest = [i for i in d["post_stream"]["stream"] if i not in have]
        for k in range(0, len(rest), 20):
            q = "&".join("post_ids[]=%d" % i for i in rest[k:k + 20])
            more = get_json(f"{GROVE}/t/{tid}/posts.json?{q}")
            posts += more["post_stream"]["posts"]
        slim = {
            "id": tid, "title": d["title"], "slug": d["slug"], "created_at": d["created_at"],
            "views": d["views"], "like_count": d.get("like_count", 0), "posts_count": d["posts_count"],
            "_bumped_at": t.get("bumped_at"), "_posts_count": t.get("posts_count"),
            "posts": [{"n": p["post_number"], "u": p["username"], "name": p.get("name") or "",
                       "at": p["created_at"], "staff": bool(p.get("staff")), "cooked": p["cooked"]}
                      for p in sorted(posts, key=lambda p: p["post_number"]) if p.get("post_type", 1) == 1],
        }
        save(name, slim)
        n += 1
    print("threads fetched:", n)

    html = get(PARTNERS_URL).decode("utf-8")
    with open(os.path.join(RAW, "partners.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("partners page bytes:", len(html))
    save("fetched_at.json", {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})


if __name__ == "__main__":
    main()
