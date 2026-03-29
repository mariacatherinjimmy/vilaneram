# backend/main.py
# ============================================================
# VilaNeram 2.0 — Complete FastAPI Backend
# ============================================================

import os, logging, threading
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, date, timedelta
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from .database import (
    get_db, init_db, SessionLocal,
    User, CommodityPrice, FetchLog,
    SupplyListing, DemandListing, MatchRequest,
    Notification, ModelEvaluation, TrainingLog
)
from .auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_farmer, require_shopkeeper, require_admin
)
from .ml.forecast import AgriculturalForecastSystem
from .ecostat_fetcher import fetch_and_store
from .kerala_local_bodies import get_districts, get_local_bodies

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Global model cache ───────────────────────────────────────
_global_model        = None
_model_trained_date  = None
_last_auto_fetch_date = None


# ============================================================
# STARTUP
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _create_default_admin()
    logger.info("VilaNeram 2.0 started.")
    yield


def _create_default_admin():
    db = SessionLocal()
    try:
        mobile = os.getenv("ADMIN_MOBILE", "9999999999")
        if not db.query(User).filter(User.mobile == mobile).first():
            db.add(User(
                name="Admin",
                mobile=mobile,
                email=os.getenv("ADMIN_EMAIL", "admin@vilaneram.com"),
                hashed_pw=hash_password(os.getenv("ADMIN_PASSWORD", "Admin@123456")),
                role="admin", is_active=True
            ))
            db.commit()
            logger.info(f"Default admin created: {mobile}")
    finally:
        db.close()


# ============================================================
# APP SETUP
# ============================================================
app = FastAPI(title="VilaNeram 2.0", version="2.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

_here = os.path.dirname(os.path.abspath(__file__))
frontend_path = os.path.normpath(os.path.join(_here, "..", "frontend"))
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")


def _html(f):
    p = os.path.join(frontend_path, f)
    return FileResponse(p) if os.path.exists(p) else {"error": f"{f} not found"}


# ============================================================
# SCHEMAS
# ============================================================
class RegisterRequest(BaseModel):
    name: str
    mobile: str
    password: str
    role: str = "farmer"
    district: Optional[str] = None
    local_body_type: Optional[str] = None
    local_body: Optional[str] = None
    email: Optional[str] = None
    commodities: Optional[list] = []       # farmer's tracked commodities
    shop_address: Optional[str] = None    # shopkeeper's address/landmark

class LoginRequest(BaseModel):
    mobile: str
    password: str

class SupplyCreate(BaseModel):
    commodity_name: str
    quantity: float
    unit: str = "kg"
    expected_price: Optional[float] = None
    description: Optional[str] = None

class DemandCreate(BaseModel):
    commodity_name: str
    quantity_needed: float
    unit: str = "kg"
    max_price: Optional[float] = None
    description: Optional[str] = None

class RequestCreate(BaseModel):
    demand_id: int
    supply_id: Optional[int] = None
    message: Optional[str] = None

class RequestRespond(BaseModel):
    status: str                        # accepted | rejected
    shopkeeper_note: Optional[str] = None

class PredictRequest(BaseModel):
    commodity: str
    days: int = 7
    category: Optional[str] = None

class ProfitCalcRequest(BaseModel):
    commodity: str
    quantity: float
    unit: str = "kg"

class UserStatusUpdate(BaseModel):
    is_active: bool

class OfferCreate(BaseModel):
    supply_id: int
    message: Optional[str] = None
    offer_price: Optional[float] = None   # shopkeeper's offered price per unit

class OfferRespond(BaseModel):
    status: str                            # accepted | rejected
    farmer_note: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    history: Optional[list] = []


# ============================================================
# PAGE ROUTES
# ============================================================
@app.get("/")
async def home(): return _html("index.html")

@app.get("/index.html")
async def index_html(): return _html("index.html")

@app.get("/farmer")
async def farmer_page(): return _html("farmer.html")

@app.get("/farmer.html")
async def farmer_html(): return _html("farmer.html")

@app.get("/shopkeeper")
async def shopkeeper_page(): return _html("shopkeeper.html")

@app.get("/shopkeeper.html")
async def shopkeeper_html(): return _html("shopkeeper.html")

@app.get("/admin")
async def admin_page(): return _html("admin.html")

@app.get("/admin.html")
async def admin_html_route(): return _html("admin.html")


# ============================================================
# AUTH
# ============================================================
@app.post("/api/auth/register")
async def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.mobile == req.mobile).first():
        raise HTTPException(400, "Mobile number already registered.")
    if req.role not in ("farmer", "shopkeeper"):
        raise HTTPException(400, "Role must be farmer or shopkeeper.")

    import json as _json
    user = User(
        name=req.name, mobile=req.mobile, email=req.email,
        hashed_pw=hash_password(req.password),
        role=req.role, district=req.district,
        local_body_type=req.local_body_type,
        local_body=req.local_body, is_active=True,
        commodities=_json.dumps(req.commodities or []),
        shop_address=req.shop_address
    )
    db.add(user); db.commit(); db.refresh(user)
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer",
            "role": user.role, "name": user.name, "id": user.id}


@app.post("/api/auth/login")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.mobile == req.mobile).first()
    if not user or not verify_password(req.password, user.hashed_pw):
        raise HTTPException(401, "Invalid mobile or password.")
    if not user.is_active:
        raise HTTPException(403, "Account deactivated. Contact admin.")
    user.last_login = datetime.utcnow(); db.commit()
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer",
            "role": user.role, "name": user.name, "id": user.id}


@app.get("/api/auth/me")
async def get_me(u: User = Depends(get_current_user)):
    import json as _json
    comms = []
    try: comms = _json.loads(u.commodities) if u.commodities else []
    except: pass
    return {
        "id": u.id, "name": u.name, "mobile": u.mobile,
        "role": u.role, "district": u.district,
        "local_body_type": u.local_body_type,
        "local_body": u.local_body,
        "commodities": comms,
        "shop_address": u.shop_address,
        "created_at": str(u.created_at)
    }


# ============================================================
# LOCATION — Kerala hierarchy
# ============================================================
@app.get("/api/location/districts")
async def list_districts():
    return {"districts": get_districts()}


@app.get("/api/location/local-bodies")
async def list_local_bodies(district: str, local_body_type: str):
    bodies = get_local_bodies(district, local_body_type)
    if bodies is None:
        raise HTTPException(404, f"No {local_body_type} found for {district}")
    return {"local_bodies": bodies}


# ============================================================
# COMMUNITY — Who is in my panchayath?
# Farmers see shopkeepers. Shopkeepers see farmers.
# Both see name + mobile (phone number).
# ============================================================
@app.get("/api/community/shopkeepers")
async def shopkeepers_in_my_area(db: Session = Depends(get_db),
                                  u: User = Depends(require_farmer)):
    """Farmer sees all shopkeepers in his local body with phone numbers."""
    users = db.query(User).filter(
        User.role == "shopkeeper",
        User.local_body == u.local_body,
        User.is_active == True
    ).all()
    return [{"id": s.id, "name": s.name, "mobile": s.mobile,
             "local_body": s.local_body, "district": s.district} for s in users]


@app.get("/api/community/farmers")
async def farmers_in_my_area(db: Session = Depends(get_db),
                              u: User = Depends(require_shopkeeper)):
    """Shopkeeper sees all farmers in his local body with phone numbers."""
    users = db.query(User).filter(
        User.role == "farmer",
        User.local_body == u.local_body,
        User.is_active == True
    ).all()
    return [{"id": f.id, "name": f.name, "mobile": f.mobile,
             "local_body": f.local_body, "district": f.district} for f in users]


# ============================================================
# COMMODITIES & AUTO-FETCH
# ============================================================
def _already_fetched_today(db):
    global _last_auto_fetch_date
    today = date.today()
    if _last_auto_fetch_date == today: return True
    if db.query(FetchLog).filter(FetchLog.fetch_date == today).first():
        _last_auto_fetch_date = today; return True
    return False


def _trigger_fetch_if_needed(db):
    global _last_auto_fetch_date
    if _already_fetched_today(db): return
    _last_auto_fetch_date = date.today()
    logger.info("First user of day — auto-fetching Ecostat prices...")
    def _do():
        fdb = SessionLocal()
        try: fetch_and_store(fdb, triggered_by="auto_daily")
        except Exception as e: logger.error(f"Auto-fetch failed: {e}")
        finally: fdb.close()
    threading.Thread(target=_do, daemon=True).start()


@app.get("/api/commodities/list")
async def commodities_public(db: Session = Depends(get_db)):
    """No auth — used by registration page."""
    names = db.query(CommodityPrice.commodity_name).distinct().order_by(
        CommodityPrice.commodity_name).all()
    return {"commodities": [n[0] for n in names]}


@app.get("/api/commodities")
async def commodities_auth(db: Session = Depends(get_db),
                            u: User = Depends(get_current_user)):
    _trigger_fetch_if_needed(db)
    names = db.query(CommodityPrice.commodity_name).distinct().order_by(
        CommodityPrice.commodity_name).all()
    return {"commodities": [n[0] for n in names]}


@app.get("/api/commodities/{name}/price")
async def commodity_price(name: str, db: Session = Depends(get_db),
                           u: User = Depends(get_current_user)):
    row = db.query(CommodityPrice).filter(
        CommodityPrice.commodity_name == name
    ).order_by(CommodityPrice.price_date.desc()).first()
    if not row: raise HTTPException(404, f"No price data for '{name}'.")
    prev = db.query(CommodityPrice).filter(
        CommodityPrice.commodity_name == name,
        CommodityPrice.price_date < row.price_date
    ).order_by(CommodityPrice.price_date.desc()).first()
    chg = round((row.price - prev.price) / prev.price * 100, 2) if prev and prev.price else 0.0
    return {"commodity": name, "today": row.price,
            "price_date": str(row.price_date), "change_pct": chg}


# ============================================================
# PREDICT (Farmer only)
# ============================================================
@app.post("/api/predict")
async def predict(req: PredictRequest, db: Session = Depends(get_db),
                  u: User = Depends(require_farmer)):
    global _global_model, _model_trained_date
    today = date.today()
    system = AgriculturalForecastSystem(db=db)

    if db.query(CommodityPrice).count() == 0:
        try: fetch_and_store(db, triggered_by="predict_safety")
        except: raise HTTPException(503, "No price data available. Try again.")

    if not db.query(CommodityPrice).filter(
            CommodityPrice.commodity_name == req.commodity).first():
        raise HTTPException(404, f"'{req.commodity}' not in data.")

    if _global_model and _model_trained_date == today:
        system.reg_model = _global_model["reg_model"]
        system.feature_columns = _global_model["feature_columns"]
    elif system.load_model():
        import joblib as _jl
        _global_model = _jl.load(system.model_file)
        _model_trained_date = today
    else:
        result = system.train_model()
        if not result: raise HTTPException(500, "Model training failed.")
        import joblib as _jl
        _global_model = _jl.load(system.model_file)
        _model_trained_date = today

    predictions = system.predict_future(req.commodity, req.category or "", req.days)
    if not predictions: raise HTTPException(500, f"Prediction failed for '{req.commodity}'.")
    trend = system.analyze_trend(predictions)

    real_row = db.query(CommodityPrice).filter(
        CommodityPrice.commodity_name == req.commodity
    ).order_by(CommodityPrice.price_date.desc()).first()
    today_price = real_row.price if real_row else predictions[0]["price"]

    return {"predictions": predictions, "trend": trend, "today_price": today_price}


# ============================================================
# PROFIT CALCULATOR (Farmer only)
# ============================================================
@app.post("/api/profit-calculator")
async def profit_calculator(req: ProfitCalcRequest, db: Session = Depends(get_db),
                             u: User = Depends(require_farmer)):
    global _global_model, _model_trained_date
    today = date.today()

    real_row = db.query(CommodityPrice).filter(
        CommodityPrice.commodity_name == req.commodity
    ).order_by(CommodityPrice.price_date.desc()).first()
    if not real_row: raise HTTPException(404, f"No price data for '{req.commodity}'.")

    today_price = real_row.price
    system = AgriculturalForecastSystem(db=db)

    if _global_model and _model_trained_date == today:
        system.reg_model = _global_model["reg_model"]
        system.feature_columns = _global_model["feature_columns"]
    elif not system.load_model():
        result = system.train_model()
        if not result: raise HTTPException(500, "Model not ready.")

    predictions = system.predict_future(req.commodity, "", 7)
    if not predictions: raise HTTPException(500, "Prediction failed.")

    prices = [p["price"] for p in predictions]
    peak_price = max(prices)
    peak_day   = prices.index(peak_price) + 1
    low_price  = min(prices)

    earn_today = round(today_price * req.quantity, 2)
    earn_peak  = round(peak_price  * req.quantity, 2)
    extra      = round(earn_peak - earn_today, 2)
    trend_dir  = "rising" if peak_price > today_price * 1.01 else \
                 "falling" if low_price < today_price * 0.99 else "stable"

    # Smart recommendation
    # Also check if there is nearby demand
    nearby_demand = db.query(DemandListing).filter(
        DemandListing.commodity_name == req.commodity,
        DemandListing.local_body == u.local_body,
        DemandListing.status == "active",
        DemandListing.expires_at > datetime.utcnow()
    ).count()

    if trend_dir == "rising" and nearby_demand == 0:
        recommendation = f"Prices rising. If you wait {peak_day} days, you could earn ₹{extra:.2f} more on {req.quantity} {req.unit}. Hold your produce."
        action = "HOLD"
    elif trend_dir == "rising" and nearby_demand > 0:
        recommendation = f"Prices rising but {nearby_demand} shopkeeper(s) nearby need this commodity. You could sell now at ₹{today_price:.2f}/kg or wait {peak_day} days for ₹{extra:.2f} more."
        action = "HOLD_OR_SELL"
    elif trend_dir == "falling" and nearby_demand > 0:
        recommendation = f"Prices are falling. Sell immediately to the {nearby_demand} nearby shopkeeper(s) to get today's price of ₹{today_price:.2f}/kg."
        action = "SELL_NOW"
    elif trend_dir == "falling":
        recommendation = f"Prices are falling. Best to sell as soon as possible. Waiting may reduce earnings by ₹{abs(extra):.2f}."
        action = "SELL_NOW"
    else:
        recommendation = f"Prices are stable. Sell at your convenience. {nearby_demand} nearby shopkeeper(s) available."
        action = "STABLE"

    return {
        "commodity":      req.commodity,
        "quantity":       req.quantity,
        "unit":           req.unit,
        "today_price":    round(today_price, 2),
        "predicted_peak": round(peak_price, 2),
        "peak_day":       peak_day,
        "earn_today":     earn_today,
        "earn_at_peak":   earn_peak,
        "extra_earning":  extra,
        "trend":          trend_dir,
        "nearby_demand":  nearby_demand,
        "action":         action,
        "recommendation": recommendation,
        "predictions":    predictions
    }


# ============================================================
# SUPPLY LISTINGS — Farmer
# ============================================================
@app.post("/api/supply")
async def create_supply(req: SupplyCreate, db: Session = Depends(get_db),
                        u: User = Depends(require_farmer)):
    listing = SupplyListing(
        farmer_id=u.id,
        commodity_name=req.commodity_name,
        quantity=req.quantity, unit=req.unit,
        expected_price=req.expected_price,
        description=req.description,
        district=u.district,
        local_body_type=u.local_body_type,
        local_body=u.local_body
    )
    db.add(listing); db.commit(); db.refresh(listing)

    # Notify matching shopkeepers in same local body
    matches = db.query(DemandListing).filter(
        DemandListing.commodity_name == req.commodity_name,
        DemandListing.local_body == u.local_body,
        DemandListing.status == "active"
    ).all()
    for d in matches:
        db.add(Notification(
            user_id=d.shopkeeper_id, title="New Supply Available",
            body=f"{u.name} listed {req.quantity} {req.unit} of {req.commodity_name} in {u.local_body}. Contact: {u.mobile}",
            notif_type="match"
        ))
    db.commit()
    return {"id": listing.id, "message": "Supply listing created."}


@app.get("/api/supply/mine")
async def my_supply(db: Session = Depends(get_db), u: User = Depends(require_farmer)):
    rows = db.query(SupplyListing).filter(
        SupplyListing.farmer_id == u.id
    ).order_by(SupplyListing.created_at.desc()).all()
    return [_fmt_supply(r) for r in rows]


@app.get("/api/supply/nearby")
async def nearby_supply(db: Session = Depends(get_db),
                         u: User = Depends(require_shopkeeper)):
    """Shopkeeper sees all active farmer supply in same local body."""
    rows = db.query(SupplyListing).filter(
        SupplyListing.local_body == u.local_body,
        SupplyListing.status == "active",
        SupplyListing.expires_at > datetime.utcnow()
    ).order_by(SupplyListing.created_at.desc()).all()
    return [_fmt_supply(r, show_contact=True) for r in rows]


@app.put("/api/supply/{sid}")
async def update_supply(sid: int, req: SupplyCreate, db: Session = Depends(get_db),
                        u: User = Depends(require_farmer)):
    row = db.query(SupplyListing).filter(
        SupplyListing.id == sid, SupplyListing.farmer_id == u.id).first()
    if not row: raise HTTPException(404, "Listing not found.")
    row.commodity_name = req.commodity_name
    row.quantity = req.quantity; row.unit = req.unit
    row.expected_price = req.expected_price
    row.description = req.description
    db.commit()
    return {"message": "Updated."}


@app.delete("/api/supply/{sid}")
async def delete_supply(sid: int, db: Session = Depends(get_db),
                        u: User = Depends(require_farmer)):
    row = db.query(SupplyListing).filter(
        SupplyListing.id == sid, SupplyListing.farmer_id == u.id).first()
    if not row: raise HTTPException(404, "Listing not found.")
    row.status = "cancelled"; db.commit()
    return {"message": "Listing cancelled."}


def _fmt_supply(r: SupplyListing, show_contact: bool = False):
    d = {
        "id": r.id,
        "commodity_name": r.commodity_name,
        "quantity": r.quantity, "unit": r.unit,
        "expected_price": r.expected_price,
        "description": r.description,
        "district": r.district, "local_body": r.local_body,
        "status": r.status,
        "created_at": str(r.created_at)[:16],
        "expires_at": str(r.expires_at)[:16],
        "farmer_id": r.farmer_id,
        "farmer_name": r.farmer.name if r.farmer else "—",
    }
    if show_contact:
        d["farmer_mobile"] = r.farmer.mobile if r.farmer else "—"
    return d


# ============================================================
# DEMAND LISTINGS — Shopkeeper
# ============================================================
@app.post("/api/demand")
async def create_demand(req: DemandCreate, db: Session = Depends(get_db),
                        u: User = Depends(require_shopkeeper)):
    listing = DemandListing(
        shopkeeper_id=u.id,
        commodity_name=req.commodity_name,
        quantity_needed=req.quantity_needed, unit=req.unit,
        max_price=req.max_price, description=req.description,
        district=u.district,
        local_body_type=u.local_body_type,
        local_body=u.local_body
    )
    db.add(listing); db.commit(); db.refresh(listing)

    # Notify matching farmers in same local body
    matches = db.query(SupplyListing).filter(
        SupplyListing.commodity_name == req.commodity_name,
        SupplyListing.local_body == u.local_body,
        SupplyListing.status == "active"
    ).all()
    for s in matches:
        db.add(Notification(
            user_id=s.farmer_id, title="Shopkeeper Needs Your Produce",
            body=f"{u.name} needs {req.quantity_needed} {req.unit} of {req.commodity_name} in {u.local_body}. Contact: {u.mobile}",
            notif_type="match"
        ))
    db.commit()
    return {"id": listing.id, "message": "Demand listing created."}


@app.get("/api/demand/mine")
async def my_demand(db: Session = Depends(get_db),
                    u: User = Depends(require_shopkeeper)):
    rows = db.query(DemandListing).filter(
        DemandListing.shopkeeper_id == u.id
    ).order_by(DemandListing.created_at.desc()).all()
    return [_fmt_demand(r) for r in rows]


@app.get("/api/demand/nearby")
async def nearby_demand(db: Session = Depends(get_db),
                         u: User = Depends(require_farmer)):
    """Farmer sees all active shopkeeper demands in same local body."""
    rows = db.query(DemandListing).filter(
        DemandListing.local_body == u.local_body,
        DemandListing.status == "active",
        DemandListing.expires_at > datetime.utcnow()
    ).order_by(DemandListing.created_at.desc()).all()
    return [_fmt_demand(r, show_contact=True) for r in rows]


@app.put("/api/demand/{did}")
async def update_demand(did: int, req: DemandCreate, db: Session = Depends(get_db),
                        u: User = Depends(require_shopkeeper)):
    row = db.query(DemandListing).filter(
        DemandListing.id == did, DemandListing.shopkeeper_id == u.id).first()
    if not row: raise HTTPException(404, "Listing not found.")
    row.commodity_name = req.commodity_name
    row.quantity_needed = req.quantity_needed; row.unit = req.unit
    row.max_price = req.max_price; row.description = req.description
    db.commit()
    return {"message": "Updated."}


@app.delete("/api/demand/{did}")
async def delete_demand(did: int, db: Session = Depends(get_db),
                        u: User = Depends(require_shopkeeper)):
    row = db.query(DemandListing).filter(
        DemandListing.id == did, DemandListing.shopkeeper_id == u.id).first()
    if not row: raise HTTPException(404, "Listing not found.")
    row.status = "cancelled"; db.commit()
    return {"message": "Listing cancelled."}


def _fmt_demand(r: DemandListing, show_contact: bool = False):
    d = {
        "id": r.id,
        "commodity_name": r.commodity_name,
        "quantity_needed": r.quantity_needed, "unit": r.unit,
        "max_price": r.max_price,
        "description": r.description,
        "district": r.district, "local_body": r.local_body,
        "status": r.status,
        "created_at": str(r.created_at)[:16],
        "expires_at": str(r.expires_at)[:16],
        "shopkeeper_id": r.shopkeeper_id,
        "shopkeeper_name": r.shopkeeper.name if r.shopkeeper else "—",
    }
    if show_contact:
        d["shopkeeper_mobile"] = r.shopkeeper.mobile if r.shopkeeper else "—"
    return d


# ============================================================
# MATCH REQUESTS
# Flow: Farmer sees nearby demands → sends request to shopkeeper
#       Shopkeeper receives request → accepts or rejects
# ============================================================
@app.post("/api/requests")
async def send_request(req: RequestCreate, db: Session = Depends(get_db),
                       u: User = Depends(require_farmer)):
    supply = None
    if req.supply_id:
        supply = db.query(SupplyListing).filter(
            SupplyListing.id == req.supply_id,
            SupplyListing.farmer_id == u.id
        ).first()
        if not supply: raise HTTPException(404, "Your supply listing not found.")

    demand = db.query(DemandListing).filter(
        DemandListing.id == req.demand_id,
        DemandListing.status == "active"
    ).first()
    if not demand: raise HTTPException(404, "Demand listing not found or inactive.")

    # Prevent duplicate
    existing_query = db.query(MatchRequest).filter(
        MatchRequest.demand_id == req.demand_id,
        MatchRequest.status == "pending",
        MatchRequest.farmer_id == u.id
    )
    if req.supply_id:
        existing_query = existing_query.filter(MatchRequest.supply_id == req.supply_id)
    else:
        existing_query = existing_query.filter(MatchRequest.supply_id == None)
        
    if existing_query.first(): raise HTTPException(400, "Request already sent for this demand.")

    mr = MatchRequest(
        supply_id=req.supply_id, demand_id=req.demand_id,
        farmer_id=u.id, shopkeeper_id=demand.shopkeeper_id,
        message=req.message, status="pending"
    )
    db.add(mr)

    # Notify shopkeeper
    supply_text = f"{supply.quantity} {supply.unit} of {supply.commodity_name}" if supply else "their produce"
    db.add(Notification(
        user_id=demand.shopkeeper_id,
        title=f"Request from {u.name}",
        body=f"{u.name} wants to supply {supply_text}. "
             f"Contact: {u.mobile}. Message: {req.message or '—'}",
        notif_type="request"
    ))
    db.commit(); db.refresh(mr)
    return {"id": mr.id, "message": "Request sent to shopkeeper."}


@app.get("/api/requests/sent")
async def requests_sent(db: Session = Depends(get_db),
                        u: User = Depends(require_farmer)):
    """Farmer sees all requests he has sent."""
    rows = db.query(MatchRequest).filter(
        MatchRequest.farmer_id == u.id
    ).order_by(MatchRequest.created_at.desc()).all()
    return [_fmt_request(r) for r in rows]


@app.get("/api/requests/received")
async def requests_received(db: Session = Depends(get_db),
                             u: User = Depends(require_shopkeeper)):
    """Shopkeeper sees all requests received from farmers."""
    rows = db.query(MatchRequest).filter(
        MatchRequest.shopkeeper_id == u.id
    ).order_by(MatchRequest.created_at.desc()).all()
    return [_fmt_request(r, show_farmer_contact=True) for r in rows]


@app.patch("/api/requests/{rid}/respond")
async def respond_to_request(rid: int, body: RequestRespond,
                              db: Session = Depends(get_db),
                              u: User = Depends(require_shopkeeper)):
    mr = db.query(MatchRequest).filter(
        MatchRequest.id == rid,
        MatchRequest.shopkeeper_id == u.id,
        MatchRequest.status == "pending"
    ).first()
    if not mr: raise HTTPException(404, "Request not found or already responded.")
    if body.status not in ("accepted", "rejected"):
        raise HTTPException(400, "Status must be accepted or rejected.")

    mr.status = body.status
    mr.shopkeeper_note = body.shopkeeper_note
    mr.updated_at = datetime.utcnow()

    # Notify farmer of decision with shopkeeper phone number
    action = "accepted ✅" if body.status == "accepted" else "rejected ❌"
    commodity_name = mr.supply.commodity_name if mr.supply else (mr.demand.commodity_name if mr.demand else "their produce")
    
    db.add(Notification(
        user_id=mr.farmer_id,
        title=f"Request {body.status.capitalize()}",
        body=f"{u.name} has {action} your supply request for {commodity_name}. "
             f"Contact: {u.mobile}. Note: {body.shopkeeper_note or '—'}",
        notif_type=body.status
    ))

    # If accepted, mark supply as sold, demand as fulfilled,
    # and cancel all other pending requests/offers for the same supply
    if body.status == "accepted":
        if mr.supply: mr.supply.status = "sold"
        if mr.demand: mr.demand.status = "fulfilled"
        if mr.supply:
            _close_other_pending(db, supply_id=mr.supply.id, accepted_id=mr.id,
                                 commodity=commodity_name)

    db.commit()
    return {"message": f"Request {body.status}."}


# ============================================================
# SHOPKEEPER-INITIATED OFFERS
# New reverse flow:
#   1. Shopkeeper sees nearby supply listings
#   2. Shopkeeper sends an offer directly to a farmer
#   3. Farmer sees incoming offers and accepts or rejects
# Stored in same MatchRequest table — differentiated by
# initiated_by = "shopkeeper" (we reuse shopkeeper_note field
# for the offer message so no schema change needed, just use
# the existing table smartly).
# ============================================================

@app.post("/api/offers")
async def send_offer(req: OfferCreate, db: Session = Depends(get_db),
                     u: User = Depends(require_shopkeeper)):
    """Shopkeeper sends a purchase offer to a farmer for their supply listing."""
    supply = db.query(SupplyListing).filter(
        SupplyListing.id == req.supply_id,
        SupplyListing.status == "active",
        SupplyListing.expires_at > datetime.utcnow()
    ).first()
    if not supply:
        raise HTTPException(404, "Supply listing not found or expired.")

    # Prevent duplicate pending offers from same shopkeeper for same supply
    existing = db.query(MatchRequest).filter(
        MatchRequest.supply_id == req.supply_id,
        MatchRequest.shopkeeper_id == u.id,
        MatchRequest.status == "pending",
        MatchRequest.demand_id == None
    ).first()
    if existing:
        raise HTTPException(400, "You already sent a pending offer for this supply.")

    # Build offer message including price if provided
    offer_msg = req.message or ""
    if req.offer_price:
        price_note = f"[Offered Price: ₹{req.offer_price}/{supply.unit}]"
        offer_msg = f"{price_note} {offer_msg}".strip()

    mr = MatchRequest(
        supply_id=req.supply_id,
        demand_id=None,                    # no demand listing — shopkeeper-initiated
        farmer_id=supply.farmer_id,
        shopkeeper_id=u.id,
        message=offer_msg or None,
        status="pending"
    )
    db.add(mr)

    # Notify farmer
    price_text = f" at ₹{req.offer_price}/{supply.unit}" if req.offer_price else ""
    db.add(Notification(
        user_id=supply.farmer_id,
        title=f"Purchase Offer from {u.name}",
        body=(f"{u.name} wants to buy your {supply.quantity} {supply.unit} of "
              f"{supply.commodity_name}{price_text}. "
              f"Contact: {u.mobile}. "
              f"Message: {req.message or '—'}"),
        notif_type="offer"
    ))
    db.commit(); db.refresh(mr)
    return {"id": mr.id, "message": "Offer sent to farmer."}


@app.get("/api/offers/received")
async def offers_received(db: Session = Depends(get_db),
                          u: User = Depends(require_farmer)):
    """Farmer sees all shopkeeper offers on their supply listings."""
    rows = db.query(MatchRequest).filter(
        MatchRequest.farmer_id == u.id,
        MatchRequest.demand_id == None       # shopkeeper-initiated = no demand_id
    ).order_by(MatchRequest.created_at.desc()).all()
    return [_fmt_offer(r) for r in rows]


@app.get("/api/offers/sent")
async def offers_sent(db: Session = Depends(get_db),
                      u: User = Depends(require_shopkeeper)):
    """Shopkeeper sees all offers they have sent."""
    rows = db.query(MatchRequest).filter(
        MatchRequest.shopkeeper_id == u.id,
        MatchRequest.demand_id == None
    ).order_by(MatchRequest.created_at.desc()).all()
    return [_fmt_offer(r) for r in rows]


@app.patch("/api/offers/{oid}/respond")
async def respond_to_offer(oid: int, body: OfferRespond,
                           db: Session = Depends(get_db),
                           u: User = Depends(require_farmer)):
    """Farmer accepts or rejects a shopkeeper's offer."""
    mr = db.query(MatchRequest).filter(
        MatchRequest.id == oid,
        MatchRequest.farmer_id == u.id,
        MatchRequest.demand_id == None,
        MatchRequest.status == "pending"
    ).first()
    if not mr:
        raise HTTPException(404, "Offer not found or already responded.")
    if body.status not in ("accepted", "rejected"):
        raise HTTPException(400, "Status must be accepted or rejected.")

    mr.status = body.status
    mr.shopkeeper_note = body.farmer_note   # reuse field for farmer's reply note
    mr.updated_at = datetime.utcnow()

    # Get shopkeeper info for notification
    sk = db.query(User).filter(User.id == mr.shopkeeper_id).first()
    commodity_name = mr.supply.commodity_name if mr.supply else "your produce"
    action_text = "accepted ✅" if body.status == "accepted" else "rejected ❌"

    # Notify shopkeeper of farmer's decision
    db.add(Notification(
        user_id=mr.shopkeeper_id,
        title=f"Offer {body.status.capitalize()} by {u.name}",
        body=(f"{u.name} has {action_text} your purchase offer for "
              f"{commodity_name}. Contact: {u.mobile}. "
              f"Note: {body.farmer_note or '—'}"),
        notif_type=body.status
    ))

    # If accepted, mark supply as sold and cancel all other pending
    # requests/offers for the same supply listing
    if body.status == "accepted" and mr.supply:
        mr.supply.status = "sold"
        _close_other_pending(db, supply_id=mr.supply.id, accepted_id=mr.id,
                             commodity=commodity_name)

    db.commit()
    return {"message": f"Offer {body.status}."}



def _close_other_pending(db, supply_id: int, accepted_id: int, commodity: str):
    """
    When a supply listing is accepted by one buyer, reject all other
    pending MatchRequests (both farmer-initiated and shopkeeper-initiated)
    that reference the same supply_id, and notify each affected party.
    """
    others = db.query(MatchRequest).filter(
        MatchRequest.supply_id == supply_id,
        MatchRequest.id != accepted_id,
        MatchRequest.status == "pending"
    ).all()

    for other in others:
        other.status = "rejected"
        other.shopkeeper_note = "Supply already sold to another buyer."
        other.updated_at = datetime.utcnow()

        # Determine who to notify and with what message
        if other.demand_id is None:
            # Shopkeeper-initiated offer — notify the shopkeeper
            db.add(Notification(
                user_id=other.shopkeeper_id,
                title=f"{commodity} No Longer Available",
                body=(f"Sorry, the supply listing for {commodity} you made an offer on "
                      f"has been sold to another buyer. Please check for other listings."),
                notif_type="rejected"
            ))
        else:
            # Farmer-initiated request — notify the shopkeeper that pending
            # request is now auto-rejected because farmer sold elsewhere
            db.add(Notification(
                user_id=other.shopkeeper_id,
                title=f"{commodity} Supply Sold",
                body=(f"A pending request for {commodity} has been automatically closed "
                      f"because the farmer sold their produce to another buyer."),
                notif_type="rejected"
            ))


def _fmt_offer(r: MatchRequest):
    return {
        "id": r.id,
        "status": r.status,
        "message": r.message,
        "farmer_note": r.shopkeeper_note,   # farmer's reply stored here
        "created_at": str(r.created_at)[:16],
        "updated_at": str(r.updated_at)[:16],
        "farmer_id": r.farmer_id,
        "farmer_name": r.farmer.name if r.farmer else "—",
        "farmer_mobile": r.farmer.mobile if r.farmer else "—",
        "shopkeeper_id": r.shopkeeper_id,
        "shopkeeper_name": r.shopkeeper.name if r.shopkeeper else "—",
        "shopkeeper_mobile": r.shopkeeper.mobile if r.shopkeeper else "—",
        "supply": {
            "id": r.supply.id,
            "commodity_name": r.supply.commodity_name,
            "quantity": r.supply.quantity,
            "unit": r.supply.unit,
            "expected_price": r.supply.expected_price,
        } if r.supply else {},
    }




def _fmt_request(r: MatchRequest, show_farmer_contact: bool = False):
    d = {
        "id": r.id,
        "status": r.status,
        "message": r.message,
        "shopkeeper_note": r.shopkeeper_note,
        "created_at": str(r.created_at)[:16],
        "updated_at": str(r.updated_at)[:16],
        "farmer_id": r.farmer_id,
        "farmer_name": r.farmer.name if r.farmer else "—",
        "shopkeeper_id": r.shopkeeper_id,
        "shopkeeper_name": r.shopkeeper.name if r.shopkeeper else "—",
        "supply": {
            "id": r.supply.id,
            "commodity_name": r.supply.commodity_name,
            "quantity": r.supply.quantity,
            "unit": r.supply.unit,
            "expected_price": r.supply.expected_price,
        } if r.supply else {},
        "demand": {
            "id": r.demand.id,
            "commodity_name": r.demand.commodity_name,
            "quantity_needed": r.demand.quantity_needed,
            "unit": r.demand.unit,
            "max_price": r.demand.max_price,
        } if r.demand else {},
    }
    if show_farmer_contact:
        d["farmer_mobile"] = r.farmer.mobile if r.farmer else "—"
    return d


# ============================================================
# NOTIFICATIONS
# ============================================================
@app.get("/api/notifications")
async def get_notifications(db: Session = Depends(get_db),
                             u: User = Depends(get_current_user)):
    rows = db.query(Notification).filter(
        Notification.user_id == u.id
    ).order_by(Notification.created_at.desc()).limit(30).all()
    return [{"id": n.id, "title": n.title, "body": n.body,
             "type": n.notif_type, "is_read": n.is_read,
             "created_at": str(n.created_at)[:16]} for n in rows]


@app.get("/api/notifications/unread-count")
async def unread_count(db: Session = Depends(get_db),
                       u: User = Depends(get_current_user)):
    count = db.query(Notification).filter(
        Notification.user_id == u.id,
        Notification.is_read == False
    ).count()
    return {"count": count}


@app.patch("/api/notifications/{nid}/read")
async def mark_read(nid: int, db: Session = Depends(get_db),
                    u: User = Depends(get_current_user)):
    n = db.query(Notification).filter(
        Notification.id == nid, Notification.user_id == u.id).first()
    if n: n.is_read = True; db.commit()
    return {"message": "Marked read."}


@app.patch("/api/notifications/read-all")
async def mark_all_read(db: Session = Depends(get_db),
                        u: User = Depends(get_current_user)):
    db.query(Notification).filter(
        Notification.user_id == u.id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked read."}


# ============================================================
# CHATBOT
# ============================================================

@app.post("/api/chat/public")
async def chat_public(req: ChatRequest, db: Session = Depends(get_db)):
    """Public chatbot — no auth required. For landing page visitors."""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        return {"reply": "VilaNeram AI is being set up. Register now and start using the marketplace!"}

    # Fetch latest prices from DB
    today_prices = db.query(CommodityPrice).order_by(CommodityPrice.price_date.desc()).limit(150).all()
    seen = {}
    for p in today_prices:
        if p.commodity_name not in seen:
            seen[p.commodity_name] = p
    prices_block = "\n".join([
        f"  {n}: \u20b9{p.price:.2f} (as of {p.price_date})"
        for n, p in list(seen.items())[:25]
    ]) or "  (price data not loaded yet — admin please run Fetch)"

    system_prompt = f"""You are VilaNeram AI, the assistant for VilaNeram — a free Kerala agricultural marketplace connecting farmers and shopkeepers.

ABOUT VILANERAM:
- Free platform for Kerala farmers and shopkeepers
- Farmers: post produce listings, see nearby shopkeeper demands, get 7-day AI price forecasts, use profit calculator, send/receive trade requests
- Shopkeepers: post requirements, browse nearby farmer supply, send direct purchase offers to farmers
- Prices from official Ecostat Kerala Government API — updated daily
- AI price forecast uses XGBoost model trained on real Kerala commodity price history
- Location-aware — matches buyers and sellers within the same panchayath/local body

CURRENT KERALA MARKET PRICES (Ecostat Kerala official data):
{prices_block}

YOUR BEHAVIOUR:
- You are talking to a VISITOR who has not yet logged in
- Answer questions about VilaNeram features, Kerala agriculture, and commodity prices
- Use the real prices above when answering price questions — NEVER make up prices
- Keep answers SHORT (3-5 lines), warm, and practical
- Encourage visitors to register — it is completely free
- You may use Malayalam greetings like Namaskaram naturally
- Guide visitors: Register → Post Supply or Post Requirement → Connect with buyers/sellers
- Today: {date.today().strftime("%d %B %Y")}
"""
    try:
        import httpx
        messages = [{"role": "system", "content": system_prompt}]
        for h in (req.history or []):
            messages.append(h)
        messages.append({"role": "user", "content": req.message})
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}",
                         "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": messages,
                      "max_tokens": 300, "temperature": 0.65},
                timeout=20
            )
            data = resp.json()
            return {"reply": data["choices"][0]["message"]["content"]}
    except Exception as e:
        logger.error(f"Public chat error: {e}")
        return {"reply": "Sorry, could not reach VilaNeram AI right now. Please try again in a moment!"}


@app.post("/api/chat")
async def chat(req: ChatRequest, db: Session = Depends(get_db),
               u: User = Depends(get_current_user)):
    """Authenticated chatbot — personalised with user's live data."""
    groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        return {"reply": "VilaNeram AI: Set GROQ_API_KEY in .env for full AI responses."}

    import json as _json

    # Parse user's tracked commodities
    try:
        my_comms = _json.loads(u.commodities) if u.commodities else []
    except Exception:
        my_comms = []

    # Fetch latest prices
    today_prices = db.query(CommodityPrice).order_by(CommodityPrice.price_date.desc()).limit(150).all()
    seen = {}
    for p in today_prices:
        if p.commodity_name not in seen:
            seen[p.commodity_name] = p
    prices_block = "\n".join([
        f"  {n}: \u20b9{p.price:.2f}"
        for n, p in list(seen.items())[:20]
    ]) or "  (no price data yet)"

    # Build role-specific context
    if u.role == "farmer":
        supply = db.query(SupplyListing).filter(
            SupplyListing.farmer_id == u.id, SupplyListing.status == "active"
        ).all()
        supply_txt = ", ".join([
            f"{s.commodity_name} {s.quantity}{s.unit}" +
            (f" @ \u20b9{s.expected_price}" if s.expected_price else "")
            for s in supply
        ]) or "none"

        demands = db.query(DemandListing).filter(
            DemandListing.local_body == u.local_body,
            DemandListing.status == "active",
            DemandListing.expires_at > datetime.utcnow()
        ).all()
        demand_txt = ", ".join([
            f"{d.commodity_name} ({d.quantity_needed}{d.unit}) by {d.shopkeeper.name if d.shopkeeper else 'shopkeeper'}"
            + (f" max \u20b9{d.max_price}" if d.max_price else "")
            for d in demands[:5]
        ]) or "none"

        pending_offers = db.query(MatchRequest).filter(
            MatchRequest.farmer_id == u.id,
            MatchRequest.demand_id == None,
            MatchRequest.status == "pending"
        ).count()

        role_ctx = f"""USER: Farmer — {u.name}
LOCATION: {u.local_body or "—"}, {u.district or "Kerala"}
TRACKED COMMODITIES: {", ".join(my_comms) or "none set"}
ACTIVE SUPPLY LISTINGS: {supply_txt}
NEARBY SHOPKEEPER DEMANDS in {u.local_body or "their area"}: {demand_txt}
PENDING PURCHASE OFFERS FROM SHOPKEEPERS: {pending_offers}"""

    elif u.role == "shopkeeper":
        my_demands = db.query(DemandListing).filter(
            DemandListing.shopkeeper_id == u.id, DemandListing.status == "active"
        ).all()
        demand_txt = ", ".join([
            f"{d.commodity_name} {d.quantity_needed}{d.unit}"
            + (f" max \u20b9{d.max_price}" if d.max_price else "")
            for d in my_demands
        ]) or "none"

        nearby = db.query(SupplyListing).filter(
            SupplyListing.local_body == u.local_body,
            SupplyListing.status == "active",
            SupplyListing.expires_at > datetime.utcnow()
        ).all()
        supply_txt = ", ".join([
            f"{s.commodity_name} {s.quantity}{s.unit} from {s.farmer.name if s.farmer else 'farmer'}"
            + (f" @ \u20b9{s.expected_price}" if s.expected_price else " (negotiable)")
            for s in nearby[:5]
        ]) or "none"

        pending_req = db.query(MatchRequest).filter(
            MatchRequest.shopkeeper_id == u.id,
            MatchRequest.status == "pending"
        ).count()

        role_ctx = f"""USER: Shopkeeper — {u.name}
LOCATION: {u.local_body or "—"}, {u.district or "Kerala"}
MY ACTIVE REQUIREMENTS: {demand_txt}
NEARBY FARMER SUPPLY in {u.local_body or "their area"}: {supply_txt}
PENDING FARMER REQUESTS WAITING FOR RESPONSE: {pending_req}"""

    else:
        role_ctx = f"USER: Admin — {u.name}"

    system_prompt = f"""You are VilaNeram AI — the agricultural assistant for VilaNeram, a Kerala farmer-shopkeeper marketplace.

{role_ctx}

CURRENT MARKET PRICES (Ecostat Kerala official data):
{prices_block}

YOUR BEHAVIOUR:
- You have the user's REAL live data above — give specific, personalised advice
- When farmer asks "should I sell today" — check their listings and nearby demands above
- When shopkeeper asks about availability — check their nearby farmer supply above
- Always mention actual \u20b9 prices from the data above when relevant
- Keep answers SHORT (3-5 lines), practical — these are mobile users
- Simple English; you may use Malayalam naturally (Namaskaram, sheriyanu, njan)
- NEVER make up prices — only use figures shown above
- Guide users to VilaNeram features: Post Supply, Post Requirement, Send Offer, Price Forecast, Profit Calculator
- Today: {date.today().strftime("%d %B %Y")}
"""
    try:
        import httpx
        messages = [{"role": "system", "content": system_prompt}]
        for h in (req.history or []):
            messages.append(h)
        messages.append({"role": "user", "content": req.message})
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_key}",
                         "Content-Type": "application/json"},
                json={"model": "llama-3.3-70b-versatile", "messages": messages,
                      "max_tokens": 400, "temperature": 0.6},
                timeout=20
            )
            data = resp.json()
            return {"reply": data["choices"][0]["message"]["content"]}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"reply": "Sorry, could not process that. Please try again."}


# ============================================================
# ADMIN ROUTES
# ============================================================
@app.get("/api/admin/stats")
async def admin_stats(db: Session = Depends(get_db),
                      admin: User = Depends(require_admin)):
    farmers      = db.query(User).filter(User.role == "farmer").count()
    shopkeepers  = db.query(User).filter(User.role == "shopkeeper").count()
    active_supply = db.query(SupplyListing).filter(SupplyListing.status == "active").count()
    active_demand = db.query(DemandListing).filter(DemandListing.status == "active").count()
    total_requests = db.query(MatchRequest).count()
    accepted = db.query(MatchRequest).filter(MatchRequest.status == "accepted").count()
    price_records = db.query(CommodityPrice).count()
    last_fetch = db.query(FetchLog).order_by(FetchLog.created_at.desc()).first()
    return {
        "farmers": farmers, "shopkeepers": shopkeepers,
        "active_supply": active_supply, "active_demand": active_demand,
        "total_requests": total_requests, "accepted_requests": accepted,
        "price_records": price_records,
        "last_fetch": {
            "date": str(last_fetch.fetch_date) if last_fetch else "Never",
            "inserted": last_fetch.inserted if last_fetch else 0,
        }
    }


@app.get("/api/admin/district-stats")
async def admin_district_stats(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    districts = {}

    for row in db.query(User.district, func.count(User.id)).filter(User.role == "farmer", User.district.isnot(None), User.district != "").group_by(User.district).all():
        districts.setdefault(row[0], {"farmers": 0, "shopkeepers": 0, "supply": 0, "demand": 0})["farmers"] = row[1]
    
    for row in db.query(User.district, func.count(User.id)).filter(User.role == "shopkeeper", User.district.isnot(None), User.district != "").group_by(User.district).all():
        districts.setdefault(row[0], {"farmers": 0, "shopkeepers": 0, "supply": 0, "demand": 0})["shopkeepers"] = row[1]

    for row in db.query(SupplyListing.district, func.count(SupplyListing.id)).filter(SupplyListing.status == "active", SupplyListing.district.isnot(None), SupplyListing.district != "").group_by(SupplyListing.district).all():
        districts.setdefault(row[0], {"farmers": 0, "shopkeepers": 0, "supply": 0, "demand": 0})["supply"] = row[1]

    for row in db.query(DemandListing.district, func.count(DemandListing.id)).filter(DemandListing.status == "active", DemandListing.district.isnot(None), DemandListing.district != "").group_by(DemandListing.district).all():
        districts.setdefault(row[0], {"farmers": 0, "shopkeepers": 0, "supply": 0, "demand": 0})["demand"] = row[1]

    top_commodities = [{"name": r[0], "count": r[1]} for r in db.query(SupplyListing.commodity_name, func.count(SupplyListing.id)).filter(SupplyListing.status == "active").group_by(SupplyListing.commodity_name).order_by(func.count(SupplyListing.id).desc()).limit(10).all()]

    today = datetime.utcnow().date()
    trend_dict = {(today - timedelta(days=i)).isoformat(): 0 for i in range(6, -1, -1)}
    
    # fetch requests for the last 7 days
    recent_date = datetime.utcnow() - timedelta(days=7)
    for req in db.query(MatchRequest).filter(MatchRequest.created_at >= recent_date).all():
        d_str = req.created_at.date().isoformat()
        if d_str in trend_dict:
            trend_dict[d_str] += 1
    request_trend = [{"date": k, "count": v} for k, v in trend_dict.items()]

    fh_rows = db.query(FetchLog).order_by(FetchLog.fetch_date.desc()).limit(14).all()
    fetch_history = [{"date": str(f.fetch_date), "inserted": f.inserted, "skipped": f.skipped, "triggered_by": f.triggered_by, "status": f.status} for f in reversed(fh_rows)]

    me_rows = db.query(ModelEvaluation).order_by(ModelEvaluation.created_at.desc()).limit(1).all()
    model_evals = [{"rmse": e.rmse, "mape": e.mape, "r2": e.r2_score, "samples": e.test_samples, "created_at": str(e.created_at)[:16]} for e in me_rows]

    return {
        "districts": districts,
        "top_commodities": top_commodities,
        "request_trend": request_trend,
        "fetch_history": fetch_history,
        "model_evals": model_evals
    }


@app.get("/api/admin/users")
async def admin_users(db: Session = Depends(get_db),
                      admin: User = Depends(require_admin)):
    users = db.query(User).filter(User.role != "admin").order_by(
        User.created_at.desc()).all()
    return [{
        "id": u.id, "name": u.name, "mobile": u.mobile,
        "role": u.role, "district": u.district,
        "local_body": u.local_body, "is_active": u.is_active,
        "created_at": str(u.created_at)[:10],
        "last_login": str(u.last_login)[:16] if u.last_login else "Never"
    } for u in users]


@app.patch("/api/admin/users/{uid}/status")
async def toggle_user(uid: int, body: UserStatusUpdate,
                      db: Session = Depends(get_db),
                      admin: User = Depends(require_admin)):
    u = db.query(User).filter(User.id == uid).first()
    if not u: raise HTTPException(404, "User not found.")
    u.is_active = body.is_active; db.commit()
    return {"message": f"User {'activated' if body.is_active else 'deactivated'}."}


@app.post("/api/admin/fetch-data")
async def manual_fetch(db: Session = Depends(get_db),
                       admin: User = Depends(require_admin)):
    try:
        result = fetch_and_store(db, triggered_by="admin")
        return result
    except Exception as e:
        raise HTTPException(500, f"Fetch failed: {e}")


@app.post("/api/admin/train")
async def manual_train(db: Session = Depends(get_db),
                       admin: User = Depends(require_admin)):
    global _global_model, _model_trained_date
    system = AgriculturalForecastSystem(db=db)
    result = system.train_model()
    if not result: raise HTTPException(500, "Training failed.")
    import joblib as _jl
    _global_model = _jl.load(system.model_file)
    _model_trained_date = date.today()
    return {"message": "Model trained.", "performance": result}


@app.get("/api/admin/price-report")
async def price_report(db: Session = Depends(get_db),
                       admin: User = Depends(require_admin)):
    rows = db.query(CommodityPrice).order_by(
        CommodityPrice.price_date.asc(),
        CommodityPrice.commodity_name.asc()
    ).all()
    return [{"date": str(r.price_date), "commodity_name": r.commodity_name,
             "category": r.category or "—",
             "price": round(r.price, 2),
             "prev_month_price": round(r.prev_month_price, 2) if r.prev_month_price else None}
            for r in rows]


# ============================================================
# RUN
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)