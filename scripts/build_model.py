#!/usr/bin/env python3
"""Turn the raw fetch (data/raw/) plus the editorial registry into model.json.

Everything in the model traces to one of three public sources:
  1. rainmatter.org/partners  (partner name, year, description, website)
  2. grove.rainmatter.org     (topics, posts, counts)
  3. data/registry.json       (editorial role and domain buckets, read from 1)
"""
import collections, datetime, html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
GROVE = "https://grove.rainmatter.org"
GROVE_MIN_MENTIONS = 3  # a state counts as "named in Grove updates" from this many mentions

# Place names that resolve to one state. State names themselves are matched too.
PLACES = {
    "Andaman and Nicobar Islands": ["Andaman", "Nicobar", "Port Blair"],
    "Andhra Pradesh": ["Anantapur", "Visakhapatnam", "Vijayawada", "Araku", "Chittoor", "Tirupati"],
    "Arunachal Pradesh": ["Itanagar", "Pakke", "Tawang"],
    "Assam": ["Guwahati", "Jorhat", "Majuli", "Kaziranga", "Dibrugarh", "Tezpur", "Silchar"],
    "Bihar": ["Patna", "Purnea", "Gaya", "Muzaffarpur"],
    "Chhattisgarh": ["Raipur", "Bastar", "Bilaspur"],
    "Delhi": ["New Delhi"],
    "Goa": ["Panaji", "Panjim"],
    "Gujarat": ["Kutch", "Kachchh", "Ahmedabad", "Bhuj", "Surat", "Vadodara", "Banni"],
    "Haryana": ["Gurugram", "Gurgaon", "Faridabad", "Sonepat"],
    "Himachal Pradesh": ["Shimla", "Dharamshala", "Dharamsala", "Spiti", "Kullu", "Manali"],
    "Jammu and Kashmir": ["Srinagar", "Kashmir"],
    "Jharkhand": ["Ranchi", "Jamshedpur", "Hazaribagh", "Gumla", "Khunti"],
    "Karnataka": ["Bengaluru", "Bangalore", "Mysuru", "Mysore", "Mandya", "Kodagu", "Coorg", "Bannerghatta",
                  "Yadgir", "Kalburgi", "Kalaburagi", "Chamarajanagar", "BR Hills", "Tumakuru", "Kolar",
                  "Devanahalli", "Hubballi", "Dharwad", "Belagavi", "Raichur", "Ramanagara", "Chikkaballapur",
                  "Saragur", "Shivamogga", "Udupi", "Mangaluru", "Hesaraghatta"],
    "Kerala": ["Wayanad", "Kannur", "Kochi", "Thiruvananthapuram", "Kozhikode", "Palakkad", "Thrissur", "Idukki"],
    "Ladakh": ["Leh", "Kargil"],
    "Madhya Pradesh": ["Jhabua", "Alirajpur", "Bhopal", "Indore", "Mandla", "Kanha", "Jabalpur"],
    "Maharashtra": ["Mumbai", "Pune", "Gadchiroli", "Ratnagiri", "Vidarbha", "Marathwada", "Satara", "Nashik",
                    "Nagpur", "Sindhudurg", "Palghar"],
    "Manipur": ["Imphal"],
    "Meghalaya": ["Shillong", "Garo Hills", "Khasi Hills"],
    "Mizoram": ["Aizawl"],
    "Nagaland": ["Kohima", "Dimapur"],
    "Odisha": ["Bhubaneswar", "Ganjam", "Koraput", "Kalahandi", "Puri", "Mayurbhanj", "Kandhamal", "Rayagada",
               "Sambalpur", "Chilika", "Cuttack"],
    "Puducherry": ["Pondicherry"],
    "Punjab": ["Amritsar", "Ludhiana"],
    "Rajasthan": ["Jaipur", "Udaipur", "Banswara", "Jodhpur", "Jaisalmer", "Bikaner"],
    "Sikkim": ["Gangtok"],
    "Tamil Nadu": ["Chennai", "Gudalur", "Mudumalai", "Nilgiris", "Nilgiri", "Hosur", "Coimbatore", "Madurai",
                   "Kanyakumari", "Kotagiri", "Ooty", "Valparai", "Anamalai"],
    "Telangana": ["Hyderabad", "Warangal"],
    "Tripura": ["Agartala"],
    "Uttar Pradesh": ["Purvanchal", "Deoria", "Lucknow", "Gorakhpur", "Kushinagar", "Varanasi", "Kanpur", "Noida"],
    "Uttarakhand": ["Dehradun", "Rishikesh", "Binsar", "Nainital", "Almora", "Haridwar", "Mussoorie"],
    "West Bengal": ["Kolkata", "Sundarbans", "Sunderbans", "Purulia", "Bankura", "Jhargram", "Darjeeling", "Bengal"],
}
STATES = ["Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chandigarh",
          "Chhattisgarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Goa", "Gujarat", "Haryana",
          "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand", "Karnataka", "Kerala", "Ladakh", "Lakshadweep",
          "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Puducherry",
          "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
          "West Bengal"]
STATE_RX = {}
for s in STATES:
    names = [s] + PLACES.get(s, [])
    if s == "Odisha":
        names.append("Orissa")
    STATE_RX[s] = re.compile(r"(?<![A-Za-z])(?:" + "|".join(re.escape(n) for n in names) + r")(?![a-z])")

OPEN_CATEGORIES = {"Funding": "call", "Collaboration": "call", "Small grants": "call", "Green Jobs": "job", "Events": "event"}
OPEN_DAYS = 60       # how far back "open now" looks
AWAIT_DAYS = 60      # a partner update this recent with no reply after it is "waiting for a reply"
MIN_TRUST = 1        # forum trust level of the poster; level 0 is a brand-new account


def load(name):
    with open(os.path.join(RAW, name), encoding="utf-8") as f:
        return json.load(f)


def text_of(cooked):
    t = re.sub(r"<aside.*?</aside>", " ", cooked, flags=re.S)  # drop quoted replies and link previews
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def states_in(text):
    out = {}
    for s, rx in STATE_RX.items():
        n = len(rx.findall(text))
        if n:
            out[s] = n
    return out


def place_terms(text):
    """For each state named in the text, the place names that matched, most specific first."""
    out = {}
    for s, rx in STATE_RX.items():
        found = list(dict.fromkeys(rx.findall(text)))
        if found:
            out[s] = [t for t in found if t not in (s, "Bengal", "Orissa")]
    return out


_GEO_PATH = os.path.join(ROOT, "data", "geocode.json")
_geo = json.load(open(_GEO_PATH, encoding="utf-8")) if os.path.exists(_GEO_PATH) else {}


def geocode(place, state):
    """Point for a place in a state, from OpenStreetMap's Nominatim. Cached in data/geocode.json."""
    key = f"{place}|{state}"
    if key not in _geo:
        import time, urllib.parse, urllib.request
        q = f"{place}, {state}, India" if place != state else f"{state}, India"
        url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
            {"q": q, "format": "json", "limit": 1, "countrycodes": "in"})
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "grove-landscape/1.0 (+https://github.com/Ashwask)"})
            hit = json.loads(urllib.request.urlopen(req, timeout=30).read())
            _geo[key] = [round(float(hit[0]["lat"]), 4), round(float(hit[0]["lon"]), 4)] if hit else None
        except Exception:
            return None  # try again at the next build rather than caching a failure
        time.sleep(1.1)
        with open(_GEO_PATH, "w", encoding="utf-8") as f:
            json.dump(_geo, f, ensure_ascii=False, indent=1, sort_keys=True)
    return _geo[key]


def parse_partners(page):
    out = []
    for m in re.finditer(r'<li data-partner data-year="(\d+)"(.*?)</li>', page, re.S):
        year, body = int(m.group(1)), m.group(2)
        a = re.search(r'<h3[^>]*><a href="([^"]*)"[^>]*>(.*?)<span', body, re.S)
        if a:
            url, name = a.group(1), a.group(2)
        else:
            h = re.search(r"<h3[^>]*>(.*?)</h3>", body, re.S)
            url, name = "", re.sub(r"<.*?>", "", h.group(1))
        p = re.search(r"</h3><p[^>]*>(.*?)</p>", body, re.S)
        desc = html.unescape(re.sub(r"<.*?>", "", p.group(1))).strip() if p else ""
        out.append({"name": html.unescape(name).strip(), "year": year, "url": url, "desc": desc})
    return out


def days_between(a, b):
    return (b - a).days


def when(s):
    return datetime.datetime.strptime(s[:19], "%Y-%m-%dT%H:%M:%S")


def main():
    reg = json.load(open(os.path.join(ROOT, "data", "registry.json"), encoding="utf-8"))
    fetched = load("fetched_at.json")["at"]
    now = when(fetched)
    about = load("about.json")["about"]
    cats = {c["id"]: c["name"] for c in load("categories.json")["category_list"]["categories"]}
    topics = load("topics.json")
    upd_index = {t["id"]: t for t in load("updates_index.json")}
    threads = {}
    for tid in upd_index:
        p = os.path.join(RAW, "threads", f"{tid}.json")
        if os.path.exists(p):
            threads[tid] = json.load(open(p, encoding="utf-8"))
    staff = {p["u"] for th in threads.values() for p in th["posts"] if p["staff"]}

    listed = parse_partners(open(os.path.join(RAW, "partners.html"), encoding="utf-8").read())
    if len(listed) < 40:
        sys.exit("partners page parsed to %d rows; layout probably changed, refusing to publish" % len(listed))
    role_group = {r: g["id"] for g in reg["groups"] for r in g["roles"]}

    # ---- match Partner Updates threads to listed partners
    rules = []
    for p in listed:
        r = reg["partners"].get(p["name"])
        if r:
            rules.append((p["name"], set(r.get("users", [])), re.compile(r["title"]) if r.get("title") else None))
    by_partner, unmatched = collections.defaultdict(list), []
    for tid, th in threads.items():
        if not th["posts"] or upd_index[tid].get("pinned"):
            continue
        op = th["posts"][0]["u"]
        hit = next((n for n, users, rx in rules if op in users), None)  # organisation-named account first
        if not hit:
            hit = next((n for n, users, rx in rules if rx and rx.search(th["title"])), None)
        (by_partner[hit] if hit else unmatched).append(th)
    # an account whose matched threads all belong to one partner posts for that partner
    owner = collections.defaultdict(set)
    for name, ths in by_partner.items():
        for th in ths:
            owner[th["posts"][0]["u"]].add(name)
    still = []
    for th in unmatched:
        u = th["posts"][0]["u"]
        if len(owner.get(u, ())) == 1 and u not in staff:
            by_partner[next(iter(owner[u]))].append(th)
        else:
            still.append(th)
    unmatched = still

    # accounts that speak for each partner
    accounts = {}
    for p in listed:
        acc = set((reg["partners"].get(p["name"]) or {}).get("users", []))
        acc |= {th["posts"][0]["u"] for th in by_partner.get(p["name"], [])}
        accounts[p["name"]] = acc - staff
    account_owner = collections.defaultdict(set)
    for n, acc in accounts.items():
        for u in acc:
            account_owner[u].add(n)
    idx = {p["name"]: i for i, p in enumerate(listed)}

    offices = json.load(open(os.path.join(ROOT, "data", "offices.json"), encoding="utf-8"))["offices"]
    workplaces = json.load(open(os.path.join(ROOT, "data", "workplaces.json"), encoding="utf-8"))["places"]
    indicators = json.load(open(os.path.join(ROOT, "data", "indicators.json"), encoding="utf-8"))["indicators"]
    partners, cross = [], collections.Counter()
    for i, p in enumerate(listed):
        r = reg["partners"].get(p["name"]) or {}
        ths = sorted(by_partner.get(p["name"], []), key=lambda t: t["created_at"])
        acc = accounts[p["name"]]
        st_rf = sorted(states_in(p["name"] + ". " + p["desc"]))
        st_decl = sorted(s for s in r.get("declared_states", []) if s in STATES and s not in st_rf)
        web = {w["state"]: w for w in workplaces.get(p["name"], []) if w["state"] in STATES}
        st_web = sorted(s for s in web if s not in st_rf and s not in st_decl)
        own = replies = views = 0
        grove_states, newest, mine = collections.Counter(), None, []
        for th in ths:
            views += th["views"]
            for s, n in states_in(th["title"]).items():
                grove_states[s] += n
            for post in th["posts"]:
                if post["u"] in acc:
                    own += 1
                    for s, n in states_in(text_of(post["cooked"])).items():
                        grove_states[s] += n
                    mine.append((th, post))
                    if not newest or post["at"] > newest[1]["at"]:
                        newest = (th, post)
                else:
                    replies += 1
                    for other in account_owner.get(post["u"], ()):  # another listed partner replied here
                        if other != p["name"]:
                            cross[tuple(sorted((i, idx[other])))] += 1
        latest = None
        if newest:
            th, post = newest
            age = (now - when(post["at"])).days
            answered = any(x["u"] not in acc and x["at"] > post["at"] for x in th["posts"])
            latest = {"date": post["at"][:10], "days": age, "title": th["title"],
                      "url": f"{GROVE}/t/{th['slug']}/{th['id']}/{post['n']}",
                      "excerpt": text_of(post["cooked"])[:240], "waiting": age <= AWAIT_DAYS and not answered}
        ups = [{"date": post["at"][:10], "title": th["title"], "url": f"{GROVE}/t/{th['slug']}/{th['id']}/{post['n']}",
                "excerpt": text_of(post["cooked"])[:200]}
               for th, post in sorted(mine, key=lambda x: x[1]["at"], reverse=True)[:3]]
        known = st_rf + st_decl + st_web
        pins = []
        terms = place_terms(p["name"] + ". " + p["desc"])
        for stt in known:
            pt = label = None
            cands = terms.get(stt, []) + ([web[stt]["place"]] if stt in web and web[stt]["place"] else [])
            for term in cands:
                pt = geocode(term, stt)
                if pt:
                    label = term
                    break
            if not pt:
                pt, label = geocode(stt, stt), stt
            if pt:
                pins.append({"k": "work", "ll": pt, "label": label, "state": stt, "exact": label != stt,
                             "src": "rf" if stt in st_rf else "decl" if stt in st_decl else "web"})
        off = offices.get(p["name"])
        if off and off["state"] in STATES:
            pt = geocode(off["city"], off["state"])
            if pt:
                pins.append({"k": "office", "ll": pt, "label": off["city"], "state": off["state"]})
        partners.append({
            "id": i, "name": p["name"], "year": p["year"], "url": p["url"], "desc": p["desc"],
            "role": r.get("role"), "group": role_group.get(r.get("role")), "focus": r.get("focus"),
            "assets": r.get("assets", []),
            "scope": "place" if len(known) == 1 else "multi" if len(known) > 1 else r.get("scope", "ns"),
            "sRF": st_rf, "sDecl": st_decl, "declSrc": r.get("declared_source"), "sWeb": st_web,
            "web": {s: {"place": web[s]["place"], "source": web[s]["source"], "quote": web[s]["quote"]} for s in st_web},
            "ups": ups,
            "sGrove": sorted(s for s, n in grove_states.items() if n >= GROVE_MIN_MENTIONS and s not in known),
            "pins": pins, "office": off if off and off["state"] in STATES else None,
            "threads": len(ths), "posts": own, "replies": replies, "views": views, "latest": latest,
        })

    # ---- open now: recent calls, jobs and events from accounts past the forum's new-user level
    open_now = []
    for t in topics:
        kind = OPEN_CATEGORIES.get(cats.get(t["category_id"], ""))
        if not kind or t.get("pinned") or not t.get("visible", True) or (t.get("_op_tl") or 0) < MIN_TRUST:
            continue
        age = (now - when(t["created_at"])).days
        if age <= OPEN_DAYS:
            open_now.append({"kind": kind, "t": t["title"], "u": f"{GROVE}/t/{t['slug']}/{t['id']}",
                             "c": cats[t["category_id"]], "y": t["created_at"][:10], "r": t["posts_count"] - 1,
                             "states": sorted(states_in(t["title"]))})
    open_now.sort(key=lambda x: x["y"], reverse=True)

    other_threads = [{"title": th["title"], "url": f"{GROVE}/t/{th['slug']}/{th['id']}", "created": th["created_at"][:10]}
                     for th in sorted(unmatched, key=lambda t: t["created_at"], reverse=True)]
    st = about.get("stats", {})
    model = {
        "meta": {"fetchedAt": fetched, "publicTopics": len(topics), "openDays": OPEN_DAYS, "awaitDays": AWAIT_DAYS,
                 "unclassified": [p["name"] for p in listed if p["name"] not in reg["partners"]],
                 "about": {k: st.get(k) for k in ("topics_count", "posts_count", "users_count", "active_users_30_days")}},
        "focus": reg["focus"], "assets": reg["assets"], "groups": reg["groups"], "roles": reg["roles"],
        "contributors": reg.get("contributors", []),
        "partners": partners, "cross": [[a, b, n] for (a, b), n in sorted(cross.items())],
        "open": open_now, "otherThreads": other_threads, "indicators": indicators,
        "work": json.load(open(os.path.join(ROOT, "data", "work.json"), encoding="utf-8"))["states"]
        if os.path.exists(os.path.join(ROOT, "data", "work.json")) else {},
    }
    with open(os.path.join(ROOT, "model.json"), "w", encoding="utf-8") as f:
        json.dump(model, f, ensure_ascii=False, separators=(",", ":"))
    w = sum(1 for p in partners if p["latest"] and p["latest"]["waiting"])
    print(f"partners {len(partners)} | with a thread {sum(1 for p in partners if p['threads'])} | waiting for a reply {w} | "
          f"cross-partner pairs {len(cross)} | open now {len(open_now)} | unmatched threads {len(other_threads)} | "
          f"unclassified {len(model['meta']['unclassified'])}")
    return model


if __name__ == "__main__":
    main()
