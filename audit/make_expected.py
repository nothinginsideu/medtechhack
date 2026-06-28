"""Convert manifest files into a structured expected-data JSON for the audit."""
import json, glob, os

def parse(path):
    d = {"rows": []}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.startswith("clinic="):
                d["clinic"] = line.split("=", 1)[1]
            elif line.startswith("city="):
                d["city"] = line.split("=", 1)[1]
            elif line.startswith("format="):
                d["format"] = line.split("=", 1)[1]
            else:
                cur, res, nonres, *name_parts = line.split("\t")
                d["rows"].append({
                    "currency": cur,
                    "price_original": float(res) if res else None,
                    "price_nonresident_original": float(nonres) if nonres else None,
                    "service_name_raw": "\t".join(name_parts).strip(),
                })
    return d

expected = {}
for p in sorted(glob.glob("_synth_prices/*.manifest.txt")):
    d = parse(p)
    expected[d["clinic"]] = d

with open("expected_test_data.json", "w", encoding="utf-8") as f:
    json.dump(expected, f, ensure_ascii=False, indent=2)

print(f"Saved expected data for {len(expected)} clinics")
total_rows = sum(len(d["rows"]) for d in expected.values())
usd_rows = sum(1 for d in expected.values() for r in d["rows"] if r["currency"] == "USD")
print(f"Total rows: {total_rows}, USD rows: {usd_rows}")
