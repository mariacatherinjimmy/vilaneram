import sqlite3
import os

db_path = "vilaneram2.db"
conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.executescript("""
PRAGMA foreign_keys=off;
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS match_requests_new (
    id INTEGER PRIMARY KEY,
    supply_id INTEGER,
    demand_id INTEGER, -- Removed NOT NULL
    farmer_id INTEGER NOT NULL,
    shopkeeper_id INTEGER NOT NULL,
    message TEXT,
    status VARCHAR(8) DEFAULT 'pending',
    shopkeeper_note TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY(supply_id) REFERENCES supply_listings(id),
    FOREIGN KEY(demand_id) REFERENCES demand_listings(id),
    FOREIGN KEY(farmer_id) REFERENCES users(id),
    FOREIGN KEY(shopkeeper_id) REFERENCES users(id)
);

INSERT INTO match_requests_new (
    id, supply_id, demand_id, farmer_id, shopkeeper_id, message, status, shopkeeper_note, created_at, updated_at
)
SELECT 
    id, supply_id, demand_id, farmer_id, shopkeeper_id, message, status, shopkeeper_note, created_at, updated_at
FROM match_requests;

DROP TABLE match_requests;
ALTER TABLE match_requests_new RENAME TO match_requests;

CREATE INDEX ix_match_requests_id ON match_requests (id);

COMMIT;
PRAGMA foreign_keys=on;
""")

conn.close()
print("DB fixed successfully.")
