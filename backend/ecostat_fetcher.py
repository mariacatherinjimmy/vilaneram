"""
backend/ecostat_fetcher.py
══════════════════════════════════════════════════════════════════════
VilaNeram — Ecostat Kerala Daily Price Fetcher

Real API endpoint (confirmed):
  GET https://www.ecostat.kerala.gov.in/api/data-subset/465

Real response format (confirmed):
  {
    "records": [
      {
        "date":        "2025-03-11",
        "measure_1":   28.5,          ← DailyPrice
        "measure_3":   24.0,          ← PrevMonthPrice
        "dim_2_name":  "Tomato",      ← Commodity name
        "dim_3_name":  "Vegetables"   ← Category
      }, ...
    ]
  }

Run modes:
  1. Auto at 6:30 AM IST daily via APScheduler
  2. Admin panel  POST /api/admin/fetch-data
  3. CLI          python -m backend.ecostat_fetcher
══════════════════════════════════════════════════════════════════════
"""

import requests
import logging
from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session
from .database import SessionLocal, CommodityPrice, FetchLog

logger = logging.getLogger("vilaneram.fetcher")

API_URL = "https://www.ecostat.kerala.gov.in/api/data-subset/465"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":  "application/json, text/plain, */*",
    "Referer": "https://www.ecostat.kerala.gov.in/",
}


def parse_date(raw) -> date:
    if not raw:
        return date.today()
    s = str(raw).split("T")[0].strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return date.today()


def fetch_and_store(db: Session, triggered_by: str = "scheduler") -> dict:
    """
    Fetch from Ecostat API and upsert into commodity_prices.

    Real column mapping:
      dim_2_name  → commodity_name
      dim_3_name  → category
      date        → price_date
      measure_1   → price (daily price)
      measure_3   → prev_month_price
    """
    inserted = 0
    skipped  = 0
    errors   = 0
    status   = "success"

    # ── 1. Call API ───────────────────────────────────────────────
    try:
        logger.info(f"Calling {API_URL}")
        resp = requests.get(API_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
    except Exception as e:
        logger.error(f"API call failed: {e}")
        _log(db, date.today(), 0, 0, 1, "failed", triggered_by)
        return {"inserted":0,"skipped":0,"errors":1,"status":"failed","detail":str(e)}

    records = payload.get("records", [])
    logger.info(f"API returned {len(records)} records")

    if not records:
        _log(db, date.today(), 0, 0, 0, "partial", triggered_by)
        return {"inserted":0,"skipped":0,"errors":0,"status":"partial","detail":"Empty records"}

    # ── 2. Process each record ────────────────────────────────────
    for row in records:
        try:
            commodity = " ".join(str(row.get("dim_2_name") or "").split())  # normalize spaces
            category  = " ".join(str(row.get("dim_3_name") or "").split())
            raw_date  = row.get("date")
            raw_price = row.get("measure_1")
            raw_prev  = row.get("measure_3")

            if not commodity:
                skipped += 1
                continue

            # parse daily price
            try:
                price = float(str(raw_price).replace(",","").strip())
                if price <= 0:
                    skipped += 1
                    continue
            except (ValueError, TypeError):
                skipped += 1
                continue

            # parse prev month price (optional)
            try:
                prev = float(str(raw_prev).replace(",","").strip()) if raw_prev else None
                if prev and prev <= 0:
                    prev = None
            except (ValueError, TypeError):
                prev = None

            price_date = parse_date(raw_date)

            # ── 3. Upsert ─────────────────────────────────────────
            existing = (
                db.query(CommodityPrice)
                .filter(
                    CommodityPrice.commodity_name == commodity,
                    CommodityPrice.price_date     == price_date,
                )
                .first()
            )
            if existing:
                existing.price           = price
                existing.prev_month_price = prev
                existing.category        = category
                existing.source          = "ecostat_api"
            else:
                db.add(CommodityPrice(
                    commodity_name   = commodity,
                    price            = price,
                    prev_month_price = prev,
                    category         = category,
                    price_date       = price_date,
                    source           = "ecostat_api",
                ))
            inserted += 1

        except Exception as e:
            logger.error(f"Row error: {e} | {row}")
            errors += 1

    # ── 4. Commit ─────────────────────────────────────────────────
    try:
        db.commit()
    except Exception as e:
        logger.error(f"Commit failed: {e}")
        db.rollback()
        errors += 1
        status = "partial"

    if errors > 0:
        status = "partial"

    logger.info(f"Done — inserted:{inserted} skipped:{skipped} errors:{errors}")
    _log(db, date.today(), inserted, skipped, errors, status, triggered_by)

    return {
        "inserted": inserted,
        "skipped":  skipped,
        "errors":   errors,
        "status":   status,
        "date":     str(date.today()),
    }


def _log(db, fetch_date, inserted, skipped, errors, status, triggered_by):
    """Write a row to fetch_logs table."""
    try:
        db.add(FetchLog(
            fetch_date   = fetch_date,
            inserted     = inserted,
            skipped      = skipped,
            errors       = errors,
            status       = status,
            triggered_by = triggered_by,
        ))
        db.commit()
    except Exception as e:
        logger.warning(f"Fetch log write failed: {e}")
        db.rollback()


def run_daily_fetch(triggered_by: str = "scheduler") -> dict:
    """Synchronous entry point — called by APScheduler and admin endpoint."""
    db = SessionLocal()
    try:
        return fetch_and_store(db, triggered_by=triggered_by)
    finally:
        db.close()


# ── CLI ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    print(f"\nVilaNeram — Manual Fetch\nAPI: {API_URL}\n" + "-"*50)
    r = run_daily_fetch(triggered_by="manual_cli")
    print(f"\nInserted / Updated : {r['inserted']}")
    print(f"Skipped            : {r['skipped']}")
    print(f"Errors             : {r['errors']}")
    print(f"Status             : {r['status']}")
    print(f"Date               : {r['date']}")