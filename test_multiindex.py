import pandas as pd
import yfinance as yf
import numpy as np
import logging

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger('test_multiindex')

def test_multiindex_handling():
    """
    Kiểm tra xử lý MultiIndex từ yfinance
    """
    # Tải dữ liệu
    logger.info("Đang tải dữ liệu BTC-USD")
    df = yf.download("BTC-USD", period="1mo", interval="1d")
    
    # In thông tin về DataFrame
    logger.info(f"Loại của columns: {type(df.columns)}")
    logger.info(f"Các cột: {list(df.columns)}")
    
    # Kiểm tra MultiIndex
    if isinstance(df.columns, pd.MultiIndex):
        logger.info("DataFrame có MultiIndex columns")
        logger.info(f"Các level: {df.columns.names}")
        logger.info(f"Level 0 values: {df.columns.get_level_values(0).unique().tolist()}")
        logger.info(f"Level 1 values: {df.columns.get_level_values(1).unique().tolist()}")
        
        # Trích xuất dữ liệu
        close_col = ('Close', df.columns.get_level_values(1)[0])
        logger.info(f"Close column: {close_col}")
        
        # Truy cập dữ liệu
        close_data = df[close_col]
        logger.info(f"Giá đóng cửa đầu tiên: {close_data.iloc[0]}")
        
        # Đổi tên cột (lowercase)
        column_map = {
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
            'Adj Close': 'adj_close'
        }
        
        # Tạo từ điển mapping mới cho MultiIndex
        new_columns = []
        for col in df.columns:
            # col[0] là tên cột (Open, High, ...), col[1] là ticker
            if col[0] in column_map:
                new_columns.append((column_map[col[0]], col[1]))
            else:
                new_columns.append(col)
        
        # Đổi tên cột
        df.columns = pd.MultiIndex.from_tuples(new_columns, names=df.columns.names)
        logger.info(f"Các cột sau khi đổi tên: {list(df.columns)}")
        
        # Truy cập dữ liệu sau khi đổi tên
        close_col = ('close', df.columns.get_level_values(1)[0])
        logger.info(f"Close column sau khi đổi tên: {close_col}")
        close_data = df[close_col]
        logger.info(f"Giá đóng cửa đầu tiên (sau khi đổi tên): {close_data.iloc[0]}")
        
        # Thêm cột RSI
        import talib as ta
        df['rsi'] = ta.RSI(close_data.values, timeperiod=14)
        logger.info(f"Các cột sau khi thêm RSI: {list(df.columns)}")
        logger.info(f"RSI đầu tiên: {df['rsi'].iloc[14]}")  # RSI cần ít nhất 14 giá trị đầu tiên
    else:
        logger.info("DataFrame có columns thông thường (không phải MultiIndex)")
    
    logger.info("Kiểm tra hoàn tất")

if __name__ == "__main__":
    test_multiindex_handling()