from sqlalchemy.orm import Session
from models.paper_trading import PaperTradingAccount, PaperPosition, PaperOrder, AssetType, OrderType, OrderSide
from datetime import datetime
from typing import List, Optional
import yfinance as yf

class PaperTradingManager:
    def __init__(self, db: Session):
        self.db = db

    def create_paper_account(self, user_id: int, initial_balance: float = 100000.0) -> PaperTradingAccount:
        """Create a new paper trading account"""
        account = PaperTradingAccount(user_id=user_id, balance=initial_balance)
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)
        return account

    def get_account_balance(self, account_id: int) -> float:
        """Get current account balance"""
        account = self.db.query(PaperTradingAccount).filter(PaperTradingAccount.id == account_id).first()
        return account.balance if account else 0.0

    def place_order(self, account_id: int, symbol: str, order_side: OrderSide, 
                   quantity: float, price: float, asset_type: AssetType = AssetType.STOCK,
                   order_type: OrderType = OrderType.MARKET, **kwargs) -> PaperOrder:
        """Place a new paper trading order"""
        account = self.db.query(PaperTradingAccount).filter(PaperTradingAccount.id == account_id).first()
        
        # Calculate order cost
        order_cost = quantity * price
        
        # Verify sufficient funds for buy orders
        if order_side in [OrderSide.BUY, OrderSide.SHORT] and order_cost > account.balance:
            raise ValueError("Insufficient funds for order")
        
        # Create the order
        order = PaperOrder(
            account_id=account_id,
            symbol=symbol,
            asset_type=asset_type,
            order_type=order_type,
            order_side=order_side,
            quantity=quantity,
            price=price,
            status='filled',  # For simplicity, we'll auto-fill market orders
            filled_at=datetime.utcnow(),
            **kwargs
        )
        
        # Update account balance
        if order_side == OrderSide.BUY:
            account.balance -= order_cost
        elif order_side == OrderSide.SELL:
            account.balance += order_cost
        
        # Create or update position
        self._update_position(account_id, symbol, quantity, price, order_side, asset_type, **kwargs)
        
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def _update_position(self, account_id: int, symbol: str, quantity: float, 
                        price: float, order_side: OrderSide, asset_type: AssetType, **kwargs):
        """Update position after order execution"""
        position = self.db.query(PaperPosition).filter(
            PaperPosition.account_id == account_id,
            PaperPosition.symbol == symbol,
            PaperPosition.asset_type == asset_type
        ).first()
        
        if position:
            if order_side == OrderSide.BUY:
                new_quantity = position.quantity + quantity
                new_cost = (position.average_price * position.quantity) + (price * quantity)
                position.average_price = new_cost / new_quantity
                position.quantity = new_quantity
            elif order_side == OrderSide.SELL:
                position.quantity -= quantity
                if position.quantity <= 0:
                    self.db.delete(position)
        else:
            position = PaperPosition(
                account_id=account_id,
                symbol=symbol,
                asset_type=asset_type,
                quantity=quantity,
                average_price=price,
                current_price=price,
                is_short=order_side == OrderSide.SHORT,
                **kwargs
            )
            self.db.add(position)
        
        self.db.commit()

    def get_positions(self, account_id: int) -> List[PaperPosition]:
        """Get all positions for an account"""
        return self.db.query(PaperPosition).filter(PaperPosition.account_id == account_id).all()

    def update_positions_value(self, account_id: int):
        """Update current prices and P&L for all positions"""
        positions = self.get_positions(account_id)
        for position in positions:
            if position.asset_type == AssetType.STOCK:
                ticker = yf.Ticker(position.symbol)
                current_price = ticker.history(period='1d')['Close'].iloc[-1]
                position.current_price = current_price
                position.unrealized_pnl = (current_price - position.average_price) * position.quantity
                if position.is_short:
                    position.unrealized_pnl *= -1
        self.db.commit()
