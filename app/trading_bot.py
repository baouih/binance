import logging
import threading
import time
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('trading_bot')

class TradingBot:
    def __init__(self, binance_api, data_processor, strategy, symbol='BTCUSDT', 
                 interval='1h', test_mode=True, leverage=1, max_positions=1):
        """
        Initialize the trading bot.
        
        Args:
            binance_api: BinanceAPI instance
            data_processor: DataProcessor instance
            strategy: Trading strategy to use
            symbol (str): Trading pair
            interval (str): Candlestick interval
            test_mode (bool): Whether to run in test mode (no real trades)
            leverage (int): Leverage to use
            max_positions (int): Maximum number of open positions
        """
        self.binance_api = binance_api
        self.data_processor = data_processor
        self.strategy = strategy
        self.symbol = symbol
        self.interval = interval
        self.test_mode = test_mode
        self.leverage = leverage
        self.max_positions = max_positions
        
        # Trading state
        self.is_running = False
        self.thread = None
        self.positions = []
        self.trade_history = []
        self.last_check_time = None
        
        # Performance metrics
        self.metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'profit_pct': 0.0,
            'win_rate': 0.0,
            'max_drawdown': 0.0
        }
        
        logger.info(f"Trading bot initialized for {symbol} on {interval} interval")
        
    def start(self, check_interval=60):
        """
        Start the trading bot.
        
        Args:
            check_interval (int): Interval in seconds between checks
            
        Returns:
            bool: Success or failure
        """
        if self.is_running:
            logger.warning("Trading bot is already running")
            return False
            
        self.is_running = True
        self.last_check_time = datetime.now()
        
        # Start the bot in a separate thread
        self.thread = threading.Thread(target=self._run, args=(check_interval,))
        self.thread.daemon = True
        self.thread.start()
        
        logger.info(f"Trading bot started with {check_interval}s check interval")
        return True
        
    def stop(self):
        """
        Stop the trading bot.
        
        Returns:
            bool: Success or failure
        """
        if not self.is_running:
            logger.warning("Trading bot is not running")
            return False
            
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None
            
        logger.info("Trading bot stopped")
        return True
        
    def _run(self, check_interval):
        """
        Main bot loop.
        
        Args:
            check_interval (int): Interval in seconds between checks
        """
        while self.is_running:
            try:
                self._check_and_trade()
            except Exception as e:
                logger.error(f"Error in trading bot loop: {str(e)}")
                
            # Sleep until next check
            time.sleep(check_interval)
            
    def _check_and_trade(self):
        """Check market conditions and execute trades if signals are generated."""
        # Get the latest market data
        df = self.data_processor.get_historical_data(
            symbol=self.symbol,
            interval=self.interval,
            lookback_days=10
        )
        
        if df is None or df.empty:
            logger.warning("No data available for trading decision")
            return
            
        # Generate signal
        signal = self.strategy.generate_signal(df)
        
        # Log the trading decision
        logger.info(f"Trading signal for {self.symbol}: {signal}")
        
        # Execute the signal
        if signal == 1:  # Buy signal
            self._open_position('BUY')
        elif signal == -1:  # Sell signal
            self._open_position('SELL')
            
        # Update positions
        self._update_positions(df)
        
        # Update last check time
        self.last_check_time = datetime.now()
        
    def _open_position(self, side):
        """
        Open a new trading position.
        
        Args:
            side (str): BUY or SELL
        """
        # Check if we can open more positions
        if len(self.positions) >= self.max_positions:
            logger.info(f"Maximum positions ({self.max_positions}) already open")
            return
            
        # Get account info
        account = self.binance_api.get_account_info()
        if not account:
            logger.warning("Could not get account info")
            return
            
        # Calculate position size (10% of available balance)
        available_balance = float(account.get('availableBalance', 0))
        position_size = available_balance * 0.1
        
        # Get current price
        latest_price = self._get_current_price()
        if not latest_price:
            logger.warning("Could not get current price")
            return
            
        # Calculate quantity
        quantity = position_size / latest_price
        
        # Round quantity to appropriate precision
        quantity = round(quantity, 3)  # Assuming 3 decimal places for quantity
        
        if quantity <= 0:
            logger.warning(f"Invalid quantity: {quantity}")
            return
            
        # Execute the order
        if self.test_mode:
            # In test mode, just simulate the order
            order_id = int(time.time() * 1000)
            status = 'FILLED'
            filled_qty = quantity
            filled_price = latest_price
            logger.info(f"TEST MODE: {side} order placed for {quantity} {self.symbol} at {latest_price}")
        else:
            # In live mode, place a real order
            order = self.binance_api.create_order(
                symbol=self.symbol,
                side=side,
                order_type='MARKET',
                quantity=quantity
            )
            
            if not order:
                logger.warning("Failed to place order")
                return
                
            order_id = order.get('orderId')
            status = order.get('status')
            filled_qty = float(order.get('executedQty', 0))
            filled_price = float(order.get('avgPrice', latest_price))
            
            logger.info(f"Order placed: {order_id}, Status: {status}, Qty: {filled_qty}, Price: {filled_price}")
            
        # Add to positions if order was filled
        if status == 'FILLED' and filled_qty > 0:
            position = {
                'id': order_id,
                'symbol': self.symbol,
                'side': side,
                'quantity': filled_qty,
                'entry_price': filled_price,
                'entry_time': datetime.now(),
                'current_price': filled_price,
                'current_pnl': 0.0,
                'exit_price': None,
                'exit_time': None,
                'status': 'OPEN'
            }
            
            self.positions.append(position)
            logger.info(f"Position opened: {position['id']}")
            
            # Update metrics
            self.metrics['total_trades'] += 1
            
    def _update_positions(self, dataframe):
        """
        Update open positions with current prices and check for closing conditions.
        
        Args:
            dataframe (pandas.DataFrame): Latest market data
        """
        if not self.positions:
            return
            
        # Get the latest price
        latest_price = dataframe['close'].iloc[-1]
        
        # Update each position
        for position in self.positions:
            if position['status'] != 'OPEN':
                continue
                
            # Update current price and P&L
            position['current_price'] = latest_price
            
            # Calculate P&L
            if position['side'] == 'BUY':
                position['current_pnl'] = (latest_price - position['entry_price']) / position['entry_price']
            else:  # SELL
                position['current_pnl'] = (position['entry_price'] - latest_price) / position['entry_price']
                
            # Check for closing conditions
            # For simplicity, using opposite signals to close positions
            signal = self.strategy.generate_signal(dataframe)
            
            should_close = False
            if position['side'] == 'BUY' and signal == -1:
                should_close = True
            elif position['side'] == 'SELL' and signal == 1:
                should_close = True
                
            # Also close if P&L exceeds thresholds
            take_profit = 0.05  # 5% profit target
            stop_loss = -0.03  # 3% stop loss
            
            if position['current_pnl'] >= take_profit or position['current_pnl'] <= stop_loss:
                should_close = True
                
            if should_close:
                self._close_position(position, latest_price)
                
    def _close_position(self, position, price):
        """
        Close an open position.
        
        Args:
            position (dict): Position to close
            price (float): Closing price
        """
        if position['status'] != 'OPEN':
            logger.warning(f"Position {position['id']} is not open")
            return
            
        # Determine the side for closing (opposite of opening side)
        close_side = 'SELL' if position['side'] == 'BUY' else 'BUY'
        
        if self.test_mode:
            # In test mode, just simulate the closing
            logger.info(f"TEST MODE: Closing position {position['id']} at {price}")
            status = 'FILLED'
        else:
            # In live mode, place a real order to close
            order = self.binance_api.create_order(
                symbol=position['symbol'],
                side=close_side,
                order_type='MARKET',
                quantity=position['quantity']
            )
            
            if not order:
                logger.warning(f"Failed to close position {position['id']}")
                return
                
            status = order.get('status')
            
            logger.info(f"Closing order placed: {order.get('orderId')}, Status: {status}")
            
        # Update position if successfully closed
        if status == 'FILLED':
            position['exit_price'] = price
            position['exit_time'] = datetime.now()
            position['status'] = 'CLOSED'
            
            # Calculate final P&L
            if position['side'] == 'BUY':
                position['final_pnl'] = (price - position['entry_price']) / position['entry_price']
            else:  # SELL
                position['final_pnl'] = (position['entry_price'] - price) / position['entry_price']
                
            # Add to trade history
            self.trade_history.append(position.copy())
            
            # Update metrics
            if position['final_pnl'] > 0:
                self.metrics['winning_trades'] += 1
            else:
                self.metrics['losing_trades'] += 1
                
            self.metrics['profit_pct'] += position['final_pnl']
            
            if self.metrics['total_trades'] > 0:
                self.metrics['win_rate'] = self.metrics['winning_trades'] / self.metrics['total_trades']
                
            logger.info(f"Position closed: {position['id']}, P&L: {position['final_pnl']:.2%}")
            
    def _get_current_price(self):
        """Get the current price of the trading pair."""
        # Use the order book to get the current price
        order_book = self.binance_api.get_order_book(self.symbol, limit=5)
        
        if not order_book or not order_book.get('bids') or not order_book.get('asks'):
            return None
            
        # Use the mid price between best bid and ask
        best_bid = float(order_book['bids'][0][0])
        best_ask = float(order_book['asks'][0][0])
        
        return (best_bid + best_ask) / 2
        
    def get_current_metrics(self):
        """
        Get current performance metrics.
        
        Returns:
            dict: Performance metrics
        """
        # Calculate additional metrics
        metrics = self.metrics.copy()
        
        # Add current positions info
        metrics['open_positions'] = len([p for p in self.positions if p['status'] == 'OPEN'])
        metrics['closed_positions'] = len(self.trade_history)
        
        # Calculate current P&L for open positions
        open_pnl = sum(p['current_pnl'] for p in self.positions if p['status'] == 'OPEN')
        metrics['open_pnl'] = open_pnl
        
        # Calculate drawdown
        if self.trade_history:
            pnls = [trade['final_pnl'] for trade in self.trade_history]
            cumulative_pnl = np.cumsum(pnls)
            
            peak = np.maximum.accumulate(cumulative_pnl)
            drawdown = (peak - cumulative_pnl) / (peak + 1e-10)  # Avoid division by zero
            max_drawdown = np.max(drawdown)
            
            metrics['max_drawdown'] = max_drawdown
            
        # Calculate the Sharpe ratio if we have enough trades
        if len(self.trade_history) > 10:
            pnls = [trade['final_pnl'] for trade in self.trade_history]
            mean_return = np.mean(pnls)
            std_return = np.std(pnls) + 1e-10  # Avoid division by zero
            
            # Annualized Sharpe ratio (assuming daily trades)
            sharpe = mean_return / std_return * np.sqrt(252)
            metrics['sharpe_ratio'] = sharpe
            
        return metrics
        
    def backtest(self, dataframe, initial_balance=10000.0):
        """
        Backtest the strategy on historical data.
        
        Args:
            dataframe (pandas.DataFrame): Historical data with indicators
            initial_balance (float): Initial balance for backtesting
            
        Returns:
            tuple: (backtest_results, performance_metrics)
        """
        if dataframe is None or dataframe.empty:
            logger.warning("No data for backtesting")
            return None, {}
            
        # Make a copy to avoid modifying the original
        df = dataframe.copy()
        
        # Initialize backtest state
        balance = initial_balance
        position = None
        trades = []
        
        # Add signal column
        signals = []
        for i in range(len(df)):
            # Use the strategy to generate signals
            signal = self.strategy.generate_signal(df.iloc[:i+1])
            signals.append(signal)
            
        df['signal'] = signals
        
        # Simulate trading
        for i in range(1, len(df)):
            timestamp = df.index[i]
            price = df['close'].iloc[i]
            signal = df['signal'].iloc[i]
            
            # Check if we need to close a position
            if position is not None:
                # Calculate current P&L
                if position['side'] == 'BUY':
                    pnl_pct = (price - position['entry_price']) / position['entry_price']
                else:  # SELL
                    pnl_pct = (position['entry_price'] - price) / position['entry_price']
                    
                # Close position if opposite signal or take profit/stop loss hit
                take_profit = 0.05  # 5% profit target
                stop_loss = -0.03  # 3% stop loss
                
                should_close = False
                if (position['side'] == 'BUY' and signal == -1) or \
                   (position['side'] == 'SELL' and signal == 1) or \
                   pnl_pct >= take_profit or pnl_pct <= stop_loss:
                    should_close = True
                    
                if should_close:
                    # Close the position
                    position['exit_price'] = price
                    position['exit_time'] = timestamp
                    position['pnl_pct'] = pnl_pct
                    position['pnl_amount'] = position['amount'] * pnl_pct
                    
                    # Update balance
                    balance += position['amount'] + position['pnl_amount']
                    
                    # Add to trades
                    trades.append(position)
                    position = None
                    
            # Check if we need to open a new position
            if position is None and (signal == 1 or signal == -1):
                # Determine position side
                side = 'BUY' if signal == 1 else 'SELL'
                
                # Calculate position size (10% of balance)
                amount = balance * 0.1
                
                if amount > 0:
                    # Open a new position
                    position = {
                        'entry_time': timestamp,
                        'entry_price': price,
                        'side': side,
                        'amount': amount,
                        'exit_price': None,
                        'exit_time': None,
                        'pnl_pct': 0.0,
                        'pnl_amount': 0.0
                    }
                    
                    # Reduce balance
                    balance -= amount
                    
        # Close any remaining position at the end
        if position is not None:
            price = df['close'].iloc[-1]
            timestamp = df.index[-1]
            
            # Calculate final P&L
            if position['side'] == 'BUY':
                pnl_pct = (price - position['entry_price']) / position['entry_price']
            else:  # SELL
                pnl_pct = (position['entry_price'] - price) / position['entry_price']
                
            position['exit_price'] = price
            position['exit_time'] = timestamp
            position['pnl_pct'] = pnl_pct
            position['pnl_amount'] = position['amount'] * pnl_pct
            
            # Update balance
            balance += position['amount'] + position['pnl_amount']
            
            # Add to trades
            trades.append(position)
            
        # Calculate performance metrics
        metrics = self._calculate_backtest_metrics(trades, initial_balance, balance)
        
        # Create results dataframe with equity curve
        results = df.copy()
        results['equity'] = initial_balance
        
        for trade in trades:
            entry_idx = results.index.get_indexer([trade['entry_time']])[0]
            exit_idx = results.index.get_indexer([trade['exit_time']])[0]
            
            # Calculate equity at each step during the trade
            for i in range(entry_idx + 1, exit_idx + 1):
                price_diff_pct = 0
                if trade['side'] == 'BUY':
                    price_diff_pct = (results['close'].iloc[i] - trade['entry_price']) / trade['entry_price']
                else:  # SELL
                    price_diff_pct = (trade['entry_price'] - results['close'].iloc[i]) / trade['entry_price']
                    
                # Calculate equity impact of this trade
                trade_pnl = trade['amount'] * price_diff_pct
                results['equity'].iloc[i] += trade_pnl
                
        # Add cumulative returns
        results['returns'] = results['equity'] / initial_balance - 1
        
        return results, metrics, trades
        
    def _calculate_backtest_metrics(self, trades, initial_balance, final_balance):
        """
        Calculate performance metrics from backtest results.
        
        Args:
            trades (list): List of trades
            initial_balance (float): Initial balance
            final_balance (float): Final balance
            
        Returns:
            dict: Performance metrics
        """
        if not trades:
            return {
                'total_trades': 0,
                'profit_pct': 0.0,
                'profit_amount': 0.0,
            }
            
        # Basic metrics
        total_trades = len(trades)
        profit_amount = final_balance - initial_balance
        profit_pct = profit_amount / initial_balance
        
        # Win/loss metrics
        winning_trades = [t for t in trades if t['pnl_amount'] > 0]
        losing_trades = [t for t in trades if t['pnl_amount'] <= 0]
        
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        # Average trade metrics
        avg_win = np.mean([t['pnl_pct'] for t in winning_trades]) if winning_trades else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losing_trades]) if losing_trades else 0
        
        # Risk metrics
        if winning_trades and losing_trades:
            profit_factor = abs(sum(t['pnl_amount'] for t in winning_trades) / 
                            sum(t['pnl_amount'] for t in losing_trades)) if sum(t['pnl_amount'] for t in losing_trades) != 0 else float('inf')
        else:
            profit_factor = 0 if not winning_trades else float('inf')
            
        # Calculate drawdown
        balances = [initial_balance]
        for trade in trades:
            balances.append(balances[-1] + trade['pnl_amount'])
            
        cumulative_returns = np.array(balances) / initial_balance - 1
        peak = np.maximum.accumulate(cumulative_returns)
        drawdown = peak - cumulative_returns
        max_drawdown = np.max(drawdown) if len(drawdown) > 0 else 0
        
        # Calculate Sharpe ratio
        returns = [t['pnl_pct'] for t in trades]
        daily_returns = []
        
        # Group trades by day and calculate daily returns
        trades_by_day = {}
        for trade in trades:
            day = trade['exit_time'].date()
            if day not in trades_by_day:
                trades_by_day[day] = []
            trades_by_day[day].append(trade)
            
        for day, day_trades in trades_by_day.items():
            daily_return = sum(t['pnl_pct'] for t in day_trades)
            daily_returns.append(daily_return)
            
        sharpe = 0
        if daily_returns:
            mean_return = np.mean(daily_returns)
            std_return = np.std(daily_returns)
            if std_return > 0:
                # Annualized Sharpe ratio
                sharpe = mean_return / std_return * np.sqrt(252)
                
        # Return metrics
        return {
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'largest_win': max([t['pnl_pct'] for t in trades]) if trades else 0,
            'largest_loss': min([t['pnl_pct'] for t in trades]) if trades else 0,
            'profit_pct': profit_pct,
            'profit_amount': profit_amount,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe,
            'final_balance': final_balance
        }
