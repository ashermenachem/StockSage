from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from utils.database import Base

class AssetType(enum.Enum):
    STOCK = "stock"
    CRYPTO = "crypto"
    OPTION = "option"
    FUTURE = "future"

class OrderType(enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"

class OrderSide(enum.Enum):
    BUY = "buy"
    SELL = "sell"
    SHORT = "short"

class PaperTradingAccount(Base):
    __tablename__ = "paper_trading_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    balance = Column(Float, default=100000.0)  # Default $100,000 paper money
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="paper_accounts")
    positions = relationship("PaperPosition", back_populates="account")
    orders = relationship("PaperOrder", back_populates="account")

class PaperPosition(Base):
    __tablename__ = "paper_positions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("paper_trading_accounts.id"))
    symbol = Column(String)
    asset_type = Column(Enum(AssetType))
    quantity = Column(Float)
    average_price = Column(Float)
    current_price = Column(Float)
    unrealized_pnl = Column(Float)
    is_short = Column(Boolean, default=False)

    # For options
    strike_price = Column(Float, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    option_type = Column(String, nullable=True)  # 'call' or 'put'

    # Relationships
    account = relationship("PaperTradingAccount", back_populates="positions")

class PaperOrder(Base):
    __tablename__ = "paper_orders"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("paper_trading_accounts.id"))
    symbol = Column(String)
    asset_type = Column(Enum(AssetType))
    order_type = Column(Enum(OrderType))
    order_side = Column(Enum(OrderSide))
    quantity = Column(Float)
    price = Column(Float)
    status = Column(String)  # 'pending', 'filled', 'cancelled'
    created_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime, nullable=True)

    # For options/futures
    strike_price = Column(Float, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    contract_type = Column(String, nullable=True)  # 'call', 'put', or future contract code

    # Relationships
    account = relationship("PaperTradingAccount", back_populates="orders")