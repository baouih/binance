"""
Script kiểm tra module position_sizing.py

Script này kiểm tra độc lập các lớp và phương thức trong module position_sizing.py:
1. BasePositionSizer - Tính toán kích thước vị thế cơ bản
2. DynamicPositionSizer - Điều chỉnh kích thước theo biến động thị trường
3. KellyCriterionSizer - Tối ưu kích thước theo Kelly Criterion
4. AntiMartingaleSizer - Tăng kích thước sau thắng, giảm sau thua
5. PortfolioSizer - Quản lý vốn danh mục với tương quan

Các kiểm tra bao gồm xác minh giá trị đầu ra và kiểm tra xử lý lỗi.
"""

import os
import sys
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_position_sizing")

# Create necessary directories
os.makedirs('../test_results', exist_ok=True)

# Try to import the module
try:
    from position_sizing import (
        BasePositionSizer, 
        DynamicPositionSizer, 
        KellyCriterionSizer, 
        AntiMartingaleSizer, 
        PortfolioSizer,
        create_position_sizer
    )
    HAS_MODULE = True
except ImportError as e:
    logger.warning(f"Could not import position_sizing module: {e}")
    logger.warning("Using mock implementations for testing")
    HAS_MODULE = False
    
    # Create mock implementations for testing
    class BasePositionSizer:
        def __init__(self, account_balance, max_risk_pct=2.0, leverage=1, min_position_size=0.0):
            self.account_balance = account_balance
            self.max_risk_pct = max_risk_pct
            self.leverage = leverage
            self.min_position_size = min_position_size
            
        def calculate_position_size(self, entry_price, stop_loss_price, **kwargs):
            risk_per_unit = abs(entry_price - stop_loss_price) / entry_price
            risk_amount = self.account_balance * (self.max_risk_pct / 100)
            position_size = risk_amount / (entry_price * risk_per_unit)
            position_size *= self.leverage
            return max(self.min_position_size, position_size), self.max_risk_pct
            
        def update_account_balance(self, new_balance):
            self.account_balance = max(0.0, new_balance)
    
    class DynamicPositionSizer(BasePositionSizer):
        def __init__(self, account_balance, max_risk_pct=2.0, leverage=1,
                   volatility_factor=1.0, confidence_factor=1.0, min_position_size=0.0):
            super().__init__(account_balance, max_risk_pct, leverage, min_position_size)
            self.volatility_factor = volatility_factor
            self.confidence_factor = confidence_factor
            
        def calculate_position_size(self, entry_price, stop_loss_price, 
                                  volatility=None, signal_confidence=None, **kwargs):
            base_size, base_risk = super().calculate_position_size(entry_price, stop_loss_price)
            
            # Apply modifiers if provided
            volatility_multiplier = 1.0
            confidence_multiplier = 1.0
            
            if volatility is not None:
                volatility = max(0.0, min(1.0, volatility))
                volatility_multiplier = 1.0 / (1.0 + volatility * self.volatility_factor)
                
            if signal_confidence is not None:
                signal_confidence = max(0.0, min(1.0, signal_confidence))
                confidence_multiplier = signal_confidence * self.confidence_factor
                
            adjusted_size = base_size * volatility_multiplier * confidence_multiplier
            return max(self.min_position_size, adjusted_size), base_risk
    
    class KellyCriterionSizer(BasePositionSizer):
        def __init__(self, account_balance, win_rate=0.5, avg_win_loss_ratio=1.0, 
                   max_risk_pct=5.0, kelly_fraction=1.0, leverage=1, min_position_size=0.0):
            super().__init__(account_balance, max_risk_pct, leverage, min_position_size)
            self.win_rate = win_rate
            self.avg_win_loss_ratio = avg_win_loss_ratio
            self.kelly_fraction = kelly_fraction
            
        def calculate_position_size(self, entry_price, stop_loss_price, take_profit_price=None, **kwargs):
            if take_profit_price is not None:
                if entry_price > stop_loss_price:  # Long
                    win_amount = take_profit_price - entry_price
                    loss_amount = entry_price - stop_loss_price
                else:  # Short
                    win_amount = entry_price - take_profit_price
                    loss_amount = stop_loss_price - entry_price
                    
                current_rr_ratio = win_amount / loss_amount if loss_amount > 0 else self.avg_win_loss_ratio
            else:
                current_rr_ratio = self.avg_win_loss_ratio
                
            kelly_pct = (self.win_rate * (current_rr_ratio + 1) - 1) / current_rr_ratio
            kelly_pct = max(0, kelly_pct * self.kelly_fraction)
            kelly_pct = min(kelly_pct, self.max_risk_pct / 100)
            
            position_value = self.account_balance * kelly_pct
            position_size = position_value / entry_price * self.leverage
            
            return max(self.min_position_size, position_size), kelly_pct * 100
    
    class AntiMartingaleSizer(BasePositionSizer):
        def __init__(self, account_balance, max_risk_pct=2.0, base_unit_pct=1.0, 
                   increase_factor=1.5, max_units=4, leverage=1, min_position_size=0.0):
            super().__init__(account_balance, max_risk_pct, leverage, min_position_size)
            self.base_unit_pct = base_unit_pct
            self.increase_factor = increase_factor
            self.max_units = max_units
            self.current_units = 1
            self.consecutive_wins = 0
            
        def calculate_position_size(self, entry_price, stop_loss_price, **kwargs):
            base_sizer = BasePositionSizer(
                self.account_balance, self.base_unit_pct, self.leverage, self.min_position_size
            )
            base_size, base_risk = base_sizer.calculate_position_size(entry_price, stop_loss_price)
            
            current_units = min(self.current_units, self.max_units)
            position_size = base_size * current_units
            
            return position_size, base_risk * current_units
            
        def update_after_trade(self, is_win):
            if is_win:
                self.consecutive_wins += 1
                self.current_units = self.current_units * self.increase_factor
            else:
                self.consecutive_wins = 0
                self.current_units = 1
    
    class PortfolioSizer:
        def __init__(self, account_balance, max_portfolio_risk=5.0, max_symbol_risk=2.0,
                   max_correlated_exposure=3.0, correlation_threshold=0.7):
            self.account_balance = account_balance
            self.max_portfolio_risk = max_portfolio_risk
            self.max_symbol_risk = max_symbol_risk
            self.max_correlated_exposure = max_correlated_exposure
            self.correlation_threshold = correlation_threshold
            self.current_positions = {}
            
        def calculate_position_allocations(self, symbols, signals, correlation_matrix):
            allocations = {}
            
            for symbol in symbols:
                if symbol not in signals or signals[symbol].get('signal') not in ['buy', 'sell']:
                    continue
                    
                signal = signals[symbol]
                entry_price = signal.get('entry_price', 0)
                stop_loss = signal.get('stop_loss', 0)
                signal_strength = signal.get('strength', 0.5)
                
                if entry_price <= 0 or stop_loss <= 0:
                    continue
                    
                symbol_risk_pct = self.max_symbol_risk * signal_strength
                risk_amount = self.account_balance * (symbol_risk_pct / 100)
                
                if signal['signal'] == 'buy':  # Long
                    risk_per_unit = (entry_price - stop_loss) / entry_price
                else:  # Short
                    risk_per_unit = (stop_loss - entry_price) / entry_price
                    
                risk_per_unit = max(risk_per_unit, 0.001)
                position_size = risk_amount / (entry_price * risk_per_unit)
                
                allocations[symbol] = {
                    'position_size': position_size,
                    'position_value': position_size * entry_price,
                    'risk_amount': risk_amount,
                    'risk_pct': symbol_risk_pct,
                    'side': signal['signal']
                }
                
            return allocations
            
        def update_account_balance(self, new_balance):
            self.account_balance = max(0.0, new_balance)
    
    def create_position_sizer(sizer_type, account_balance, **kwargs):
        if sizer_type.lower() == 'basic':
            return BasePositionSizer(account_balance, **kwargs)
        elif sizer_type.lower() == 'dynamic':
            return DynamicPositionSizer(account_balance, **kwargs)
        elif sizer_type.lower() == 'kelly':
            return KellyCriterionSizer(account_balance, **kwargs)
        elif sizer_type.lower() == 'antimartingale':
            return AntiMartingaleSizer(account_balance, **kwargs)
        elif sizer_type.lower() == 'portfolio':
            return PortfolioSizer(account_balance, **kwargs)
        else:
            return BasePositionSizer(account_balance, **kwargs)

def test_base_position_sizer():
    """Test the BasePositionSizer class"""
    print("\n=== Testing BasePositionSizer ===")
    
    # Initialize with default parameters
    account_balance = 10000.0
    sizer = BasePositionSizer(account_balance)
    
    # Test case 1: Normal calculation
    entry_price = 40000.0
    stop_loss_price = 39000.0
    size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
    expected_size = (account_balance * 0.02) / (40000 * (1000 / 40000))
    print(f"Test case 1: entry={entry_price}, stop={stop_loss_price}")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk=2.00%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    assert abs(risk - 2.0) < 0.01, f"Expected risk 2.0%, got {risk}%"
    
    # Test case 2: With leverage
    leverage = 5
    sizer = BasePositionSizer(account_balance, leverage=leverage)
    size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
    expected_size = (account_balance * 0.02) / (40000 * (1000 / 40000)) * leverage
    print(f"\nTest case 2: With leverage={leverage}")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk=2.00%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    
    # Test case 3: Short position
    entry_price = 39000.0
    stop_loss_price = 40000.0
    size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
    expected_size = (account_balance * 0.02) / (39000 * (1000 / 39000)) * leverage
    print(f"\nTest case 3: Short position")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk=2.00%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    
    # Test case 4: Higher risk percentage
    max_risk_pct = 5.0
    sizer = BasePositionSizer(account_balance, max_risk_pct=max_risk_pct, leverage=1)
    size, risk = sizer.calculate_position_size(40000.0, 39000.0)
    expected_size = (account_balance * 0.05) / (40000 * (1000 / 40000))
    print(f"\nTest case 4: Higher risk={max_risk_pct}%")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={max_risk_pct:.2f}%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    assert abs(risk - max_risk_pct) < 0.01, f"Expected risk {max_risk_pct}%, got {risk}%"
    
    # Test case 5: Minimum position size
    min_size = 0.01
    sizer = BasePositionSizer(100.0, max_risk_pct=2.0, min_position_size=min_size)
    size, risk = sizer.calculate_position_size(40000.0, 39000.0)
    print(f"\nTest case 5: Minimum position size={min_size}")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={min_size:.6f} (min size applied)")
    assert size == min_size, f"Expected size {min_size}, got {size}"
    
    # Test case 6: Edge cases
    print("\nTest case 6: Edge cases")
    try:
        size, risk = sizer.calculate_position_size(0, 39000.0)
        print("  Zero entry price: No exception raised (potential issue)")
    except Exception as e:
        print(f"  Zero entry price: Exception correctly raised: {type(e).__name__}")
        
    try:
        size, risk = sizer.calculate_position_size(40000.0, 40000.0)
        print("  Equal entry/stop: No exception raised (potential issue)")
    except Exception as e:
        print(f"  Equal entry/stop: Exception correctly raised: {type(e).__name__}")
        
    # Test case 7: Update account balance
    print("\nTest case 7: Update account balance")
    initial_balance = 10000.0
    sizer = BasePositionSizer(initial_balance)
    new_balance = 12000.0
    sizer.update_account_balance(new_balance)
    assert sizer.account_balance == new_balance, f"Expected balance {new_balance}, got {sizer.account_balance}"
    print(f"  Balance updated: {sizer.account_balance}")
    
    # Negative balance test
    sizer.update_account_balance(-5000.0)
    assert sizer.account_balance == 0.0, f"Expected balance 0.0 (floor), got {sizer.account_balance}"
    print(f"  Negative balance handled: {sizer.account_balance}")
    
    print("\nBasePositionSizer tests completed successfully!")
    return True

def test_dynamic_position_sizer():
    """Test the DynamicPositionSizer class"""
    print("\n=== Testing DynamicPositionSizer ===")
    
    # Initialize with default parameters
    account_balance = 10000.0
    sizer = DynamicPositionSizer(account_balance, volatility_factor=1.0, confidence_factor=1.0)
    
    # Test case 1: No modifiers (should be the same as base sizer)
    entry_price = 40000.0
    stop_loss_price = 39000.0
    size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
    base_sizer = BasePositionSizer(account_balance)
    base_size, base_risk = base_sizer.calculate_position_size(entry_price, stop_loss_price)
    print(f"Test case 1: No modifiers")
    print(f"  Dynamic sizer: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Base sizer:    size={base_size:.6f}, risk={base_risk:.2f}%")
    assert abs(size - base_size) < 0.001, f"Expected size {base_size}, got {size}"
    assert abs(risk - base_risk) < 0.01, f"Expected risk {base_risk}%, got {risk}%"
    
    # Test case 2: High volatility, high confidence
    volatility = 0.8  # 80% volatility
    signal_confidence = 0.9  # 90% confidence
    size, risk = sizer.calculate_position_size(
        entry_price, stop_loss_price, volatility=volatility, signal_confidence=signal_confidence
    )
    volatility_multiplier = 1.0 / (1.0 + volatility * sizer.volatility_factor)
    confidence_multiplier = signal_confidence * sizer.confidence_factor
    expected_size = base_size * volatility_multiplier * confidence_multiplier
    
    print(f"\nTest case 2: volatility={volatility}, confidence={signal_confidence}")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={base_risk:.2f}%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    
    # Test case 3: Low volatility, low confidence
    volatility = 0.2  # 20% volatility
    signal_confidence = 0.4  # 40% confidence
    size, risk = sizer.calculate_position_size(
        entry_price, stop_loss_price, volatility=volatility, signal_confidence=signal_confidence
    )
    volatility_multiplier = 1.0 / (1.0 + volatility * sizer.volatility_factor)
    confidence_multiplier = signal_confidence * sizer.confidence_factor
    expected_size = base_size * volatility_multiplier * confidence_multiplier
    
    print(f"\nTest case 3: volatility={volatility}, confidence={signal_confidence}")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={base_risk:.2f}%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    
    # Test case 4: Only volatility provided
    volatility = 0.5  # 50% volatility
    size, risk = sizer.calculate_position_size(
        entry_price, stop_loss_price, volatility=volatility
    )
    volatility_multiplier = 1.0 / (1.0 + volatility * sizer.volatility_factor)
    expected_size = base_size * volatility_multiplier
    
    print(f"\nTest case 4: Only volatility={volatility}")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={base_risk:.2f}%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    
    # Test case 5: Only confidence provided
    signal_confidence = 0.6  # 60% confidence
    size, risk = sizer.calculate_position_size(
        entry_price, stop_loss_price, signal_confidence=signal_confidence
    )
    confidence_multiplier = signal_confidence * sizer.confidence_factor
    expected_size = base_size * confidence_multiplier
    
    print(f"\nTest case 5: Only confidence={signal_confidence}")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={base_risk:.2f}%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    
    # Test case 6: Higher volatility factor
    volatility_factor = 2.0
    sizer = DynamicPositionSizer(account_balance, volatility_factor=volatility_factor)
    volatility = 0.5
    size, risk = sizer.calculate_position_size(
        entry_price, stop_loss_price, volatility=volatility
    )
    volatility_multiplier = 1.0 / (1.0 + volatility * volatility_factor)
    expected_size = base_size * volatility_multiplier
    
    print(f"\nTest case 6: volatility_factor={volatility_factor}, volatility={volatility}")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={base_risk:.2f}%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    
    # Test case 7: Out of bounds values
    volatility = 1.5  # Above 1.0
    signal_confidence = -0.2  # Below 0.0
    size, risk = sizer.calculate_position_size(
        entry_price, stop_loss_price, volatility=volatility, signal_confidence=signal_confidence
    )
    # Should clamp to 1.0 and 0.0 respectively
    volatility_multiplier = 1.0 / (1.0 + 1.0 * volatility_factor)
    confidence_multiplier = 0.0 * sizer.confidence_factor
    expected_size = base_size * volatility_multiplier * confidence_multiplier
    
    print(f"\nTest case 7: Out of bounds values (vol={volatility}, conf={signal_confidence})")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    
    # Confidence = 0 should make the position size 0 or min_position_size
    assert abs(size) <= 0.000001, f"Expected size near 0, got {size}"
    
    print("\nDynamicPositionSizer tests completed successfully!")
    return True

def test_kelly_criterion_sizer():
    """Test the KellyCriterionSizer class"""
    print("\n=== Testing KellyCriterionSizer ===")
    
    # Initialize with default parameters
    account_balance = 10000.0
    win_rate = 0.6
    avg_win_loss_ratio = 2.0
    sizer = KellyCriterionSizer(account_balance, win_rate=win_rate, 
                              avg_win_loss_ratio=avg_win_loss_ratio)
    
    # Test case 1: Basic Kelly calculation
    entry_price = 40000.0
    stop_loss_price = 39000.0
    size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
    
    # Kelly formula: f* = (p*b - q)/b where p=win rate, q=1-p, b=win/loss ratio
    kelly_pct = (win_rate * avg_win_loss_ratio - (1 - win_rate)) / avg_win_loss_ratio
    expected_size = (account_balance * kelly_pct) / entry_price
    
    print(f"Test case 1: win_rate={win_rate}, ratio={avg_win_loss_ratio}")
    print(f"  Kelly formula: ({win_rate}*{avg_win_loss_ratio} - {1-win_rate})/{avg_win_loss_ratio} = {kelly_pct:.4f}")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={kelly_pct*100:.2f}%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    assert abs(risk - kelly_pct*100) < 0.01, f"Expected risk {kelly_pct*100}%, got {risk}%"
    
    # Test case 2: With take profit price
    take_profit_price = 42000.0
    size, risk = sizer.calculate_position_size(
        entry_price, stop_loss_price, take_profit_price=take_profit_price
    )
    
    # Calculate actual win/loss ratio from prices
    win_amount = take_profit_price - entry_price
    loss_amount = entry_price - stop_loss_price
    current_rr_ratio = win_amount / loss_amount
    
    # Kelly formula with actual ratio
    kelly_pct = (win_rate * current_rr_ratio - (1 - win_rate)) / current_rr_ratio
    expected_size = (account_balance * kelly_pct) / entry_price
    
    print(f"\nTest case 2: With take profit price={take_profit_price}")
    print(f"  Actual win/loss ratio: {win_amount}/{loss_amount} = {current_rr_ratio:.2f}")
    print(f"  Kelly formula: ({win_rate}*{current_rr_ratio} - {1-win_rate})/{current_rr_ratio} = {kelly_pct:.4f}")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={kelly_pct*100:.2f}%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    assert abs(risk - kelly_pct*100) < 0.01, f"Expected risk {kelly_pct*100}%, got {risk}%"
    
    # Test case 3: Short position with take profit
    entry_price = 40000.0
    stop_loss_price = 41000.0  # Short stop higher than entry
    take_profit_price = 38000.0  # Short take profit lower than entry
    size, risk = sizer.calculate_position_size(
        entry_price, stop_loss_price, take_profit_price=take_profit_price
    )
    
    # Calculate actual win/loss ratio from prices for short
    win_amount = entry_price - take_profit_price
    loss_amount = stop_loss_price - entry_price
    current_rr_ratio = win_amount / loss_amount
    
    # Kelly formula with actual ratio
    kelly_pct = (win_rate * current_rr_ratio - (1 - win_rate)) / current_rr_ratio
    expected_size = (account_balance * kelly_pct) / entry_price
    
    print(f"\nTest case 3: Short position with take profit")
    print(f"  Actual win/loss ratio: {win_amount}/{loss_amount} = {current_rr_ratio:.2f}")
    print(f"  Kelly formula: ({win_rate}*{current_rr_ratio} - {1-win_rate})/{current_rr_ratio} = {kelly_pct:.4f}")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={kelly_pct*100:.2f}%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    assert abs(risk - kelly_pct*100) < 0.01, f"Expected risk {kelly_pct*100}%, got {risk}%"
    
    # Test case 4: Half-Kelly (kelly_fraction=0.5)
    kelly_fraction = 0.5
    sizer = KellyCriterionSizer(account_balance, win_rate=win_rate, 
                              avg_win_loss_ratio=avg_win_loss_ratio,
                              kelly_fraction=kelly_fraction)
    
    entry_price = 40000.0
    stop_loss_price = 39000.0
    size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
    
    # Kelly formula with fraction
    full_kelly_pct = (win_rate * avg_win_loss_ratio - (1 - win_rate)) / avg_win_loss_ratio
    half_kelly_pct = full_kelly_pct * kelly_fraction
    expected_size = (account_balance * half_kelly_pct) / entry_price
    
    print(f"\nTest case 4: Half-Kelly (fraction={kelly_fraction})")
    print(f"  Full Kelly: {full_kelly_pct:.4f}, Half Kelly: {half_kelly_pct:.4f}")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={half_kelly_pct*100:.2f}%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    assert abs(risk - half_kelly_pct*100) < 0.01, f"Expected risk {half_kelly_pct*100}%, got {risk}%"
    
    # Test case 5: Negative expectancy (should return zero position)
    win_rate = 0.3  # Low win rate
    avg_win_loss_ratio = 1.0  # Even payoff
    sizer = KellyCriterionSizer(account_balance, win_rate=win_rate, 
                              avg_win_loss_ratio=avg_win_loss_ratio)
    
    size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
    
    # Kelly formula: f* = (p*b - q)/b where p=win rate, q=1-p, b=win/loss ratio
    kelly_pct = (win_rate * avg_win_loss_ratio - (1 - win_rate)) / avg_win_loss_ratio
    # Negative Kelly should result in zero position
    
    print(f"\nTest case 5: Negative expectancy (win_rate={win_rate}, ratio={avg_win_loss_ratio})")
    print(f"  Kelly formula: ({win_rate}*{avg_win_loss_ratio} - {1-win_rate})/{avg_win_loss_ratio} = {kelly_pct:.4f}")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size=0.000000, risk=0.00%")
    assert abs(size) < 0.0001, f"Expected size near 0, got {size}"
    assert abs(risk) < 0.01, f"Expected risk near 0%, got {risk}%"
    
    # Test case 6: Max risk limiting
    win_rate = 0.8  # High win rate
    avg_win_loss_ratio = 5.0  # High payoff ratio
    max_risk_pct = 3.0  # Lower than the Kelly percentage would suggest
    sizer = KellyCriterionSizer(account_balance, win_rate=win_rate, 
                              avg_win_loss_ratio=avg_win_loss_ratio,
                              max_risk_pct=max_risk_pct)
    
    size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
    
    # Kelly formula would give a high percentage, but we're limited by max_risk_pct
    kelly_pct = (win_rate * avg_win_loss_ratio - (1 - win_rate)) / avg_win_loss_ratio
    expected_risk = min(kelly_pct*100, max_risk_pct)
    expected_size = (account_balance * expected_risk/100) / entry_price
    
    print(f"\nTest case 6: Max risk limiting (max_risk_pct={max_risk_pct})")
    print(f"  Kelly formula: ({win_rate}*{avg_win_loss_ratio} - {1-win_rate})/{avg_win_loss_ratio} = {kelly_pct:.4f}")
    print(f"  Full Kelly %: {kelly_pct*100:.2f}%, Limited to max_risk_pct: {max_risk_pct}%")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={expected_risk:.2f}%")
    assert abs(risk - expected_risk) < 0.01, f"Expected risk {expected_risk}%, got {risk}%"
    
    print("\nKellyCriterionSizer tests completed successfully!")
    return True

def test_anti_martingale_sizer():
    """Test the AntiMartingaleSizer class"""
    print("\n=== Testing AntiMartingaleSizer ===")
    
    # Initialize with default parameters
    account_balance = 10000.0
    base_unit_pct = 1.0
    increase_factor = 1.5
    max_units = 4
    sizer = AntiMartingaleSizer(account_balance, base_unit_pct=base_unit_pct,
                              increase_factor=increase_factor, max_units=max_units)
    
    # Test case 1: Initial sizing (1 unit)
    entry_price = 40000.0
    stop_loss_price = 39000.0
    size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
    
    # Base sizer calculation
    base_sizer = BasePositionSizer(account_balance, max_risk_pct=base_unit_pct)
    base_size, base_risk = base_sizer.calculate_position_size(entry_price, stop_loss_price)
    expected_size = base_size  # 1 unit initially
    
    print(f"Test case 1: Initial sizing (1 unit)")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={base_risk:.2f}%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    assert abs(risk - base_risk) < 0.01, f"Expected risk {base_risk}%, got {risk}%"
    
    # Test case 2: After one win
    sizer.update_after_trade(is_win=True)
    assert sizer.current_units == 1 * increase_factor, f"Expected units {1*increase_factor}, got {sizer.current_units}"
    assert sizer.consecutive_wins == 1, f"Expected consecutive_wins 1, got {sizer.consecutive_wins}"
    
    size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
    expected_size = base_size * (1 * increase_factor)
    
    print(f"\nTest case 2: After one win (units={sizer.current_units})")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={base_risk*sizer.current_units:.2f}%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    
    # Test case 3: After two consecutive wins
    sizer.update_after_trade(is_win=True)
    assert sizer.current_units == 1 * increase_factor * increase_factor, f"Expected units {1*increase_factor*increase_factor}, got {sizer.current_units}"
    assert sizer.consecutive_wins == 2, f"Expected consecutive_wins 2, got {sizer.consecutive_wins}"
    
    size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
    expected_size = base_size * (1 * increase_factor * increase_factor)
    
    print(f"\nTest case 3: After two consecutive wins (units={sizer.current_units})")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={base_risk*sizer.current_units:.2f}%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    
    # Test case 4: After a loss (should reset to 1 unit)
    sizer.update_after_trade(is_win=False)
    assert sizer.current_units == 1, f"Expected units 1, got {sizer.current_units}"
    assert sizer.consecutive_wins == 0, f"Expected consecutive_wins 0, got {sizer.consecutive_wins}"
    
    size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
    expected_size = base_size
    
    print(f"\nTest case 4: After a loss (reset to units={sizer.current_units})")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={base_risk:.2f}%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    
    # Test case 5: Max units limiting
    # Set up a series of wins to exceed max_units
    for i in range(5):  # Should go well beyond max_units
        sizer.update_after_trade(is_win=True)
        
    current_units = min(sizer.current_units, max_units)
    assert current_units == max_units, f"Expected units capped at {max_units}, got {current_units}"
    
    size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
    expected_size = base_size * max_units
    
    print(f"\nTest case 5: Max units limiting (max_units={max_units})")
    print(f"  Raw units: {sizer.current_units}, Limited units: {current_units}")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected: size={expected_size:.6f}, risk={base_risk*max_units:.2f}%")
    assert abs(size - expected_size) < 0.001, f"Expected size {expected_size}, got {size}"
    
    # Test case 6: Max risk limiting
    # Create a sizer with low max_risk_pct but high base_unit_pct
    max_risk_pct = 2.0
    base_unit_pct = 1.0
    sizer = AntiMartingaleSizer(account_balance, max_risk_pct=max_risk_pct,
                              base_unit_pct=base_unit_pct, increase_factor=increase_factor)
    
    # Simulate 3 consecutive wins
    for i in range(3):
        sizer.update_after_trade(is_win=True)
        
    # Current units should be 3.375 (1 * 1.5 * 1.5 * 1.5)
    expected_units = 1 * (increase_factor ** 3)
    assert abs(sizer.current_units - expected_units) < 0.001, f"Expected units {expected_units}, got {sizer.current_units}"
    
    # This would make the risk too high, so it should be limited
    size, risk = sizer.calculate_position_size(entry_price, stop_loss_price)
    
    # The maximum risk should be limited to max_risk_pct
    expected_risk = max_risk_pct
    
    print(f"\nTest case 6: Max risk limiting (max_risk_pct={max_risk_pct})")
    print(f"  Current units: {sizer.current_units}")
    print(f"  Raw risk: {base_unit_pct * sizer.current_units:.2f}%, Limited risk: {max_risk_pct}%")
    print(f"  Result: size={size:.6f}, risk={risk:.2f}%")
    print(f"  Expected risk: {expected_risk:.2f}%")
    assert abs(risk - expected_risk) < 0.01, f"Expected risk {expected_risk}%, got {risk}%"
    
    print("\nAntiMartingaleSizer tests completed successfully!")
    return True

def test_portfolio_sizer():
    """Test the PortfolioSizer class"""
    print("\n=== Testing PortfolioSizer ===")
    
    # Initialize with default parameters
    account_balance = 10000.0
    max_portfolio_risk = 5.0
    max_symbol_risk = 2.0
    max_correlated_exposure = 3.0
    correlation_threshold = 0.7
    
    sizer = PortfolioSizer(account_balance, max_portfolio_risk=max_portfolio_risk,
                         max_symbol_risk=max_symbol_risk, 
                         max_correlated_exposure=max_correlated_exposure,
                         correlation_threshold=correlation_threshold)
    
    # Test case 1: Basic allocation without correlation
    symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
    signals = {
        'BTCUSDT': {'signal': 'buy', 'strength': 1.0, 'entry_price': 40000, 'stop_loss': 39000},
        'ETHUSDT': {'signal': 'buy', 'strength': 0.8, 'entry_price': 2500, 'stop_loss': 2400},
        'SOLUSDT': {'signal': 'sell', 'strength': 0.6, 'entry_price': 100, 'stop_loss': 105}
    }
    correlation_matrix = {}  # Empty correlation matrix for now
    
    allocations = sizer.calculate_position_allocations(symbols, signals, correlation_matrix)
    
    print(f"Test case 1: Basic allocation without correlation")
    print(f"  Symbols: {symbols}")
    
    # Check allocation for each symbol
    for symbol in symbols:
        allocation = allocations.get(symbol, {})
        print(f"  {symbol}: size={allocation.get('position_size', 0):.6f}, " + 
              f"risk={allocation.get('risk_pct', 0):.2f}%, " + 
              f"side={allocation.get('side', 'N/A')}")
        
        # Check that risk percentage is proportional to signal strength
        signal_strength = signals[symbol]['strength']
        expected_risk = max_symbol_risk * signal_strength
        actual_risk = allocation.get('risk_pct', 0)
        
        assert abs(actual_risk - expected_risk) < 0.01, f"Expected risk {expected_risk}%, got {actual_risk}%"
    
    # Calculate total risk
    total_risk = sum(alloc.get('risk_pct', 0) for alloc in allocations.values())
    print(f"  Total risk: {total_risk:.2f}%")
    
    # If total risk exceeds max_portfolio_risk, it should be scaled down
    if total_risk > max_portfolio_risk:
        expected_scaling = max_portfolio_risk / total_risk
        actual_scaling = min(alloc.get('risk_pct', 0) / (max_symbol_risk * signals[symbol]['strength']) 
                          for symbol, alloc in allocations.items())
        
        print(f"  Risk scaling: {actual_scaling:.4f}")
        assert abs(actual_scaling - expected_scaling) < 0.01, f"Expected scaling {expected_scaling}, got {actual_scaling}"
    
    # Test case 2: Allocation with correlation
    correlation_matrix = {
        'BTCUSDT': {'BTCUSDT': 1.0, 'ETHUSDT': 0.8, 'SOLUSDT': 0.6},
        'ETHUSDT': {'BTCUSDT': 0.8, 'ETHUSDT': 1.0, 'SOLUSDT': 0.7},
        'SOLUSDT': {'BTCUSDT': 0.6, 'ETHUSDT': 0.7, 'SOLUSDT': 1.0}
    }
    
    allocations = sizer.calculate_position_allocations(symbols, signals, correlation_matrix)
    
    print(f"\nTest case 2: Allocation with correlation")
    
    # Check allocation for each symbol
    for symbol in symbols:
        allocation = allocations.get(symbol, {})
        print(f"  {symbol}: size={allocation.get('position_size', 0):.6f}, " + 
              f"risk={allocation.get('risk_pct', 0):.2f}%, " + 
              f"side={allocation.get('side', 'N/A')}")
        
        # Check if correlation information is present
        if 'correlation_info' in allocation:
            corr_info = allocation['correlation_info']
            print(f"    Correlation exposure: {corr_info.get('exposure_score', 0):.2f}")
            print(f"    Scale factor: {corr_info.get('scale_factor', 1.0):.2f}")
    
    # Test case 3: Check position updates
    print("\nTest case 3: Position updates")
    
    # Add some positions
    sizer.update_position('BTCUSDT', 'LONG', 0.1, 4000.0)
    sizer.update_position('ETHUSDT', 'LONG', 1.0, 2500.0)
    
    # Check the current positions
    print(f"  Current positions:")
    for symbol, position in sizer.current_positions.items():
        print(f"    {symbol}: {position.get('side', 'N/A')} " + 
              f"size={position.get('position_size', 0):.6f}, " + 
              f"value=${position.get('position_value', 0):.2f}")
        
    # Remove a position
    sizer.remove_position('BTCUSDT')
    assert 'BTCUSDT' not in sizer.current_positions, "BTCUSDT should be removed from positions"
    print(f"  After removing BTCUSDT:")
    for symbol, position in sizer.current_positions.items():
        print(f"    {symbol}: {position.get('side', 'N/A')} " + 
              f"size={position.get('position_size', 0):.6f}, " + 
              f"value=${position.get('position_value', 0):.2f}")
    
    # Test case 4: Update account balance
    print("\nTest case 4: Update account balance")
    
    initial_balance = sizer.account_balance
    print(f"  Initial balance: ${initial_balance:.2f}")
    
    new_balance = 12000.0
    sizer.update_account_balance(new_balance)
    assert sizer.account_balance == new_balance, f"Expected balance {new_balance}, got {sizer.account_balance}"
    print(f"  Updated balance: ${sizer.account_balance:.2f}")
    
    # Test negative balance handling
    sizer.update_account_balance(-5000.0)
    assert sizer.account_balance == 0.0, f"Expected balance 0.0 (floor), got {sizer.account_balance}"
    print(f"  Negative balance handled: ${sizer.account_balance:.2f}")
    
    print("\nPortfolioSizer tests completed successfully!")
    return True

def test_factory_function():
    """Test the create_position_sizer factory function"""
    print("\n=== Testing create_position_sizer Factory Function ===")
    
    account_balance = 10000.0
    
    # Test all sizer types
    sizer_types = ['basic', 'dynamic', 'kelly', 'antimartingale', 'portfolio', 'unknown']
    
    for sizer_type in sizer_types:
        sizer = create_position_sizer(sizer_type, account_balance)
        
        # Check the type of sizer created
        if sizer_type == 'basic':
            expected_type = BasePositionSizer
        elif sizer_type == 'dynamic':
            expected_type = DynamicPositionSizer
        elif sizer_type == 'kelly':
            expected_type = KellyCriterionSizer
        elif sizer_type == 'antimartingale':
            expected_type = AntiMartingaleSizer
        elif sizer_type == 'portfolio':
            expected_type = PortfolioSizer
        else:
            expected_type = BasePositionSizer  # fallback for unknown types
            
        actual_type = type(sizer)
        print(f"Requested: {sizer_type}, Created: {actual_type.__name__}")
        assert isinstance(sizer, expected_type), f"Expected type {expected_type.__name__}, got {actual_type.__name__}"
    
    # Test with additional parameters
    kwargs = {
        'max_risk_pct': 3.0,
        'leverage': 5
    }
    
    basic_sizer = create_position_sizer('basic', account_balance, **kwargs)
    assert basic_sizer.max_risk_pct == kwargs['max_risk_pct'], f"Expected max_risk_pct {kwargs['max_risk_pct']}, got {basic_sizer.max_risk_pct}"
    assert basic_sizer.leverage == kwargs['leverage'], f"Expected leverage {kwargs['leverage']}, got {basic_sizer.leverage}"
    
    print(f"\nWith kwargs: {kwargs}")
    print(f"  Created BasePositionSizer with max_risk_pct={basic_sizer.max_risk_pct}, leverage={basic_sizer.leverage}")
    
    # Test with Kelly-specific parameters
    kelly_kwargs = {
        'win_rate': 0.6,
        'avg_win_loss_ratio': 2.0,
        'kelly_fraction': 0.5
    }
    
    kelly_sizer = create_position_sizer('kelly', account_balance, **kelly_kwargs)
    assert isinstance(kelly_sizer, KellyCriterionSizer), f"Expected KellyCriterionSizer, got {type(kelly_sizer).__name__}"
    assert kelly_sizer.win_rate == kelly_kwargs['win_rate'], f"Expected win_rate {kelly_kwargs['win_rate']}, got {kelly_sizer.win_rate}"
    assert kelly_sizer.avg_win_loss_ratio == kelly_kwargs['avg_win_loss_ratio'], f"Expected avg_win_loss_ratio {kelly_kwargs['avg_win_loss_ratio']}, got {kelly_sizer.avg_win_loss_ratio}"
    assert kelly_sizer.kelly_fraction == kelly_kwargs['kelly_fraction'], f"Expected kelly_fraction {kelly_kwargs['kelly_fraction']}, got {kelly_sizer.kelly_fraction}"
    
    print(f"\nWith Kelly kwargs: {kelly_kwargs}")
    print(f"  Created KellyCriterionSizer with win_rate={kelly_sizer.win_rate}, " + 
          f"avg_win_loss_ratio={kelly_sizer.avg_win_loss_ratio}, " + 
          f"kelly_fraction={kelly_sizer.kelly_fraction}")
          
    print("\nFactory function tests completed successfully!")
    return True

def run_all_tests():
    """Run all position sizing tests"""
    start_time = datetime.now()
    
    print("=== Starting Position Sizing Tests ===")
    print(f"Time: {start_time}")
    print(f"Using actual module: {HAS_MODULE}")
    
    # Dictionary to track test results
    results = {
        "meta": {
            "timestamp": start_time,
            "module_available": HAS_MODULE
        },
        "tests": {}
    }
    
    # Run tests
    test_functions = [
        test_base_position_sizer,
        test_dynamic_position_sizer,
        test_kelly_criterion_sizer,
        test_anti_martingale_sizer,
        test_portfolio_sizer,
        test_factory_function
    ]
    
    all_passed = True
    
    for test_func in test_functions:
        test_name = test_func.__name__
        try:
            passed = test_func()
            results["tests"][test_name] = {"passed": passed}
        except Exception as e:
            print(f"Error in {test_name}: {e}")
            print(traceback.format_exc())
            results["tests"][test_name] = {
                "passed": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            all_passed = False
    
    # Calculate test duration
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    results["meta"]["duration_seconds"] = duration
    
    # Save results
    result_path = os.path.join('../test_results', f"position_sizing_tests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    def serialize_datetime(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return obj
    
    with open(result_path, 'w') as f:
        json.dump(results, f, default=serialize_datetime, indent=2)
        
    print(f"\nSaved test results to {result_path}")
    
    # Print summary
    print("\n=== Test Summary ===")
    print(f"Testing completed in {duration:.2f} seconds")
    
    for test_name, result in results["tests"].items():
        if result.get("passed", False):
            print(f"✅ {test_name}: Passed")
        else:
            print(f"❌ {test_name}: Failed - {result.get('error', 'Unknown error')}")
            
    print(f"\nOverall result: {'PASSED' if all_passed else 'FAILED'}")
    
    return results

if __name__ == "__main__":
    run_all_tests()