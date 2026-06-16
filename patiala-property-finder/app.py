import os
import re
import sqlite3
import hashlib
from flask import Flask, jsonify, request, render_template, g
from flask_cors import CORS
from scrapers import run_all_scrapers, scrape_status

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), "properties.db")


# ── DB helpers ─────────────────────────────────────────────────────────────

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.execute("""
        CREATE TABLE IF NOT EXISTS properties (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            url_hash      TEXT UNIQUE NOT NULL,
            tlp_hash      TEXT,
            title         TEXT NOT NULL,
            price         TEXT,
            price_numeric REAL,
            location      TEXT,
            area          TEXT,
            area_sqft     REAL,
            property_type TEXT,
            listing_type  TEXT,
            summary       TEXT,
            source_url    TEXT NOT NULL,
            source_name   TEXT,
            added_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_url_hash ON properties(url_hash)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_tlp_hash ON properties(tlp_hash)")
    db.commit()
    db.close()


# ── Hash helpers ────────────────────────────────────────────────────────────

def url_hash(url: str) -> str:
    return hashlib.md5(url.strip().lower().encode()).hexdigest()


def tlp_hash(title: str, location: str, price: str) -> str:
    t = re.sub(r"\s+", " ", title.lower().strip())
    l = location.lower().strip()
    p = re.sub(r"[₹,\s]", "", price.lower().strip())
    return hashlib.md5(f"{t}|{l}|{p}".encode()).hexdigest()


# ── Price / area parsers ────────────────────────────────────────────────────

def parse_price_lakh(price_str: str) -> float | None:
    if not price_str:
        return None
    s = price_str.replace(",", "").replace("₹", "").strip()
    m = re.match(r"([\d.]+)", s)
    if not m:
        return None
    num = float(m.group(1))
    sl = s.lower()
    if "cr" in sl:
        return round(num * 100, 2)
    if "lac" in sl or "lakh" in sl:
        return round(num, 2)
    if "/month" in sl or "/mo" in sl or "per month" in sl:
        return round(num / 100_000, 4)
    # bare rupees
    if num > 100_000:
        return round(num / 100_000, 4)
    return round(num, 2)


def parse_area_sqft(area_str: str) -> float | None:
    if not area_str:
        return None
    s = area_str.replace(",", "").strip()
    m = re.match(r"([\d.]+)", s)
    if not m:
        return None
    num = float(m.group(1))
    sl = s.lower()
    if "kanal" in sl:
        return round(num * 5445, 1)
    if "marla" in sl:
        return round(num * 272.25, 1)
    if "acre" in sl:
        return round(num * 43_560, 1)
    if "sq yrd" in sl or "sqyrd" in sl or "sq yd" in sl:
        return round(num * 9, 1)
    if "sq m" in sl or "sqm" in sl:
        return round(num * 10.764, 1)
    return round(num, 1)  # sqft / default


# ── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/properties")
def get_properties():
    db = get_db()

    search        = request.args.get("search", "").strip()
    listing_type  = request.args.get("listing_type", "").strip()
    property_type = request.args.get("property_type", "").strip()
    location_f    = request.args.get("location", "").strip()
    source_f      = request.args.get("source", "").strip()
    min_price     = request.args.get("min_price", "").strip()
    max_price     = request.args.get("max_price", "").strip()
    min_area      = request.args.get("min_area", "").strip()
    max_area      = request.args.get("max_area", "").strip()
    page          = max(1, int(request.args.get("page", 1)))
    per_page      = min(50, max(1, int(request.args.get("per_page", 24))))

    where, params = ["1=1"], []

    if search:
        where.append("(title LIKE ? OR location LIKE ? OR summary LIKE ? OR property_type LIKE ?)")
        like = f"%{search}%"
        params += [like, like, like, like]
    if listing_type:
        where.append("listing_type = ?"); params.append(listing_type)
    if property_type:
        where.append("property_type = ?"); params.append(property_type)
    if location_f:
        where.append("location LIKE ?"); params.append(f"%{location_f}%")
    if source_f:
        where.append("source_name = ?"); params.append(source_f)
    if min_price:
        where.append("price_numeric >= ?"); params.append(float(min_price))
    if max_price:
        where.append("price_numeric <= ?"); params.append(float(max_price))
    if min_area:
        where.append("area_sqft >= ?"); params.append(float(min_area))
    if max_area:
        where.append("area_sqft <= ?"); params.append(float(max_area))

    base_q = "FROM properties WHERE " + " AND ".join(where)
    total  = db.execute("SELECT COUNT(*) " + base_q, params).fetchone()[0]
    rows   = db.execute(
        "SELECT * " + base_q + " ORDER BY added_at DESC LIMIT ? OFFSET ?",
        params + [per_page, (page - 1) * per_page]
    ).fetchall()

    return jsonify({
        "properties": [dict(r) for r in rows],
        "total":  total,
        "page":   page,
        "per_page": per_page,
        "pages":  (total + per_page - 1) // per_page if total else 0,
    })


@app.route("/api/filters")
def get_filters():
    db = get_db()
    locations = [r[0] for r in db.execute(
        "SELECT DISTINCT location FROM properties WHERE location IS NOT NULL AND location != '' ORDER BY location"
    ).fetchall()]
    prop_types = [r[0] for r in db.execute(
        "SELECT DISTINCT property_type FROM properties WHERE property_type IS NOT NULL AND property_type != '' ORDER BY property_type"
    ).fetchall()]
    sources = [r[0] for r in db.execute(
        "SELECT DISTINCT source_name FROM properties WHERE source_name IS NOT NULL ORDER BY source_name"
    ).fetchall()]
    price_range = db.execute(
        "SELECT MIN(price_numeric), MAX(price_numeric) FROM properties WHERE price_numeric IS NOT NULL AND price_numeric > 0"
    ).fetchone()
    area_range = db.execute(
        "SELECT MIN(area_sqft), MAX(area_sqft) FROM properties WHERE area_sqft IS NOT NULL AND area_sqft > 0"
    ).fetchone()
    return jsonify({
        "locations":   locations,
        "property_types": prop_types,
        "sources":     sources,
        "price_min":   price_range[0] if price_range else None,
        "price_max":   price_range[1] if price_range else None,
        "area_min":    area_range[0] if area_range else None,
        "area_max":    area_range[1] if area_range else None,
    })


@app.route("/api/stats")
def get_stats():
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM properties").fetchone()[0]
    by_type = dict(db.execute(
        "SELECT listing_type, COUNT(*) FROM properties GROUP BY listing_type"
    ).fetchall())
    by_source = dict(db.execute(
        "SELECT source_name, COUNT(*) FROM properties GROUP BY source_name"
    ).fetchall())
    by_prop = dict(db.execute(
        "SELECT property_type, COUNT(*) FROM properties GROUP BY property_type ORDER BY COUNT(*) DESC"
    ).fetchall())
    last_updated = db.execute("SELECT MAX(added_at) FROM properties").fetchone()[0]
    return jsonify({
        "total":        total,
        "by_type":      by_type,
        "by_source":    by_source,
        "by_prop_type": by_prop,
        "last_updated": last_updated,
    })


@app.route("/api/scrape-status")
def get_scrape_status():
    return jsonify(scrape_status)


@app.route("/api/refresh", methods=["POST"])
def refresh_listings():
    db = get_db()
    listings, status = run_all_scrapers()

    added = skipped = dupes = 0
    seen_tlp: set[str] = set(
        r[0] for r in db.execute("SELECT tlp_hash FROM properties WHERE tlp_hash IS NOT NULL").fetchall()
    )

    for item in listings:
        url_h = url_hash(item.get("source_url", ""))
        tlp_h = tlp_hash(
            item.get("title", ""),
            item.get("location", ""),
            item.get("price", ""),
        )

        # Skip if same URL already exists
        if db.execute("SELECT id FROM properties WHERE url_hash = ?", (url_h,)).fetchone():
            skipped += 1
            continue

        # Skip if same title+location+price already exists (different URL)
        if tlp_h in seen_tlp:
            dupes += 1
            continue
        seen_tlp.add(tlp_h)

        price_n = parse_price_lakh(item.get("price", ""))
        area_n  = parse_area_sqft(item.get("area", ""))

        db.execute("""
            INSERT OR IGNORE INTO properties
              (url_hash, tlp_hash, title, price, price_numeric,
               location, area, area_sqft, property_type, listing_type,
               summary, source_url, source_name)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            url_h, tlp_h,
            item.get("title", ""),
            item.get("price", ""),
            price_n,
            item.get("location", ""),
            item.get("area", ""),
            area_n,
            item.get("property_type", ""),
            item.get("listing_type", ""),
            item.get("summary", ""),
            item.get("source_url", ""),
            item.get("source_name", ""),
        ))
        added += 1

    db.commit()

    status["total_added"]   = added
    status["total_skipped"] = skipped + dupes
    total = db.execute("SELECT COUNT(*) FROM properties").fetchone()[0]

    return jsonify({
        "added":   added,
        "skipped": skipped,
        "dupes":   dupes,
        "total":   total,
        "sources": status.get("sources", {}),
    })


@app.route("/api/property/<int:prop_id>", methods=["DELETE"])
def delete_property(prop_id):
    db = get_db()
    db.execute("DELETE FROM properties WHERE id = ?", (prop_id,))
    db.commit()
    return jsonify({"success": True})


@app.route("/api/clear-demo", methods=["POST"])
def clear_demo():
    """Remove any demo/placeholder listings (source_name = 'Demo Data')."""
    db = get_db()
    n = db.execute("DELETE FROM properties WHERE source_name = 'Demo Data'").rowcount
    db.commit()
    return jsonify({"removed": n})


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    print("\n" + "=" * 54)
    print("  Patiala Property Finder")
    print("=" * 54)
    print(f"  Laptop : http://127.0.0.1:{port}")
    print(f"  Network: http://0.0.0.0:{port}  (share your IP)")
    print("=" * 54 + "\n")
    app.run(host="0.0.0.0", port=port, debug=False)
