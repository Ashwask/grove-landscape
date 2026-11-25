# The Grove Landscape

What the Rainmatter Foundation's listed partners are doing, state by state, read from their own posts on [The Grove](https://grove.rainmatter.org/): the work, who it is with, what it means for the place, and who could work together on what.

This is an independent reading of public pages. It is not a Rainmatter Foundation publication.

## What it is for

It sits between partners who work in the same place or on the same natural asset, and between them and people who can help (funders, researchers, practitioners, job seekers), so that they can find each other without waiting for an introduction. It is a diagnostic and is meant to be temporary: if it proves useful its natural home is The Grove or rainmatter.org; if not, it should be retired.

## What the page shows

- **Map (OpenStreetMap data, India only).** A filled pin is a place a partner works, from the Foundation's page or the partner's own website. A hollow pin is an office. Partners with neither are listed, never guessed.
- **Place brief.** Click a state: what it means for the place, next actions, who works on which natural asset, and public indicators for that asset.
- **What is happening.** For 32 states, the pieces of work partners describe in their own posts on The Grove since 2024: what is done, the numbers, who it is with, what is asked for, each linked to its source post (`data/work.json`).
- **Who could work together.** Proposed collaborations, each naming who brings what, whether the partners complement or intersect, and the artefact they would make.
- **Open now.** What partners are asking for, and recent calls and events from the forum.
- **Partners.** The full directory.
- **About and contribute.** Method, limits, and how to correct an entry.

Replies and reply counts on the forum are not used anywhere. The readings and collaborations are interpretation written from the posts; a collaboration is a proposal, not something partners have agreed.

## How partners are grouped

The Foundation's own vocabulary is used wherever it publishes one: its four focus areas (Urban, Rural, Conservation and Restoration, Messaging) plus a cross-cutting bucket, and its six natural assets (air, water, soil, biodiversity, energy, materials). Role is one of eight kinds of organisation. All three are an editorial reading of the Foundation's description of each partner, kept in `data/registry.json`.

## Sources

| Source | What is read |
|---|---|
| [rainmatter.org/partners](https://rainmatter.org/partners) | Partner name, year, description, website, places named |
| [grove.rainmatter.org](https://grove.rainmatter.org/) | Public topic lists, the Partner Updates category and its threads |
| Each partner's own website | Where it says it works (`data/workplaces.json`) and its main office (`data/offices.json`), each with source page and quote |
| OpenStreetMap | Base map data (vector tiles served by OpenFreeMap), and Nominatim for locating named places (`data/geocode.json`) |

## How it stays current

`.github/workflows/refresh.yml` runs every day at 06:00 IST: it fetches the sources, rebuilds `index.html`, `partners.json` and `partners.csv`, and commits only if something changed. A partner added to the Foundation's list appears automatically as unclassified until it is added to `data/registry.json`. Office locations, places of work from partner websites, state indicators and the reading of posts in `data/work.json` are one-time reads and are not refreshed by the daily job.

```
python3 scripts/fetch.py   # writes data/raw (not committed)
python3 build.py           # writes model.json, index.html, partners.json, partners.csv
```

No dependencies beyond Python 3. The page loads MapLibre GL from cdnjs and OpenStreetMap vector tiles from OpenFreeMap; no key is needed.

## Correcting an entry

If you work at a listed partner and your place, natural assets or role are wrong or missing, open an issue with a public link that supports the change. A partner's own correction is stored as `declared_states` and `declared_source` in `data/registry.json` and shown as declared.

## Honesty rules

- A state counts as a place of work only when the Foundation's page names it or a place inside it, or the partner has declared it. Offices are never counted as places of work.
- The indicative view (off by default) adds states named three or more times in a partner's own Grove posts.
- An empty state or cell means "not in these public sources", not "no work happens here".
- No funding amounts appear because none are published on the pages read.

## Licence

Code under the licence in `LICENSE`. Partner descriptions and forum content belong to their authors and are linked to their source. Map data © OpenStreetMap contributors, tiles by OpenFreeMap.
