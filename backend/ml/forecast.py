# backend/ml/forecast.py
# ============================================================
# VILANERAM — XGBoost Price Forecasting Engine
# ============================================================
# Rules:
#   - NO fake/sample data anywhere
#   - NO rule-based predictions
#   - Data comes ONLY from Ecostat Kerala API (stored in DB)
#   - Model trains ONLY on real fetched prices
#   - Prediction uses ONLY the trained XGBoost model
# ============================================================

import os
import pandas as pd
import numpy as np
import xgboost as xgb
import joblib
from datetime import datetime, timedelta
import logging
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sqlalchemy.orm import Session

MODEL_FILE = "xgboost_model.pkl"
logger = logging.getLogger(__name__)


class AgriculturalForecastSystem:
    def __init__(self, db: Session = None):
        self.db = db
        self.model_file = MODEL_FILE
        self.feature_columns = None
        self.reg_model = None

    def set_db(self, db: Session):
        self.db = db

    # ============================================================
    # STEP 1 — LOAD REAL DATA FROM DB
    # Data was fetched from Ecostat API by ecostat_fetcher.py
    # and stored in commodity_prices table.
    # Column names must match database.py exactly.
    # ============================================================
    def load_data_from_db(self, commodity=None, category=None) -> pd.DataFrame:
        from ..database import CommodityPrice

        query = self.db.query(CommodityPrice)
        if commodity:
            query = query.filter(CommodityPrice.commodity_name == commodity)
        if category and category.strip():
            query = query.filter(CommodityPrice.category == category)

        rows = query.order_by(CommodityPrice.price_date).all()

        if not rows:
            logger.warning(f"No data in DB for commodity='{commodity}'")
            return pd.DataFrame()

        records = [{
            "Date":      r.price_date,
            "Price":     r.price,            # real Ecostat price
            "Commodity": r.commodity_name,
            "Category":  getattr(r, "category", "") or "",
        } for r in rows]

        df = pd.DataFrame(records)
        df["Date"]  = pd.to_datetime(df["Date"])
        df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
        df = df.dropna(subset=["Price"])
        df = df[df["Price"] > 0]
        logger.info(f"Loaded {len(df)} real rows for '{commodity or 'ALL'}'")
        return df

    # ============================================================
    # STEP 2 — FEATURE ENGINEERING
    # All features derived from real price history only.
    # No external inputs, no fake values.
    # ============================================================
    def create_features(self, df: pd.DataFrame, is_training: bool = True) -> pd.DataFrame:
        df = df.copy()
        df = df.sort_values(["Commodity", "Date"]).reset_index(drop=True)
        df = df.drop_duplicates(subset=["Date", "Commodity"], keep="last")

        # Calendar features
        df["Year"]      = df["Date"].dt.year
        df["Month"]     = df["Date"].dt.month
        df["Day"]       = df["Date"].dt.day
        df["Weekday"]   = df["Date"].dt.weekday
        df["Quarter"]   = df["Date"].dt.quarter
        df["DayOfYear"] = df["Date"].dt.dayofyear
        df["Is_Monsoon"] = df["Month"].isin([6, 7, 8, 9]).astype(int)
        df["Is_Harvest"] = df["Month"].isin([10, 11, 12]).astype(int)

        # Lag features — past prices as inputs
        g = df.groupby("Commodity")["Price"]
        for lag in [1, 2, 3, 5, 7, 14, 30]:
            df[f"Lag_{lag}"] = g.shift(lag)

        # Rolling statistics
        for w in [3, 7, 14, 30]:
            rolled = g.transform(lambda x: x.rolling(w, min_periods=1))
            df[f"RollMean_{w}"] = g.transform(lambda x: x.rolling(w, min_periods=1).mean())
            df[f"RollStd_{w}"]  = g.transform(lambda x: x.rolling(w, min_periods=1).std().fillna(0))
            df[f"RollMin_{w}"]  = g.transform(lambda x: x.rolling(w, min_periods=1).min())
            df[f"RollMax_{w}"]  = g.transform(lambda x: x.rolling(w, min_periods=1).max())

        # Price position (where is today's price relative to recent range)
        df["PricePos_7d"]  = (df["Price"] - df["RollMin_7"])  / (df["RollMax_7"]  - df["RollMin_7"]  + 1e-8)
        df["PricePos_30d"] = (df["Price"] - df["RollMin_30"]) / (df["RollMax_30"] - df["RollMin_30"] + 1e-8)

        # Momentum and returns
        df["Return_1d"]     = g.pct_change(1)
        df["Return_7d"]     = g.pct_change(7)
        df["Volatility_7d"] = g.transform(lambda x: x.pct_change().rolling(7, min_periods=1).std().fillna(0))
        df["Momentum_7d"]   = df["Price"] / (df["Lag_7"]  + 1e-8) - 1
        df["Momentum_14d"]  = df["Price"] / (df["Lag_14"] + 1e-8) - 1

        # Target: next day's real price (training only)
        if is_training:
            df["Target"] = g.shift(-1)

        df = df.dropna()

        skip = ["Date", "Commodity", "Category", "Price"]
        if is_training:
            skip.append("Target")
        self.feature_columns = [c for c in df.columns if c not in skip]

        return df

    # ============================================================
    # STEP 3 — TRAIN
    # Trains on ALL real commodities data from DB.
    # One global model — learns price patterns across all Kerala
    # agricultural commodities.
    # ============================================================
    def train_model(self):
        logger.info("Loading real data from DB for training...")

        df = self.load_data_from_db()  # load ALL commodities
        if df.empty:
            logger.error("DB has no data. Cannot train. Run Fetch first.")
            return False

        n_commodities = df["Commodity"].nunique()
        logger.info(f"Training on {len(df)} rows across {n_commodities} commodities")

        processed = self.create_features(df, is_training=True)
        if processed.empty:
            logger.error("Feature engineering produced empty dataframe.")
            return False

        X = processed[self.feature_columns]
        y = processed["Target"]

        # Time-based train/test split (no data leakage)
        split = int(len(X) * 0.8)
        X_train, X_test = X.iloc[:split], X.iloc[split:]
        y_train, y_test = y.iloc[:split], y.iloc[split:]

        logger.info(f"Training: {len(X_train)} rows | Test: {len(X_test)} rows")

        self.reg_model = xgb.XGBRegressor(
            n_estimators=500,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            verbosity=0
        )
        self.reg_model.fit(X_train, y_train)

        y_pred = self.reg_model.predict(X_test)
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        mae  = float(mean_absolute_error(y_test, y_pred))
        mape = float(np.mean(np.abs((y_test - y_pred) / (np.abs(y_test) + 1e-8))) * 100)
        r2   = float(r2_score(y_test, y_pred))

        logger.info(f"Model trained — RMSE: ₹{rmse:.2f}, MAPE: {mape:.1f}%, R²: {r2:.3f}")

        # Save evaluation to DB
        try:
            from ..database import ModelEvaluation, TrainingLog
            self.db.add(ModelEvaluation(
                rmse=rmse, mae=mae, mape=mape, r2_score=r2,
                test_samples=len(X_test), data_samples=len(processed)
            ))
            self.db.add(TrainingLog(
                data_samples=processed.shape[0],
                data_features=processed.shape[1],
                price_rmse=rmse, status="success"
            ))
            self.db.commit()
        except Exception as e:
            logger.warning(f"Could not save eval to DB: {e}")

        # Save model to disk
        joblib.dump({
            "reg_model":       self.reg_model,
            "feature_columns": self.feature_columns,
            "train_date":      datetime.now(),
            "n_commodities":   n_commodities,
            "n_rows":          len(df),
            "performance":     {"rmse": rmse, "mae": mae, "mape": mape, "r2": r2}
        }, self.model_file)

        return {"rmse": rmse, "mae": mae, "mape": mape, "r2": r2}

    def load_model(self):
        if not os.path.exists(self.model_file):
            return False
        try:
            info = joblib.load(self.model_file)
            self.reg_model       = info["reg_model"]
            self.feature_columns = info["feature_columns"]
            logger.info(f"Model loaded. Trained: {info.get('train_date','?')} | Rows: {info.get('n_rows','?')}")
            return True
        except Exception as e:
            logger.error(f"Model load error: {e}")
            return False

    # ============================================================
    # STEP 4 — PREDICT
    # Uses the trained XGBoost model + real price history from DB
    # to forecast next N days for a specific commodity.
    # No rules, no fallbacks, no fake data.
    # ============================================================
    def predict_future(self, commodity: str, category: str, prediction_days: int = 7):
        if not self.reg_model:
            if not self.load_model():
                logger.error("No trained model available.")
                return None

        # Load real history for this commodity
        df = self.load_data_from_db(commodity=commodity)
        if df.empty:
            logger.error(f"No real data found for '{commodity}'. Cannot predict.")
            return None

        processed = self.create_features(df, is_training=False)
        if processed.empty:
            logger.error(f"Feature engineering failed for '{commodity}'.")
            return None

        predictions = []

        # Keep a rolling buffer of raw rows — always >= 60 so create_features
        # has enough data to compute lag-30 and rolling-30 features without
        # dropping rows due to NaN, which was causing the loop to die after 3
        # iterations.
        raw_buffer = df.tail(90).copy()   # start with last 90 real rows

        for day in range(prediction_days):
            # Re-engineer features on current buffer (always has plenty of rows)
            feat = self.create_features(raw_buffer, is_training=False)
            if feat.empty:
                logger.warning(f"Feature engineering empty at day {day+1}, stopping.")
                break

            latest_row = feat.iloc[[-1]]

            # Guard: make sure all expected feature columns exist
            missing = [c for c in self.feature_columns if c not in latest_row.columns]
            if missing:
                logger.warning(f"Missing feature columns at day {day+1}: {missing}")
                break

            X = latest_row[self.feature_columns]
            price_pred = float(self.reg_model.predict(X)[0])
            price_pred = max(round(price_pred, 2), 0.01)

            prev_price = (
                float(df["Price"].iloc[-1])
                if day == 0
                else predictions[-1]["price"]
            )
            trend = "Rise" if price_pred > prev_price else "Fall"

            predictions.append({
                "date":  (datetime.now() + timedelta(days=day + 1)).strftime("%Y-%m-%d"),
                "day":   day + 1,
                "price": price_pred,
                "trend": trend,
            })

            # Append predicted price as a new raw row so next iteration has it
            last_date = raw_buffer["Date"].iloc[-1]
            new_raw = pd.DataFrame([{
                "Date":      pd.to_datetime(last_date) + timedelta(days=1),
                "Price":     price_pred,
                "Commodity": commodity,
                "Category":  category or "",
            }])
            raw_buffer = pd.concat([raw_buffer, new_raw], ignore_index=True)

        logger.info(f"Predicted {len(predictions)} days for '{commodity}'")
        return predictions

    # ============================================================
    # TREND ANALYSIS
    # ============================================================
    def analyze_trend(self, predictions: list) -> dict:
        if not predictions:
            return {}
        rise  = sum(1 for p in predictions if p["trend"] == "Rise")
        fall  = sum(1 for p in predictions if p["trend"] == "Fall")
        first = predictions[0]["price"]
        last  = predictions[-1]["price"]
        change = ((last - first) / (first + 1e-8)) * 100

        if rise > fall:
            direction = "BULLISH"
            short = f"Prices expected to rise by ₹{abs(last-first):.2f} over 7 days. Consider holding."
        elif fall > rise:
            direction = "BEARISH"
            short = f"Prices expected to fall by ₹{abs(last-first):.2f} over 7 days. Consider selling now."
        else:
            direction = "NEUTRAL"
            short = "Prices expected to remain stable. Monitor daily."

        return {
            "direction":      direction,
            "rise_days":      rise,
            "fall_days":      fall,
            "overall_change": round(change, 2),
            "starting_price": first,
            "ending_price":   last,
            "short":          short,
        }