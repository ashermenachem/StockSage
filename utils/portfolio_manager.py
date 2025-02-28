from sqlalchemy.orm import Session
from models.portfolio import User, Portfolio, Position, Transaction, WatchlistItem
from datetime import datetime
from typing import List, Optional
import numpy as np

class PortfolioManager:
    def __init__(self, db: Session):
        self.db = db

    def create_user(self, username: str, email: str) -> User:
        user = User(username=username, email=email)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_portfolio(self, user_id: int, name: str) -> Portfolio:
        portfolio = Portfolio(user_id=user_id, name=name)
        self.db.add(portfolio)
        self.db.commit()
        self.db.refresh(portfolio)
        return portfolio

    def add_position(self, portfolio_id: int, symbol: str, shares: float, price: float) -> Position:
        # Convert numpy types to Python native types
        shares = float(shares) if isinstance(shares, np.floating) else shares
        price = float(price) if isinstance(price, np.floating) else price

        position = Position(
            portfolio_id=portfolio_id,
            symbol=symbol,
            shares=shares,
            average_price=price
        )
        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)

        # Record the transaction
        transaction = Transaction(
            position_id=position.id,
            type="BUY",
            shares=shares,
            price=price
        )
        self.db.add(transaction)
        self.db.commit()

        return position

    def update_position(self, position_id: int, shares_change: float, price: float):
        # Convert numpy types to Python native types
        shares_change = float(shares_change) if isinstance(shares_change, np.floating) else shares_change
        price = float(price) if isinstance(price, np.floating) else price

        position = self.db.query(Position).filter(Position.id == position_id).first()
        if position:
            transaction_type = "BUY" if shares_change > 0 else "SELL"

            # Update position
            position.shares += shares_change
            new_total = (position.shares * position.average_price) + (shares_change * price)
            position.average_price = new_total / position.shares if position.shares > 0 else 0
            position.last_updated = datetime.utcnow()

            # Record transaction
            transaction = Transaction(
                position_id=position.id,
                type=transaction_type,
                shares=abs(shares_change),
                price=price
            )
            self.db.add(transaction)
            self.db.commit()

    def get_portfolio_value(self, portfolio_id: int, current_prices: dict) -> float:
        positions = self.db.query(Position).filter(Position.portfolio_id == portfolio_id).all()
        total_value = 0
        for position in positions:
            if position.symbol in current_prices:
                total_value += position.shares * current_prices[position.symbol]
        return total_value

    def add_to_watchlist(self, user_id: int, symbol: str, price_alert: Optional[float] = None) -> WatchlistItem:
        # Convert numpy types to Python native types
        price_alert = float(price_alert) if isinstance(price_alert, np.floating) else price_alert

        item = WatchlistItem(user_id=user_id, symbol=symbol, price_alert=price_alert)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_watchlist(self, user_id: int) -> List[WatchlistItem]:
        return self.db.query(WatchlistItem).filter(WatchlistItem.user_id == user_id).all()