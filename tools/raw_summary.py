#!/usr/bin/env python3
"""Convert a raw platform match summary (numeric ids) into the named JSON that analyze_match.py reads.

Platform downloads (and `cambc matches summary` without --json conversion) use numeric codes:
metric ids, event kind ids, team 0/1, champion_type integers. The schema below is copied from the
schema embedded in the cambc CLI (summary format 1.0).

usage: raw_summary.py RAW.json [-o NAMED.json]      (prints to stdout without -o)
"""
import argparse, json, sys

METRICS = ["earnedGold", "spentGold", "gold", "gems", "collectedGems", "submittedGems", "saleRefunds", "kills", "deaths",
           "assists", "monsterDamageDone", "monsterDamageTaken", "championDamageDone", "championDamageTaken", "healingDone",
           "healingReceived", "shieldingDone"]
EVENT_KINDS = {1: "death", 2: "kill", 3: "assist", 4: "wardPlacement", 5: "buyItem", 6: "buyConsumable", 7: "sellItem",
               8: "campClear", 9: "gemSubmission", 10: "gemCollection", 11: "gemLoss", 12: "itemCombination", 13: "botFault",
               14: "fuelExhausted", 15: "resignation"}
CHAMPION_TYPES = ["Ryth", "Vesper Vale", "Vendetta", "Cassi", "Issac", "Stellar", "Prism", "Marcella", "Willow", "Ren", "Varg", "Tavi"]
DRAFT_CHOICES = ["Ryth", "Vesper Vale", "Vendetta", "Cassi & Issac", "Stellar", "Prism", "Marcella", "Willow", "Ren", "Varg", "Tavi"]
ITEM_FAMILIES = ["Monster", "Power", "Durability", "Treasure", "Jungle", "Home", "Bruiser"]
ITEM_KINDS = ["Shard of Strength", "Emblem of Strength", "Shard of Focus", "Emblem of Focus", "Shard of Health", "Emblem of Health"]
CONSUMABLES = {0: "Teleport Crystal", 1: "Teleport Crystal", 2: "Altar Lock"}
# Team timelines use their own metric table: id 0 is the banked score (its last run equals teams[].submittedGems).
TEAM_METRICS = ["submittedGems"]
TEAM = {0: "teamA", 1: "teamB"}
OUTCOME = {0: "none", 1: "teamA", 2: "teamB"}
ENTITY_KINDS = {"1": "champion", "2": "camp", "6": "altarLock"}


def item_name(i):
    i = int(i)
    if 0 <= i < len(ITEM_FAMILIES) * 6:
        return f"{ITEM_FAMILIES[i // 6]} {ITEM_KINDS[i % 6]}"
    return f"item{i}"


def convert(raw):
    ident = {c["id"]: c for c in raw["roster"]["champions"]}
    def champ_ref(cid):
        c = ident.get(cid)
        if not c:
            return {"id": cid, "kind": "unknown"}
        return {"id": cid, "kind": "champion", "name": CHAMPION_TYPES[c["type"]], "team": TEAM[c["team"]]}

    out = {"formatVersion": raw.get("formatVersion"), "jsonFormatVersion": "raw-converted"}
    m = dict(raw["match"])
    m["outcome"] = OUTCOME.get(m.get("outcome"), m.get("outcome"))
    out["match"] = m
    out["roster"] = {
        "draft": [{"team": TEAM[p["team"]], "champion": DRAFT_CHOICES[p["type"]]} for p in raw["roster"]["draft"]],
        "champions": [{"id": c["id"], "team": TEAM[c["team"]], "name": CHAMPION_TYPES[c["type"]], "draftPick": c["draftPick"]}
                      for c in raw["roster"]["champions"]],
    }
    out["teams"] = [{"team": TEAM[t["id"]], "submittedGems": t["submittedGems"]} for t in raw["teams"]]
    champs = []
    for c in raw["champions"]:
        ref = champ_ref(c["id"])
        metrics = {METRICS[x["id"]]: x["value"] for x in c["metrics"] if x["id"] < len(METRICS)}
        champs.append({
            "id": c["id"], "name": ref.get("name"), "team": ref.get("team"), "metrics": metrics,
            "items": [{"item": item_name(i["id"]), "quantity": i["quantity"]} for i in c.get("items", [])],
            "itemsBought": [{"item": item_name(i["id"]), "quantity": i["quantity"]} for i in c.get("itemsBought", [])],
            "consumables": [{"consumable": CONSUMABLES.get(i["id"], i["id"]), "quantity": i["quantity"]} for i in c.get("consumables", [])],
            "consumablesBought": [{"consumable": CONSUMABLES.get(i["id"], i["id"]), "quantity": i["quantity"]} for i in c.get("consumablesBought", [])],
        })
    out["champions"] = champs
    def timeline(t, team_owner):
        owner = TEAM.get(t["owner"]) if team_owner else champ_ref(t["owner"])
        names = TEAM_METRICS if team_owner else METRICS
        return {"owner": owner, "metric": names[t["metric"]] if t["metric"] < len(names) else t["metric"],
                "sampleCount": t["sampleCount"], "runs": t["runs"]}
    out["teamTimelines"] = [timeline(t, True) for t in raw.get("teamTimelines", [])]
    out["championTimelines"] = [timeline(t, False) for t in raw.get("championTimelines", [])]
    events = []
    for s in raw.get("events", []):
        kind = EVENT_KINDS.get(s["kind"], str(s["kind"]))
        entries = []
        for e in s["entries"]:
            ctx = str(e.get("context", ""))
            target = e.get("target")
            # Champion-targeted events carry the other champion's id; camp/item targets keep the raw id.
            if kind in ("death", "kill", "assist", "gemLoss") and ctx in ("1", "champion"):
                tref = champ_ref(target)
                ctx_name = "champion"
            elif kind in ("death", "gemLoss") and ctx in ("2", "camp"):
                tref = {"id": target, "kind": "camp"}
                ctx_name = "camp"
            elif kind == "gemCollection":
                # gem collections: 1 = camp-group capture, 2 = taken from a killed champion
                ctx_name = {"1": "campGroup", "2": "champion"}.get(ctx, ctx)
                tref = champ_ref(target) if ctx_name == "champion" else {"id": target, "kind": "campGroup"}
            else:
                tref = target
                ctx_name = ENTITY_KINDS.get(ctx, ctx)
            entries.append({**e, "context": ctx_name, "target": tref})
        events.append({"owner": champ_ref(s["owner"]), "kind": kind, "entries": entries})
    out["events"] = events
    d = raw.get("diagnostics", {})
    faults = d.get("botFaults", [0, 0])
    out["diagnostics"] = {"botFaults": {"teamA": faults[0] if faults else 0, "teamB": faults[1] if len(faults) > 1 else 0},
                          "codes": d.get("codes", []), "detailedCaptureComplete": d.get("detailedCaptureComplete")}
    out["heatmaps"] = raw.get("heatmaps", [])
    return out


def is_raw(d):
    return isinstance(d.get("teams", [{}])[0].get("id"), int) and "team" not in d.get("teams", [{}])[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("-o", "--output")
    a = ap.parse_args()
    raw = json.load(open(a.file))
    named = convert(raw) if is_raw(raw) else raw
    text = json.dumps(named, indent=1)
    if a.output:
        open(a.output, "w").write(text)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
