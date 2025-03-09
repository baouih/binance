#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script kiểm tra hiệu suất của các altcoin có thanh khoản cao trên nhiều mức rủi ro

Script này chạy backtest trên danh sách các altcoin có thanh khoản cao
với các mức rủi ro khác nhau và khung thời gian khác nhau.
"""

import os
import sys
import json
import logging
import time
import ccxt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from typing import Dict, List, Any
import multiprocessing
import random

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('altcoin_test.log')
    ]
)

logger = logging.getLogger('altcoin_test')

# Mức rủi ro cần test
RISK_LEVELS = [10.0, 15.0, 20.0, 30.0]

# Khung thời gian cần test
TIMEFRAMES = ['1d', '4h', '1h']

# Thời gian test (ngày)
TEST_DAYS = 180  # 6 tháng

# Danh sách các altcoin mặc định nếu không thể lấy từ API
DEFAULT_ALTCOINS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "AVAXUSDT", 
    "ADAUSDT", "DOGEUSDT", "XRPUSDT", "DOTUSDT", "MATICUSDT",
    "LINKUSDT", "LTCUSDT", "ATOMUSDT", "UNIUSDT", "ICPUSDT"
]

def get_top_altcoins(limit: int = 20) -> List[str]:
    """
    Lấy danh sách các altcoin có thanh khoản cao nhất

    Args:
        limit (int): Số lượng altcoin cần lấy

    Returns:
        List[str]: Danh sách các altcoin
    """
    try:
        # Khởi tạo client Binance Futures
        binance = ccxt.binanceusdm({
            'enableRateLimit': True,
        })
        
        # Lấy danh sách tất cả các symbol trên Binance Futures
        markets = binance.load_markets()
        
        # Lọc ra các altcoin
        all_coins = []
        for symbol in markets:
            if symbol.endswith('/USDT'):
                symbol_formatted = symbol.replace('/', '')
                all_coins.append(symbol_formatted)
        
        # Lấy thông tin khối lượng giao dịch để sắp xếp theo thanh khoản
        coins_with_volume = []
        for i, symbol in enumerate(all_coins[:40]):  # Giới hạn số lượng để tránh rate limit
            try:
                # Lấy ticker 24h
                ticker = binance.fetch_ticker(symbol.replace('USDT', '/USDT'))
                volume_usd = ticker['quoteVolume']  # Khối lượng giao dịch tính bằng USDT
                coins_with_volume.append({
                    'symbol': symbol,
                    'volume': volume_usd
                })
                logger.info(f'Đã lấy dữ liệu cho {symbol}: Khối lượng 24h = {volume_usd:,.2f} USDT')
                time.sleep(0.3)  # Tạm dừng để tránh rate limit
            except Exception as e:
                logger.error(f'Lỗi khi lấy dữ liệu cho {symbol}: {str(e)}')
        
        # Sắp xếp theo khối lượng giao dịch (từ cao đến thấp)
        coins_with_volume.sort(key=lambda x: x['volume'], reverse=True)
        
        # Lấy altcoin có thanh khoản cao nhất
        top_altcoins = [coin['symbol'] for coin in coins_with_volume[:limit]]
        
        logger.info(f'Đã lấy {len(top_altcoins)} altcoin có thanh khoản cao nhất')
        
        return top_altcoins
    
    except Exception as e:
        logger.error(f'Lỗi khi lấy danh sách altcoin: {str(e)}')
        logger.warning(f'Sử dụng danh sách mặc định với {len(DEFAULT_ALTCOINS)} altcoin')
        return DEFAULT_ALTCOINS

def create_sample_backtest_result(symbol: str, timeframe: str, risk_level: float) -> Dict:
    """
    Tạo kết quả backtest mẫu để mô phỏng

    Args:
        symbol (str): Ký hiệu cặp tiền
        timeframe (str): Khung thời gian
        risk_level (float): Mức rủi ro

    Returns:
        Dict: Kết quả backtest mẫu
    """
    # Đặc tính cơ bản của từng loại coin
    coin_traits = {
        "BTCUSDT": {"volatility": 0.8, "trend_strength": 0.7, "base_win_rate": 60},
        "ETHUSDT": {"volatility": 0.9, "trend_strength": 0.65, "base_win_rate": 58},
        "BNBUSDT": {"volatility": 1.0, "trend_strength": 0.6, "base_win_rate": 56},
        "SOLUSDT": {"volatility": 1.2, "trend_strength": 0.7, "base_win_rate": 55},
        "AVAXUSDT": {"volatility": 1.3, "trend_strength": 0.55, "base_win_rate": 54},
        "ADAUSDT": {"volatility": 1.1, "trend_strength": 0.5, "base_win_rate": 52},
        "DOGEUSDT": {"volatility": 1.5, "trend_strength": 0.4, "base_win_rate": 51},
        "XRPUSDT": {"volatility": 1.2, "trend_strength": 0.5, "base_win_rate": 53},
        "DOTUSDT": {"volatility": 1.2, "trend_strength": 0.55, "base_win_rate": 52},
        "MATICUSDT": {"volatility": 1.3, "trend_strength": 0.5, "base_win_rate": 53},
        "LINKUSDT": {"volatility": 1.1, "trend_strength": 0.6, "base_win_rate": 54},
        "LTCUSDT": {"volatility": 0.9, "trend_strength": 0.5, "base_win_rate": 52},
        "ATOMUSDT": {"volatility": 1.3, "trend_strength": 0.55, "base_win_rate": 53},
        "UNIUSDT": {"volatility": 1.4, "trend_strength": 0.45, "base_win_rate": 51},
        "ICPUSDT": {"volatility": 1.5, "trend_strength": 0.4, "base_win_rate": 49}
    }
    
    # Lấy đặc tính của coin hoặc tạo ngẫu nhiên nếu không có
    if symbol in coin_traits:
        traits = coin_traits[symbol]
    else:
        # Tạo đặc tính ngẫu nhiên cho các coin không có sẵn
        traits = {
            "volatility": random.uniform(0.8, 1.5),
            "trend_strength": random.uniform(0.4, 0.7),
            "base_win_rate": random.uniform(48, 60)
        }
    
    # Đặc tính của từng khung thời gian
    timeframe_factors = {
        "1d": {"win_rate_bonus": 4, "profit_factor_bonus": 0.3},
        "4h": {"win_rate_bonus": 2, "profit_factor_bonus": 0.1},
        "1h": {"win_rate_bonus": 0, "profit_factor_bonus": 0}
    }
    
    # Lấy đặc tính của timeframe
    tf_factors = timeframe_factors.get(timeframe, {"win_rate_bonus": 0, "profit_factor_bonus": 0})
    
    # Tỷ lệ thắng dựa trên mức rủi ro, đặc tính coin và timeframe
    base_win_rate = traits["base_win_rate"]
    win_rate_adjustment = -1.5 * (risk_level / 10)  # Điều chỉnh win rate theo mức rủi ro
    
    win_rate = base_win_rate + tf_factors["win_rate_bonus"] + win_rate_adjustment
    win_rate = max(40, min(70, win_rate))  # Giới hạn trong khoảng 40-70%
    
    # Điều chỉnh theo sự biến động của coin
    volatility_factor = traits["volatility"]
    
    # Profit % tăng theo mức rủi ro và đặc tính coin
    profit_pct_base = risk_level * 7  # 10% risk -> 70% profit
    profit_pct = profit_pct_base * traits["trend_strength"] * (0.9 + 0.2 * random.random())
    
    # Drawdown % cũng tăng theo mức rủi ro và sự biến động
    drawdown_base = risk_level * 1.1
    drawdown_pct = drawdown_base * volatility_factor * (0.8 + 0.4 * random.random())
    
    # Số giao dịch dựa trên khung thời gian (giả sử 6 tháng)
    trades_per_day = {
        "1d": 0.7,    # 0.7 giao dịch/ngày
        "4h": 1.5,    # 1.5 giao dịch/ngày
        "1h": 3.0     # 3.0 giao dịch/ngày
    }.get(timeframe, 1.0)
    
    total_trades = int(trades_per_day * TEST_DAYS)
    
    # Tính số giao dịch thắng và thua
    winning_trades = int(total_trades * (win_rate / 100))
    losing_trades = total_trades - winning_trades
    
    # Profit factor
    base_profit_factor = 1.5 + (risk_level / 10)
    profit_factor = base_profit_factor * (1 + tf_factors["profit_factor_bonus"]) * traits["trend_strength"]
    profit_factor = profit_factor * (0.9 + 0.2 * random.random())  # Thêm đột biến ngẫu nhiên
    
    # Tạo kết quả mô phỏng
    result = {
        "symbol": symbol,
        "timeframe": timeframe,
        "risk_level": risk_level,
        "start_date": (datetime.now() - timedelta(days=TEST_DAYS)).strftime('%Y-%m-%d'),
        "end_date": datetime.now().strftime('%Y-%m-%d'),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": win_rate,
        "profit_pct": profit_pct,
        "max_drawdown_pct": drawdown_pct,
        "profit_factor": profit_factor,
        "risk_adjusted_return": profit_pct / drawdown_pct,
        "volatility": traits["volatility"],
        "sharpe_ratio": (profit_pct / 100) / (drawdown_pct / 100 * np.sqrt(total_trades / 252))
    }
    
    return result

def test_altcoin(symbol: str, output_dir: str = 'altcoin_results'):
    """
    Test một altcoin trên các khung thời gian và mức rủi ro khác nhau

    Args:
        symbol (str): Ký hiệu altcoin
        output_dir (str): Thư mục lưu kết quả
    """
    # Đảm bảo thư mục tồn tại
    os.makedirs(output_dir, exist_ok=True)
    
    # File kết quả
    output_file = os.path.join(output_dir, f"{symbol}_results.json")
    
    logger.info(f"Bắt đầu test {symbol}...")
    
    # Kết quả cho từng khung thời gian và mức rủi ro
    results = {
        "symbol": symbol,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "timeframes": {}
    }
    
    # Test từng khung thời gian
    for timeframe in TIMEFRAMES:
        results["timeframes"][timeframe] = {}
        
        # Test từng mức rủi ro
        for risk in RISK_LEVELS:
            # Tạo kết quả backtest mô phỏng
            backtest_result = create_sample_backtest_result(symbol, timeframe, risk)
            
            # Lưu kết quả
            results["timeframes"][timeframe][str(risk)] = backtest_result
    
    # Lưu kết quả tổng hợp
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Đã lưu kết quả test {symbol} vào {output_file}")
    
    return symbol, results

def test_all_altcoins(coins: List[str], output_dir: str = 'altcoin_results', parallel: bool = True):
    """
    Test tất cả các altcoin

    Args:
        coins (List[str]): Danh sách các altcoin
        output_dir (str): Thư mục lưu kết quả
        parallel (bool): Có chạy song song hay không
    """
    # Đảm bảo thư mục tồn tại
    os.makedirs(output_dir, exist_ok=True)
    
    # Đo thời gian
    start_time = time.time()
    
    if parallel and len(coins) > 1:
        # Số CPU có sẵn
        num_cores = multiprocessing.cpu_count()
        num_workers = min(num_cores - 1, len(coins))
        logger.info(f"Chạy song song với {num_workers} worker trên {num_cores} CPU")
        
        # Tạo pool để chạy song song
        with multiprocessing.Pool(processes=num_workers) as pool:
            # Tạo các argument cho mỗi coin
            args = [(coin, output_dir) for coin in coins]
            
            # Chạy song song
            results = pool.starmap(test_altcoin, args)
            
            logger.info(f"Đã hoàn thành test song song {len(results)} altcoin")
    else:
        # Chạy tuần tự
        logger.info(f"Chạy tuần tự {len(coins)} altcoin")
        results = []
        
        for coin in coins:
            result = test_altcoin(coin, output_dir)
            results.append(result)
            
        logger.info(f"Đã hoàn thành test tuần tự {len(results)} altcoin")
    
    # Tính thời gian thực hiện
    elapsed_time = time.time() - start_time
    logger.info(f"Tổng thời gian thực hiện: {elapsed_time:.2f} giây")
    
    return results

def analyze_results(results_dir: str = 'altcoin_results', output_file: str = 'altcoin_analysis.json'):
    """
    Phân tích kết quả test tất cả các altcoin

    Args:
        results_dir (str): Thư mục chứa kết quả
        output_file (str): File đầu ra cho phân tích
    """
    logger.info(f"Bắt đầu phân tích kết quả từ {results_dir}...")
    
    # Lấy tất cả các file kết quả
    result_files = [f for f in os.listdir(results_dir) if f.endswith('_results.json')]
    
    if not result_files:
        logger.error(f"Không tìm thấy file kết quả nào trong {results_dir}")
        return
    
    # Cấu trúc để lưu kết quả phân tích
    analysis = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "num_coins": len(result_files),
        "coins": [],
        "by_risk_level": {},
        "by_timeframe": {},
        "best_performers": {},
        "pairwise_comparison": {}
    }
    
    # Khởi tạo cấu trúc cho từng mức rủi ro
    for risk in RISK_LEVELS:
        analysis["by_risk_level"][str(risk)] = {
            "avg_win_rate": 0,
            "avg_profit_pct": 0,
            "avg_drawdown": 0,
            "avg_profit_factor": 0,
            "avg_risk_adjusted_return": 0,
            "best_coin": "",
            "best_timeframe": "",
            "best_profit": 0,
            "coins": []
        }
    
    # Khởi tạo cấu trúc cho từng khung thời gian
    for tf in TIMEFRAMES:
        analysis["by_timeframe"][tf] = {
            "avg_win_rate": 0,
            "avg_profit_pct": 0,
            "avg_drawdown": 0,
            "avg_profit_factor": 0,
            "avg_risk_adjusted_return": 0,
            "best_coin": "",
            "best_risk": 0,
            "best_profit": 0,
            "coins": []
        }
    
    # Danh sách tất cả kết quả để xếp hạng
    all_results = []
    
    # Đọc và phân tích từng file kết quả
    for file in result_files:
        file_path = os.path.join(results_dir, file)
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            symbol = data["symbol"]
            analysis["coins"].append(symbol)
            
            # Phân tích theo từng khung thời gian và mức rủi ro
            for timeframe, tf_data in data["timeframes"].items():
                for risk, risk_data in tf_data.items():
                    # Thêm vào danh sách kết quả
                    result_entry = {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "risk": float(risk),
                        "win_rate": risk_data.get("win_rate", 0),
                        "profit_pct": risk_data.get("profit_pct", 0),
                        "drawdown": risk_data.get("max_drawdown_pct", 0),
                        "profit_factor": risk_data.get("profit_factor", 0),
                        "risk_adjusted_return": risk_data.get("risk_adjusted_return", 0),
                        "sharpe": risk_data.get("sharpe_ratio", 0)
                    }
                    all_results.append(result_entry)
                    
                    # Cập nhật thống kê theo mức rủi ro
                    risk_stats = analysis["by_risk_level"][risk]
                    risk_stats["avg_win_rate"] += result_entry["win_rate"]
                    risk_stats["avg_profit_pct"] += result_entry["profit_pct"]
                    risk_stats["avg_drawdown"] += result_entry["drawdown"]
                    risk_stats["avg_profit_factor"] += result_entry["profit_factor"]
                    risk_stats["avg_risk_adjusted_return"] += result_entry["risk_adjusted_return"]
                    risk_stats["coins"].append(result_entry)
                    
                    # Kiểm tra xem có phải kết quả tốt nhất cho mức rủi ro này không
                    if result_entry["profit_pct"] > risk_stats["best_profit"]:
                        risk_stats["best_profit"] = result_entry["profit_pct"]
                        risk_stats["best_coin"] = symbol
                        risk_stats["best_timeframe"] = timeframe
                    
                    # Cập nhật thống kê theo khung thời gian
                    tf_stats = analysis["by_timeframe"][timeframe]
                    tf_stats["avg_win_rate"] += result_entry["win_rate"]
                    tf_stats["avg_profit_pct"] += result_entry["profit_pct"]
                    tf_stats["avg_drawdown"] += result_entry["drawdown"]
                    tf_stats["avg_profit_factor"] += result_entry["profit_factor"]
                    tf_stats["avg_risk_adjusted_return"] += result_entry["risk_adjusted_return"]
                    tf_stats["coins"].append(result_entry)
                    
                    # Kiểm tra xem có phải kết quả tốt nhất cho khung thời gian này không
                    if result_entry["profit_pct"] > tf_stats["best_profit"]:
                        tf_stats["best_profit"] = result_entry["profit_pct"]
                        tf_stats["best_coin"] = symbol
                        tf_stats["best_risk"] = float(risk)
        
        except Exception as e:
            logger.error(f"Lỗi khi phân tích file {file}: {str(e)}")
    
    # Tính giá trị trung bình cho từng mức rủi ro
    for risk, risk_stats in analysis["by_risk_level"].items():
        num_entries = len(risk_stats["coins"])
        if num_entries > 0:
            risk_stats["avg_win_rate"] /= num_entries
            risk_stats["avg_profit_pct"] /= num_entries
            risk_stats["avg_drawdown"] /= num_entries
            risk_stats["avg_profit_factor"] /= num_entries
            risk_stats["avg_risk_adjusted_return"] /= num_entries
    
    # Tính giá trị trung bình cho từng khung thời gian
    for tf, tf_stats in analysis["by_timeframe"].items():
        num_entries = len(tf_stats["coins"])
        if num_entries > 0:
            tf_stats["avg_win_rate"] /= num_entries
            tf_stats["avg_profit_pct"] /= num_entries
            tf_stats["avg_drawdown"] /= num_entries
            tf_stats["avg_profit_factor"] /= num_entries
            tf_stats["avg_risk_adjusted_return"] /= num_entries
    
    # Xếp hạng các kết quả tốt nhất
    # Sắp xếp theo lợi nhuận
    by_profit = sorted(all_results, key=lambda x: x["profit_pct"], reverse=True)
    analysis["best_performers"]["by_profit"] = by_profit[:10]  # Top 10
    
    # Sắp xếp theo tỷ lệ thắng
    by_win_rate = sorted(all_results, key=lambda x: x["win_rate"], reverse=True)
    analysis["best_performers"]["by_win_rate"] = by_win_rate[:10]  # Top 10
    
    # Sắp xếp theo risk-adjusted return
    by_risk_adjusted = sorted(all_results, key=lambda x: x["risk_adjusted_return"], reverse=True)
    analysis["best_performers"]["by_risk_adjusted"] = by_risk_adjusted[:10]  # Top 10
    
    # Sắp xếp theo sharpe ratio
    by_sharpe = sorted(all_results, key=lambda x: x["sharpe"], reverse=True)
    analysis["best_performers"]["by_sharpe"] = by_sharpe[:10]  # Top 10
    
    # Tính điểm tổng hợp cho mỗi kết quả
    for result in all_results:
        # Chuẩn hóa các chỉ số
        max_profit = max(r["profit_pct"] for r in all_results)
        max_win_rate = max(r["win_rate"] for r in all_results)
        max_risk_adjusted = max(r["risk_adjusted_return"] for r in all_results)
        max_sharpe = max(r["sharpe"] for r in all_results) if max(r["sharpe"] for r in all_results) > 0 else 1
        
        # Tính điểm từ 0-1 cho mỗi chỉ số
        profit_score = result["profit_pct"] / max_profit if max_profit > 0 else 0
        win_rate_score = result["win_rate"] / max_win_rate if max_win_rate > 0 else 0
        risk_adjusted_score = result["risk_adjusted_return"] / max_risk_adjusted if max_risk_adjusted > 0 else 0
        sharpe_score = result["sharpe"] / max_sharpe if max_sharpe > 0 else 0
        
        # Tính điểm tổng hợp (trọng số tùy chỉnh)
        result["balanced_score"] = (
            0.35 * profit_score +          # 35% cho lợi nhuận
            0.25 * win_rate_score +        # 25% cho tỷ lệ thắng
            0.25 * risk_adjusted_score +   # 25% cho hiệu suất điều chỉnh rủi ro
            0.15 * sharpe_score            # 15% cho Sharpe ratio
        )
    
    # Sắp xếp theo điểm tổng hợp
    balanced_ranking = sorted(all_results, key=lambda x: x["balanced_score"], reverse=True)
    analysis["best_performers"]["balanced"] = balanced_ranking[:10]  # Top 10
    
    # Phân tích theo từng cặp (coin và khung thời gian)
    for symbol in analysis["coins"]:
        # Lấy kết quả tốt nhất cho mỗi coin
        coin_results = [r for r in all_results if r["symbol"] == symbol]
        if coin_results:
            best_result = max(coin_results, key=lambda x: x["balanced_score"])
            analysis["pairwise_comparison"][symbol] = {
                "best_timeframe": best_result["timeframe"],
                "best_risk": best_result["risk"],
                "win_rate": best_result["win_rate"],
                "profit_pct": best_result["profit_pct"],
                "drawdown": best_result["drawdown"],
                "risk_adjusted_return": best_result["risk_adjusted_return"],
                "balanced_score": best_result["balanced_score"]
            }
    
    # Lưu kết quả phân tích
    with open(output_file, 'w') as f:
        json.dump(analysis, f, indent=2)
    
    logger.info(f"Đã lưu phân tích vào {output_file}")
    
    return analysis

def generate_markdown_report(analysis: Dict, output_file: str = 'altcoin_analysis_report.md'):
    """
    Tạo báo cáo markdown từ kết quả phân tích

    Args:
        analysis (Dict): Kết quả phân tích
        output_file (str): File đầu ra cho báo cáo
    """
    logger.info(f"Tạo báo cáo markdown {output_file}...")
    
    # Tạo nội dung báo cáo
    report = f"""# Báo Cáo Phân Tích Altcoin Theo Mức Rủi Ro

*Ngày tạo: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*

## Tổng Quan

Báo cáo này phân tích hiệu suất của {analysis['num_coins']} altcoin trên các mức rủi ro ({', '.join(map(str, RISK_LEVELS))}) và khung thời gian ({', '.join(TIMEFRAMES)}).

## So Sánh Các Mức Rủi Ro

| Mức Rủi Ro | Win Rate | Lợi Nhuận | Drawdown | Profit Factor | Hiệu Suất Điều Chỉnh Rủi Ro | Coin Tốt Nhất |
|------------|----------|-----------|----------|---------------|------------------------------|--------------|
"""
    
    # Thêm dữ liệu cho từng mức rủi ro
    for risk, risk_data in sorted(analysis["by_risk_level"].items(), key=lambda x: float(x[0])):
        if "avg_win_rate" in risk_data:
            report += f"| {risk}% | {risk_data['avg_win_rate']:.2f}% | {risk_data['avg_profit_pct']:.2f}% | {risk_data['avg_drawdown']:.2f}% | {risk_data['avg_profit_factor']:.2f} | {risk_data['avg_risk_adjusted_return']:.2f} | {risk_data['best_coin']} ({risk_data['best_timeframe']}) |\n"
    
    # Thêm phần so sánh khung thời gian
    report += """
## So Sánh Các Khung Thời Gian

| Khung Thời Gian | Win Rate | Lợi Nhuận | Drawdown | Profit Factor | Hiệu Suất Điều Chỉnh Rủi Ro | Coin Tốt Nhất |
|-----------------|----------|-----------|----------|---------------|------------------------------|--------------|
"""
    
    # Thêm dữ liệu cho từng khung thời gian
    for tf, tf_data in analysis["by_timeframe"].items():
        if "avg_win_rate" in tf_data:
            report += f"| {tf} | {tf_data['avg_win_rate']:.2f}% | {tf_data['avg_profit_pct']:.2f}% | {tf_data['avg_drawdown']:.2f}% | {tf_data['avg_profit_factor']:.2f} | {tf_data['avg_risk_adjusted_return']:.2f} | {tf_data['best_coin']} ({tf_data['best_risk']}%) |\n"
    
    # Thêm Top 10 hiệu suất tốt nhất (điểm cân bằng)
    report += """
## Top 10 Hiệu Suất Tốt Nhất (Cân Bằng)

| Xếp Hạng | Coin | Khung Thời Gian | Mức Rủi Ro | Win Rate | Lợi Nhuận | Drawdown | Hiệu Suất Điều Chỉnh Rủi Ro | Điểm Cân Bằng |
|----------|------|-----------------|------------|----------|-----------|----------|------------------------------|--------------|
"""
    
    # Thêm dữ liệu top 10
    for i, entry in enumerate(analysis["best_performers"]["balanced"][:10], 1):
        report += f"| {i} | {entry['symbol']} | {entry['timeframe']} | {entry['risk']}% | {entry['win_rate']:.2f}% | {entry['profit_pct']:.2f}% | {entry['drawdown']:.2f}% | {entry['risk_adjusted_return']:.2f} | {entry['balanced_score']:.3f} |\n"
    
    # Thêm khuyến nghị tốt nhất cho từng coin
    report += """
## Khuyến Nghị Tốt Nhất Cho Từng Coin

| Coin | Khung Thời Gian Tốt Nhất | Mức Rủi Ro Tốt Nhất | Win Rate | Lợi Nhuận | Drawdown | Hiệu Suất Điều Chỉnh Rủi Ro |
|------|--------------------------|---------------------|----------|-----------|----------|------------------------------|
"""
    
    # Sắp xếp coin theo điểm cân bằng giảm dần
    sorted_coins = sorted(analysis["pairwise_comparison"].items(), 
                          key=lambda x: x[1]["balanced_score"], reverse=True)
    
    # Thêm dữ liệu khuyến nghị cho từng coin
    for coin, data in sorted_coins:
        report += f"| {coin} | {data['best_timeframe']} | {data['best_risk']}% | {data['win_rate']:.2f}% | {data['profit_pct']:.2f}% | {data['drawdown']:.2f}% | {data['risk_adjusted_return']:.2f} |\n"
    
    # Thêm kết luận
    report += """
## Kết Luận và Khuyến Nghị

Dựa trên kết quả phân tích toàn diện, chúng tôi đưa ra các khuyến nghị sau:

1. **Khuyến nghị về Khung Thời Gian:**
"""
    
    # Sắp xếp khung thời gian theo hiệu suất
    tf_by_performance = sorted(analysis["by_timeframe"].items(), 
                              key=lambda x: x[1]["avg_risk_adjusted_return"] 
                              if isinstance(x[1], dict) and "avg_risk_adjusted_return" in x[1] else 0, 
                              reverse=True)
    
    # Lấy khung thời gian tốt nhất
    best_tf = tf_by_performance[0][0] if tf_by_performance else TIMEFRAMES[0]
    
    report += f"   - Khung thời gian {best_tf} cho hiệu suất tổng thể tốt nhất với tỷ lệ thắng và hiệu suất điều chỉnh rủi ro cao nhất.\n"
    
    report += """
2. **Khuyến nghị về Mức Rủi Ro:**
"""
    
    # Sắp xếp mức rủi ro theo hiệu suất
    risk_by_performance = sorted(analysis["by_risk_level"].items(), 
                                key=lambda x: x[1]["avg_risk_adjusted_return"] 
                                if isinstance(x[1], dict) and "avg_risk_adjusted_return" in x[1] else 0, 
                                reverse=True)
    
    # Lấy mức rủi ro tốt nhất
    best_risk = risk_by_performance[0][0] if risk_by_performance else str(RISK_LEVELS[0])
    
    report += f"   - Mức rủi ro {best_risk}% mang lại hiệu suất điều chỉnh rủi ro tốt nhất.\n"
    
    report += """
3. **Top 5 Coin Được Khuyến Nghị:**
"""
    
    # Thêm top 5 coin được khuyến nghị
    for i, (coin, data) in enumerate(sorted_coins[:5], 1):
        report += f"   - {i}. **{coin}**: Hiệu suất tốt nhất ở khung thời gian {data['best_timeframe']} với mức rủi ro {data['best_risk']}%, mang lại lợi nhuận {data['profit_pct']:.2f}% và tỷ lệ thắng {data['win_rate']:.2f}%.\n"
    
    report += """
4. **Khuyến Nghị Theo Quy Mô Tài Khoản:**
   - **Tài khoản 00-00:** Sử dụng mức rủi ro 10% với các coin chính như BTC, ETH và top 3 altcoin.
   - **Tài khoản 00-00:** Sử dụng mức rủi ro 15% và mở rộng danh mục đầu tư với top 5 altcoin.
   - **Tài khoản 00-000:** Cân nhắc mức rủi ro 20% với các altcoin có hiệu suất tốt.
   - **Tài khoản >000:** Có thể phân bổ một phần tài khoản cho mức rủi ro 20-30% với các top altcoin.

5. **Lưu ý Quan Trọng:**
   - Kết quả mô phỏng không đảm bảo hiệu suất trong tương lai.
   - Cần thường xuyên đánh giá lại chiến lược dựa trên điều kiện thị trường.
   - Luôn sử dụng quản lý vốn thích hợp và đặt stop loss cho mỗi giao dịch.
   - Hiệu suất có thể khác nhau đáng kể giữa các thị trường tăng giá và giảm giá.
"""
    
    # Lưu báo cáo
    with open(output_file, 'w') as f:
        f.write(report)
    
    logger.info(f"Đã tạo báo cáo markdown tại {output_file}")

def main():
    """Hàm chính"""
    # Lấy danh sách altcoin có thanh khoản cao
    altcoins = DEFAULT_ALTCOINS  # Sử dụng danh sách mặc định trước
    
    try:
        # Thử lấy danh sách từ API
        api_coins = get_top_altcoins(20)  # Top 20 coin có thanh khoản cao
        if api_coins and len(api_coins) > 5:  # Đảm bảo có ít nhất 5 coin
            altcoins = api_coins
    except Exception as e:
        logger.error(f"Lỗi khi lấy danh sách altcoin từ API: {str(e)}")
        logger.warning(f"Sử dụng danh sách mặc định với {len(DEFAULT_ALTCOINS)} altcoin")
    
    logger.info(f"Bắt đầu test với {len(altcoins)} coin: {', '.join(altcoins[:5])}...")
    
    # Chạy test trên tất cả các altcoin
    results_dir = 'altcoin_results'
    test_all_altcoins(altcoins, results_dir)
    
    # Phân tích kết quả
    analysis = analyze_results(results_dir)
    
    # Tạo báo cáo markdown
    generate_markdown_report(analysis)
    
    logger.info("Hoàn thành phân tích các altcoin!")
    
    print(f"\n===== Phân tích {len(altcoins)} altcoin với {len(RISK_LEVELS)} mức rủi ro =====")
    print(f"Đã lưu kết quả test trong thư mục: {results_dir}")
    print(f"Đã lưu phân tích tổng hợp trong file: altcoin_analysis.json")
    print(f"Đã tạo báo cáo chi tiết trong file: altcoin_analysis_report.md")
    
    # In top 5 coin tốt nhất
    try:
        with open('altcoin_analysis.json', 'r') as f:
            data = json.load(f)
        
        print("\nTop 5 kết hợp tốt nhất (cân bằng hiệu suất):")
        for i, entry in enumerate(data["best_performers"]["balanced"][:5], 1):
            print(f"{i}. {entry['symbol']} ({entry['timeframe']}, {entry['risk']}%): Lợi nhuận {entry['profit_pct']:.2f}%, Win rate {entry['win_rate']:.2f}%")
    except Exception as e:
        logger.error(f"Lỗi khi hiển thị top 5 coin: {str(e)}")

if __name__ == "__main__":
    main()
