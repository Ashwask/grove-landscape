#!/usr/bin/env python3
"""Build index.html: model.json + India state shapes inlined into template.html.

  python3 scripts/fetch.py        # refresh data/raw from the public pages
  python3 build.py                # rebuild model.json and index.html
"""
import csv, json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import build_model  # noqa: E402


# Where corrections are filed. Leave empty until the repository exists; the page then hides the links.
REPO = "https://github.com/Ashwask/grove-landscape"


def open_data(model):
    """The partner table as plain files, so others can reuse it without this page."""
    lab = lambda key: {x["id"]: x["label"] for x in model[key]}
    focus, assets, roles = lab("focus"), lab("assets"), lab("roles")
    rows = [{"name": p["name"], "website": p["url"], "partner_since": p["year"], "focus_area": focus.get(p["focus"], ""),
             "role": roles.get(p["role"], ""), "natural_assets": [assets[a] for a in p["assets"]],
             "states_stated": p["sRF"], "states_declared": p["sDecl"], "states_named_in_grove_updates": p["sGrove"],
             "office_city": (p["office"] or {}).get("city", ""), "office_state": (p["office"] or {}).get("state", ""),
             "office_source": (p["office"] or {}).get("source", ""), "latest_grove_update": (p["latest"] or {}).get("date", ""), "latest_grove_url": (p["latest"] or {}).get("url", "")}
            for p in model["partners"]]
    json.dump({"refreshed": model["meta"]["fetchedAt"], "partners": rows},
              open(os.path.join(ROOT, "partners.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, "partners.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(rows[0].keys())
        for r in rows:
            w.writerow(["; ".join(v) if isinstance(v, list) else v for v in r.values()])


def main():
    model = build_model.main()
    open_data(model)
    geo = json.load(open(os.path.join(ROOT, "data", "india_states.geojson"), encoding="utf-8"))
    html = open(os.path.join(ROOT, "template.html"), encoding="utf-8").read()
    dump = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    for mark, value in (("/*MODEL*/null", dump(model)), ("/*GEO*/null", dump(geo)),
                        ("/*MINM*/3", str(build_model.GROVE_MIN_MENTIONS)), ('/*REPO*/""', json.dumps(REPO))):
        assert mark in html, mark
        html = html.replace(mark, value)
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html", len(html), "bytes")


if __name__ == "__main__":
    main()
