"""
Kiểm tra module VolumeProfileAnalyzer với dữ liệu thực 3 tháng

Script này sẽ chạy kiểm tra VolumeProfileAnalyzer với dữ liệu thực tế 3 tháng có sẵn
cho BTCUSDT và ETHUSDT, sau đó tạo báo cáo chi tiết về kết quả.
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import logging
import json
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('test_volume_profile_3months')

# Import VolumeProfileAnalyzer
try:
    from volume_profile_analyzer_extended import VolumeProfileAnalyzer
    logger.info("Đã import VolumeProfileAnalyzer thành công")
except ImportError as e:
    logger.error(f"Lỗi khi import VolumeProfileAnalyzer: {str(e)}")
    sys.exit(1)

def load_data(symbol: str, timeframe: str = '1h') -> pd.DataFrame:
    """
    Load dữ liệu từ file CSV
    
    Args:
        symbol: Ký hiệu cặp giao dịch (ví dụ: BTCUSDT)
        timeframe: Khung thời gian (ví dụ: 1h, 4h)
        
    Returns:
        DataFrame chứa dữ liệu của cặp giao dịch
    """
    file_path = f'data/{symbol}_{timeframe}.csv'
    
    if not os.path.exists(file_path):
        logger.error(f"Không tìm thấy file dữ liệu {file_path}")
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(file_path)
        
        # Convert timestamp to datetime for index
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        
        # Ensure data is sorted by time
        df.sort_index(inplace=True)
        
        logger.info(f"Đã nạp dữ liệu {symbol}_{timeframe}: {len(df)} dòng từ {df.index.min()} đến {df.index.max()}")
        return df
    
    except Exception as e:
        logger.error(f"Lỗi khi nạp dữ liệu {file_path}: {str(e)}")
        return pd.DataFrame()

def count_data_periods(df: pd.DataFrame) -> Dict:
    """
    Đếm số lượng dữ liệu theo các mốc thời gian
    
    Args:
        df: DataFrame dữ liệu
        
    Returns:
        Dict chứa số lượng dữ liệu theo các khoảng thời gian
    """
    if df.empty:
        return {'days': 0, 'weeks': 0, 'months': 0, 'total_candles': 0}
    
    # Tính số ngày, tuần, tháng trong dữ liệu
    start_date = df.index.min()
    end_date = df.index.max()
    days = (end_date - start_date).days
    weeks = days // 7
    months = days // 30
    
    return {
        'days': days,
        'weeks': weeks,
        'months': months,
        'total_candles': len(df),
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    }

def test_volume_profile(symbol: str, timeframe: str = '1h') -> Dict:
    """
    Chạy kiểm tra VolumeProfileAnalyzer cho cặp tiền và khung thời gian
    
    Args:
        symbol: Ký hiệu cặp giao dịch (ví dụ: BTCUSDT)
        timeframe: Khung thời gian (ví dụ: 1h, 4h)
        
    Returns:
        Dict chứa kết quả kiểm tra
    """
    logger.info(f"Bắt đầu kiểm tra {symbol} {timeframe}")
    
    # Load dữ liệu
    df = load_data(symbol, timeframe)
    if df.empty:
        return {'error': f"Không có dữ liệu cho {symbol}_{timeframe}"}
    
    # Thông tin dữ liệu
    data_info = count_data_periods(df)
    logger.info(f"Dữ liệu {symbol}_{timeframe}: {data_info['total_candles']} nến, "
               f"{data_info['days']} ngày, {data_info['weeks']} tuần, {data_info['months']} tháng")
    
    # Khởi tạo VolumeProfileAnalyzer
    analyzer = VolumeProfileAnalyzer()
    
    # Bắt đầu kiểm tra
    results = {}
    
    # Test 1: Tính volume profile theo session (1 ngày)
    logger.info("1. Kiểm tra calculate_volume_profile (session)...")
    session_profile = analyzer.calculate_volume_profile(df, symbol, 'session')
    
    if not session_profile:
        logger.warning("Không tính được session profile")
        results['session_profile'] = {'error': 'Failed'}
    else:
        results['session_profile'] = {
            'poc': session_profile.get('poc'),
            'value_area': session_profile.get('value_area'),
            'volume_nodes_count': len(session_profile.get('volume_nodes', [])),
            'success': True
        }
        logger.info(f"- POC: {session_profile.get('poc')}")
        logger.info(f"- Value Area: {session_profile.get('value_area')}")
        logger.info(f"- Volume Nodes: {len(session_profile.get('volume_nodes', []))}")
    
    # Test 2: Tính volume profile theo ngày
    logger.info("2. Kiểm tra calculate_volume_profile (daily)...")
    daily_profile = analyzer.calculate_volume_profile(df, symbol, 'daily')
    
    if not daily_profile:
        logger.warning("Không tính được daily profile")
        results['daily_profile'] = {'error': 'Failed'}
    else:
        results['daily_profile'] = {
            'poc': daily_profile.get('poc'),
            'value_area': daily_profile.get('value_area'),
            'volume_nodes_count': len(daily_profile.get('volume_nodes', [])),
            'success': True
        }
        logger.info(f"- POC: {daily_profile.get('poc')}")
        logger.info(f"- Value Area: {daily_profile.get('value_area')}")
        logger.info(f"- Volume Nodes: {len(daily_profile.get('volume_nodes', []))}")
    
    # Test 3: Xác định vùng hỗ trợ/kháng cự
    logger.info("3. Kiểm tra identify_support_resistance...")
    sr_levels = analyzer.identify_support_resistance(df, symbol)
    
    if not sr_levels:
        logger.warning("Không xác định được vùng hỗ trợ/kháng cự")
        results['support_resistance'] = {'error': 'Failed'}
    else:
        results['support_resistance'] = {
            'support_levels': len(sr_levels.get('support_levels', [])),
            'resistance_levels': len(sr_levels.get('resistance_levels', [])),
            'success': True
        }
        logger.info(f"- Support Levels: {len(sr_levels.get('support_levels', []))}")
        logger.info(f"- Resistance Levels: {len(sr_levels.get('resistance_levels', []))}")
    
    # Test 4: Phân tích vùng giao dịch
    logger.info("4. Kiểm tra analyze_trading_range...")
    trading_range = analyzer.analyze_trading_range(df, symbol)
    
    if not trading_range:
        logger.warning("Không phân tích được vùng giao dịch")
        results['trading_range'] = {'error': 'Failed'}
    else:
        results['trading_range'] = {
            'position': trading_range.get('position'),
            'nearest_support': trading_range.get('nearest_support'),
            'nearest_resistance': trading_range.get('nearest_resistance'),
            'breakout_potential_up': trading_range.get('breakout_potential', {}).get('up'),
            'breakout_potential_down': trading_range.get('breakout_potential', {}).get('down'),
            'success': True
        }
        logger.info(f"- Position: {trading_range.get('position')}")
        logger.info(f"- Nearest Support: {trading_range.get('nearest_support')}")
        logger.info(f"- Nearest Resistance: {trading_range.get('nearest_resistance')}")
        logger.info(f"- Breakout Potential Up: {trading_range.get('breakout_potential', {}).get('up')}")
        logger.info(f"- Breakout Potential Down: {trading_range.get('breakout_potential', {}).get('down')}")
    
    # Test 5: VWAP Zones
    logger.info("5. Kiểm tra identify_vwap_zones...")
    try:
        # Sử dụng dữ liệu 1 ngày gần nhất để kiểm tra VWAP
        last_day_data = df.iloc[-24:]
        vwap_result = analyzer.identify_vwap_zones(last_day_data)
        
        if not vwap_result:
            logger.warning("Không tính được vùng VWAP")
            results['vwap_zones'] = {'error': 'Failed'}
        else:
            results['vwap_zones'] = {
                'vwap': vwap_result.get('vwap'),
                'upper_band': vwap_result.get('bands', {}).get('upper'),
                'lower_band': vwap_result.get('bands', {}).get('lower'),
                'success': True
            }
            logger.info(f"- VWAP: {vwap_result.get('vwap')}")
            logger.info(f"- VWAP Upper Band (1SD): {vwap_result.get('bands', {}).get('upper')}")
            logger.info(f"- VWAP Lower Band (1SD): {vwap_result.get('bands', {}).get('lower')}")
    except Exception as e:
        logger.error(f"Lỗi khi kiểm tra VWAP: {str(e)}")
        results['vwap_zones'] = {'error': str(e)}
    
    # Test 6: Tạo biểu đồ
    logger.info("6. Tạo biểu đồ...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        # Tạo Volume Profile chart
        vp_chart = analyzer.visualize_volume_profile(symbol, custom_path=f'charts/volume_profile/volume_profile_{symbol}_{timestamp}.png')
        
        # Tạo VWAP chart
        vwap_chart = analyzer.visualize_vwap_zones(last_day_data, symbol, 
                                                custom_path=f'charts/vwap/vwap_{symbol}_{timestamp}.png')
        
        results['charts'] = {
            'volume_profile': vp_chart,
            'vwap': vwap_chart,
            'success': True
        }
        logger.info(f"- Volume Profile Chart: {vp_chart}")
        logger.info(f"- VWAP Chart: {vwap_chart}")
    except Exception as e:
        logger.error(f"Lỗi khi tạo biểu đồ: {str(e)}")
        results['charts'] = {'error': str(e)}
    
    # Hoàn thành kiểm tra
    logger.info(f"Kiểm tra {symbol}_{timeframe} hoàn tất!")
    
    # Thêm thông tin dữ liệu vào kết quả
    results['data_info'] = data_info
    
    return results

def main():
    """
    Hàm chính để chạy kiểm tra và tạo báo cáo
    """
    logger.info("Bắt đầu kiểm tra VolumeProfileAnalyzer với dữ liệu thực 3 tháng")
    
    # Danh sách cặp tiền từ backtest_master_config.json
    try:
        with open('backtest_master_config.json', 'r') as f:
            config = json.load(f)
            symbols = config.get('symbols', ['BTCUSDT', 'ETHUSDT'])
    except Exception:
        symbols = ['BTCUSDT', 'ETHUSDT']  # Mặc định nếu không đọc được file config
    
    timeframes = ['1h']  # Chỉ kiểm tra timeframe 1h hiện tại
    
    # Chạy kiểm tra cho tất cả cặp tiền và khung thời gian
    all_results = {}
    
    for symbol in symbols:
        all_results[symbol] = {}
        for timeframe in timeframes:
            all_results[symbol][timeframe] = test_volume_profile(symbol, timeframe)
    
    # Tạo báo cáo tổng hợp
    report_path = 'backtest_reports/volume_profile_test_results.json'
    os.makedirs('backtest_reports', exist_ok=True)
    
    with open(report_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    logger.info(f"Báo cáo kiểm tra đã được lưu vào {report_path}")
    
    # Tóm tắt kết quả
    print("\n===== TÓM TẮT KẾT QUẢ KIỂM TRA VOLUME PROFILE =====")
    for symbol in all_results:
        for timeframe in all_results[symbol]:
            result = all_results[symbol][timeframe]
            data_info = result.get('data_info', {})
            print(f"\n{symbol} {timeframe}:")
            print(f"- Dữ liệu: {data_info.get('total_candles')} nến, {data_info.get('days')} ngày")
            print(f"- Khoảng thời gian: {data_info.get('start_date')} đến {data_info.get('end_date')}")
            
            tests = [
                ('Session Profile', result.get('session_profile', {}).get('success', False)),
                ('Daily Profile', result.get('daily_profile', {}).get('success', False)),
                ('Support/Resistance', result.get('support_resistance', {}).get('success', False)),
                ('Trading Range', result.get('trading_range', {}).get('success', False)),
                ('VWAP Zones', result.get('vwap_zones', {}).get('success', False)),
                ('Charts', result.get('charts', {}).get('success', False))
            ]
            
            for test_name, success in tests:
                status = '✅ PASS' if success else '❌ FAIL'
                print(f"- {test_name}: {status}")
    
    print("\n===== KẾT THÚC KIỂM TRA =====")

if __name__ == "__main__":
    main()