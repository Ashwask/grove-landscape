#!/usr/bin/env python3
"""Fetch the first page of every public Grove topic outside Partner Updates (opening post and up to 19 replies).

Raw output goes to data/raw/forum/ (not committed). Used for the one-time reading of the wider forum.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import GROVE, RAW, get_json, load, save

def main():
    topics = load("topics.json")
    done = 0
    for t in topics:
        if t["category_id"] == 21:
            continue
        name = f"forum/{t['id']}.json"
        if load(name):
            continue
        try:
            d = get_json(f"{GROVE}/t/{t['id']}.json")
        except Exception as e:
            print("skip", t["id"], str(e)[:60]); continue
        save(name, {"id": t["id"], "title": d["title"], "slug": d["slug"], "category_id": d.get("category_id"),
                    "created_at": d["created_at"], "views": d["views"], "like_count": d.get("like_count", 0),
                    "posts_count": d["posts_count"],
                    "posts": [{"n": p["post_number"], "u": p["username"], "staff": bool(p.get("staff")), "tl": p.get("trust_level"),
                               "at": p["created_at"], "likes": sum(a.get("count", 0) for a in p.get("actions_summary", []) if a.get("id") == 2),
                               "cooked": p["cooked"]} for p in d["post_stream"]["posts"] if p.get("post_type", 1) == 1]})
        done += 1
    print("forum topics fetched:", done)

if __name__ == "__main__":
    main()
