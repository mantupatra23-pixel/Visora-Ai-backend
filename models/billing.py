# models/billing.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship, declarative_base
import datetime

Base = declarative_base()

def now():
    return datetime.datetime.utcnow()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255))
    created_at = Column(DateTime, default=now)

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    stripe_subscription_id = Column(String(255), unique=True, index=True)
    price_id = Column(String(255))
    status = Column(String(50))   # active / past_due / canceled / unpaid
    current_period_start = Column(DateTime)
    current_period_end = Column(DateTime)
    cancel_at_period_end = Column(Boolean, default=False)
    raw = Column(JSON)            # store raw stripe json
    user = relationship("User")

class Invoice(Base):
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    stripe_invoice_id = Column(String(255), unique=True, index=True)
    amount_due = Column(Numeric(12,2))
    currency = Column(String(10))
    paid = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)
    raw = Column(JSON)

class StripeEvent(Base):
    __tablename__ = "stripe_events"
    id = Column(Integer, primary_key=True)
    stripe_event_id = Column(String(255), unique=True, index=True)
    type = Column(String(255))
    payload = Column(JSON)
    received_at = Column(DateTime, default=now)
    processed = Column(Boolean, default=False)
