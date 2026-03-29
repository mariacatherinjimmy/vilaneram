# backend/database.py
# ============================================================
# VilaNeram 2.0 — Database Models
# ============================================================
# Tables:
#   1. users               — farmer / shopkeeper / admin
#   2. supply_listings     — farmer posts available produce
#   3. demand_listings     — shopkeeper posts requirements
#   4. match_requests      — farmer sends request to shopkeeper
#   5. notifications       — in-app alerts
#   6. commodity_prices    — daily prices from Ecostat API
#   7. fetch_logs          — Ecostat fetch audit trail
#   8. model_evaluations   — XGBoost training metrics
#   9. training_logs       — training run history
# ============================================================

import os
import json
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    Boolean, Date, DateTime, Text, ForeignKey, Enum
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.types import TypeDecorator

# ── JSON column (SQLite-compatible) ──────────────────────────
class JSONColumn(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return json.dumps(value) if value is not None else "[]"

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        try:
            return json.loads(value)
        except Exception:
            return []

# ── Engine setup ─────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./vilaneram2.db")

# SQLite needs check_same_thread=False
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


# ============================================================
# TABLE 1 — USERS
# ============================================================
class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(120), nullable=False)
    mobile        = Column(String(15), unique=True, nullable=False, index=True)
    email         = Column(String(180), unique=True, nullable=True)   # optional
    hashed_pw     = Column(String(255), nullable=False)
    role          = Column(Enum("farmer", "shopkeeper", "admin", name="user_role"),
                           default="farmer", nullable=False)

    # Location — Kerala hierarchy
    district      = Column(String(60), nullable=True)
    local_body_type = Column(
        Enum("grama_panchayat", "municipality", "corporation", name="local_body_type"),
        nullable=True
    )
    local_body    = Column(String(120), nullable=True)   # exact panchayath/municipality/corporation name

    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    last_login    = Column(DateTime, nullable=True)
    commodities   = Column(Text, nullable=True)        # JSON list of commodity names (farmer)
    shop_address  = Column(String(300), nullable=True) # address/landmark (shopkeeper)

    # Relationships
    supply_listings  = relationship("SupplyListing",  back_populates="farmer",      cascade="all, delete-orphan")
    demand_listings  = relationship("DemandListing",  back_populates="shopkeeper",  cascade="all, delete-orphan")
    sent_requests    = relationship("MatchRequest",   foreign_keys="MatchRequest.farmer_id",      back_populates="farmer")
    received_requests= relationship("MatchRequest",   foreign_keys="MatchRequest.shopkeeper_id",  back_populates="shopkeeper")
    notifications    = relationship("Notification",   back_populates="user",        cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.mobile} role={self.role}>"


# ============================================================
# TABLE 2 — SUPPLY LISTINGS (Farmer posts)
# ============================================================
class SupplyListing(Base):
    __tablename__ = "supply_listings"

    id              = Column(Integer, primary_key=True, index=True)
    farmer_id       = Column(Integer, ForeignKey("users.id"), nullable=False)

    commodity_name  = Column(String(180), nullable=False)
    quantity        = Column(Float, nullable=False)
    unit            = Column(String(20), default="kg")       # kg, bunch, nos, litre
    expected_price  = Column(Float, nullable=True)           # optional asking price per unit
    description     = Column(Text, nullable=True)

    # Location (copied from user at time of posting for quick filtering)
    district        = Column(String(60), nullable=True)
    local_body_type = Column(String(30), nullable=True)
    local_body      = Column(String(120), nullable=True)

    status          = Column(
        Enum("active", "sold", "expired", "cancelled", name="supply_status"),
        default="active"
    )
    created_at      = Column(DateTime, default=datetime.utcnow)
    expires_at      = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=3))

    # Relationships
    farmer          = relationship("User", back_populates="supply_listings")
    requests        = relationship("MatchRequest", back_populates="supply", cascade="all, delete-orphan")

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at


# ============================================================
# TABLE 3 — DEMAND LISTINGS (Shopkeeper posts)
# ============================================================
class DemandListing(Base):
    __tablename__ = "demand_listings"

    id              = Column(Integer, primary_key=True, index=True)
    shopkeeper_id   = Column(Integer, ForeignKey("users.id"), nullable=False)

    commodity_name  = Column(String(180), nullable=False)
    quantity_needed = Column(Float, nullable=False)
    unit            = Column(String(20), default="kg")
    max_price       = Column(Float, nullable=True)           # optional max willing to pay
    description     = Column(Text, nullable=True)

    # Location (copied from user)
    district        = Column(String(60), nullable=True)
    local_body_type = Column(String(30), nullable=True)
    local_body      = Column(String(120), nullable=True)

    status          = Column(
        Enum("active", "fulfilled", "expired", "cancelled", name="demand_status"),
        default="active"
    )
    created_at      = Column(DateTime, default=datetime.utcnow)
    expires_at      = Column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=3))

    # Relationships
    shopkeeper      = relationship("User", back_populates="demand_listings")
    requests        = relationship("MatchRequest", back_populates="demand", cascade="all, delete-orphan")

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at


# ============================================================
# TABLE 4 — MATCH REQUESTS
# ============================================================
# Flow:
#   1. Farmer sees nearby shopkeeper demands
#   2. Farmer sends a request linking their supply to shopkeeper's demand
#   3. Shopkeeper accepts or rejects
# ============================================================
class MatchRequest(Base):
    __tablename__ = "match_requests"

    id              = Column(Integer, primary_key=True, index=True)
    supply_id       = Column(Integer, ForeignKey("supply_listings.id"), nullable=True)
    demand_id       = Column(Integer, ForeignKey("demand_listings.id"), nullable=True)
    farmer_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    shopkeeper_id   = Column(Integer, ForeignKey("users.id"), nullable=False)

    message         = Column(Text, nullable=True)            # optional note from farmer
    status          = Column(
        Enum("pending", "accepted", "rejected", name="request_status"),
        default="pending"
    )
    shopkeeper_note = Column(Text, nullable=True)            # optional reply from shopkeeper

    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    supply          = relationship("SupplyListing",  back_populates="requests")
    demand          = relationship("DemandListing",  back_populates="requests")
    farmer          = relationship("User", foreign_keys=[farmer_id],      back_populates="sent_requests")
    shopkeeper      = relationship("User", foreign_keys=[shopkeeper_id],  back_populates="received_requests")


# ============================================================
# TABLE 5 — NOTIFICATIONS
# ============================================================
class Notification(Base):
    __tablename__ = "notifications"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False)
    title       = Column(String(180), nullable=False)
    body        = Column(Text, nullable=False)
    notif_type  = Column(String(40), default="info")   # info, request, accepted, rejected, match
    is_read     = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    user        = relationship("User", back_populates="notifications")


# ============================================================
# TABLE 6 — COMMODITY PRICES (from Ecostat Kerala API)
# ============================================================
class CommodityPrice(Base):
    __tablename__ = "commodity_prices"

    id               = Column(Integer, primary_key=True, index=True)
    commodity_name   = Column(String(180), nullable=False, index=True)
    category         = Column(String(100), nullable=True)
    price            = Column(Float, nullable=False)
    prev_month_price = Column(Float, nullable=True)
    price_date       = Column(Date, nullable=False, index=True)
    source           = Column(String(40), default="ecostat_api")
    created_at       = Column(DateTime, default=datetime.utcnow)


# ============================================================
# TABLE 7 — FETCH LOGS
# ============================================================
class FetchLog(Base):
    __tablename__ = "fetch_logs"

    id           = Column(Integer, primary_key=True, index=True)
    fetch_date   = Column(Date, nullable=False, index=True)
    inserted     = Column(Integer, default=0)
    skipped      = Column(Integer, default=0)
    errors       = Column(Integer, default=0)
    status       = Column(String(20), default="success")
    triggered_by = Column(String(40), default="auto")
    created_at   = Column(DateTime, default=datetime.utcnow)


# ============================================================
# TABLE 8 — MODEL EVALUATIONS
# ============================================================
class ModelEvaluation(Base):
    __tablename__ = "model_evaluations"

    id            = Column(Integer, primary_key=True, index=True)
    commodity_name= Column(String(180), nullable=True)
    rmse          = Column(Float, nullable=True)
    mae           = Column(Float, nullable=True)
    mape          = Column(Float, nullable=True)
    r2_score      = Column(Float, nullable=True)
    test_samples  = Column(Integer, nullable=True)
    data_samples  = Column(Integer, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)


# ============================================================
# TABLE 9 — TRAINING LOGS
# ============================================================
class TrainingLog(Base):
    __tablename__ = "training_logs"

    id             = Column(Integer, primary_key=True, index=True)
    data_samples   = Column(Integer, nullable=True)
    data_features  = Column(Integer, nullable=True)
    price_rmse     = Column(Float, nullable=True)
    status         = Column(String(20), default="success")
    created_at     = Column(DateTime, default=datetime.utcnow)


# ============================================================
# DB INIT
# ============================================================
def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()