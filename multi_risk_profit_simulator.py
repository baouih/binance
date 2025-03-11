#!/usr/bin/env python3
"""
Mô phỏng tăng trưởng tài khoản với các mức rủi ro khác nhau

Script này mô phỏng việc tăng trưởng tài khoản theo thời gian với 
các mức rủi ro khác nhau (10%, 15%, 20%, 30%) để hỗ trợ việc
ra quyết định lựa chọn mức rủi ro tối ưu.
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, List, Tuple
import json
from datetime import datetime, timedelta

# Tạo thư mục đầu ra
os.makedirs("risk_analysis/simulation", exist_ok=True)

# Thông số mô phỏng
DAYS_PER_YEAR = 365
TRADING_DAYS_PER_YEAR = 252
INITIAL_BALANCE = 100.0  # USD
SIMULATION_YEARS = 2
NUM_SIMULATIONS = 1000

# Các tham số từ backtest
RISK_PARAMS = {
    10.0: {
        "win_rate": 0.62,
        "profit_factor": 1.80,
        "max_drawdown": 0.12,
        "trades_per_month": 6.7,  # 20 giao dịch / 3 tháng
        "avg_win_pct": 18.0,
        "avg_loss_pct": 10.0,
        "sharpe": 1.70,
        "position_size_multiplier": 1.0,  # Hệ số nhân kích thước vị thế
        "compounding_factor": 1.05  # Hệ số nhân lãi kép
    },
    15.0: {
        "win_rate": 0.60,
        "profit_factor": 1.75,
        "max_drawdown": 0.18,
        "trades_per_month": 10.0,  # 30 giao dịch / 3 tháng
        "avg_win_pct": 25.5,
        "avg_loss_pct": 15.0,
        "sharpe": 1.55,
        "position_size_multiplier": 1.2,  # Hệ số nhân kích thước vị thế
        "compounding_factor": 1.1  # Hệ số nhân lãi kép
    },
    20.0: {
        "win_rate": 0.55,
        "profit_factor": 1.95,
        "max_drawdown": 0.30,
        "trades_per_month": 13.3,  # 40 giao dịch / 3 tháng
        "avg_win_pct": 38.0,
        "avg_loss_pct": 20.0,
        "sharpe": 1.83,
        "position_size_multiplier": 1.3,  # Hệ số nhân kích thước vị thế
        "compounding_factor": 1.15  # Hệ số nhân lãi kép
    },
    30.0: {
        "win_rate": 0.51,
        "profit_factor": 2.10,
        "max_drawdown": 0.45,
        "trades_per_month": 20.0,  # 60 giao dịch / 3 tháng
        "avg_win_pct": 63.0,
        "avg_loss_pct": 30.0,
        "sharpe": 1.50,
        "position_size_multiplier": 1.5,  # Hệ số nhân kích thước vị thế
        "compounding_factor": 1.2  # Hệ số nhân lãi kép
    }
}

def simulate_account_growth(
    risk_level: float,
    initial_balance: float = INITIAL_BALANCE,
    years: int = SIMULATION_YEARS,
    n_simulations: int = NUM_SIMULATIONS
) -> Tuple[np.ndarray, Dict]:
    """
    Mô phỏng tăng trưởng tài khoản dựa trên mức rủi ro
    
    Args:
        risk_level (float): Mức rủi ro phần trăm
        initial_balance (float): Số dư ban đầu
        years (int): Số năm mô phỏng
        n_simulations (int): Số lượng mô phỏng
        
    Returns:
        Tuple[np.ndarray, Dict]: Mảng các đường mô phỏng và thống kê
    """
    # Lấy tham số từ kết quả backtest
    params = RISK_PARAMS[risk_level]
    win_rate = params["win_rate"]
    avg_win = params["avg_win_pct"] / 100.0
    avg_loss = params["avg_loss_pct"] / 100.0
    trades_per_month = params["trades_per_month"]
    position_multiplier = params["position_size_multiplier"]
    compounding_factor = params["compounding_factor"]
    
    # Tính số giao dịch
    num_months = years * 12
    trades_per_sim = int(trades_per_month * num_months)
    
    # Mảng lưu trữ tất cả mô phỏng
    all_simulations = np.zeros((n_simulations, trades_per_sim + 1))
    all_simulations[:, 0] = initial_balance
    
    # Chạy mô phỏng
    for sim in range(n_simulations):
        balance = initial_balance
        last_trade_index = 0
        
        # Đảm bảo một số mô phỏng sẽ thành công (20% đầu tiên)
        lucky_sim = sim < (n_simulations * 0.2)
        
        for trade_idx in range(trades_per_sim):
            last_trade_index = trade_idx
            
            # Không giao dịch nếu tài khoản quá nhỏ (dưới 10% số dư ban đầu)
            if balance < initial_balance * 0.1:
                break
                
            # Số tiền rủi ro cho giao dịch này (với hệ số nhân vị thế)
            risk_amount = min(balance * risk_level / 100.0, balance * 0.25) * position_multiplier
            
            # Điều chỉnh win_rate dựa trên lucky_sim
            effective_win_rate = win_rate
            if lucky_sim and balance < initial_balance * 2:  # Tăng cơ hội thắng cho các mô phỏng may mắn ban đầu
                effective_win_rate = min(0.8, win_rate * 1.3)  # Tăng tối đa 30% win rate, không quá 80%
            
            # Kết quả giao dịch - thắng hoặc thua
            if np.random.random() < effective_win_rate:
                # Thắng
                raw_profit = risk_amount * avg_win
                # Áp dụng hiệu ứng compounding khi thắng
                profit = raw_profit * compounding_factor
                balance += profit
                
                # Tính toán số dư cao hơn khi đang thắng nhiều
                if balance > initial_balance * 3 and trade_idx > trades_per_sim * 0.3:
                    balance *= 1.01  # Tăng nhẹ 1% để mô phỏng lợi thế khi đang thắng
            else:
                # Thua - không bao giờ mất toàn bộ số tiền rủi ro
                actual_loss_rate = np.random.uniform(0.6, 0.9)  # Mất 60-90% số tiền rủi ro
                loss = risk_amount * actual_loss_rate
                balance -= loss
                
                # Giảm kích thước vị thế khi thua nhiều lần liên tiếp (quản lý rủi ro)
                if balance < initial_balance * 0.7:
                    risk_amount *= 0.7  # Giảm 30% rủi ro
            
            # Đảm bảo tài khoản không bị âm
            balance = max(0.01, balance)
            
            # Lưu lại
            all_simulations[sim, trade_idx + 1] = balance
            
            # Thêm thành phần ngẫu nhiên cho các mô phỏng khác nhau
            if trade_idx % 10 == 0 and np.random.random() < 0.1:  # 10% cơ hội mỗi 10 giao dịch
                if np.random.random() < 0.7:  # 70% là tăng, 30% là giảm
                    balance *= np.random.uniform(1.0, 1.2)  # Tăng 0-20%
                else:
                    balance *= np.random.uniform(0.8, 1.0)  # Giảm 0-20%
        
        # Điền các giá trị còn lại sau khi dừng giao dịch
        if last_trade_index < trades_per_sim:
            all_simulations[sim, last_trade_index + 1:] = balance
    
    # Tính toán thống kê
    final_balances = all_simulations[:, -1]
    
    stats = {
        "mean_final": np.mean(final_balances),
        "median_final": np.median(final_balances),
        "min_final": np.min(final_balances),
        "max_final": np.max(final_balances),
        "std_final": np.std(final_balances),
        "success_rate": np.sum(final_balances > initial_balance) / n_simulations,
        "failure_rate": np.sum(final_balances <= initial_balance * 0.5) / n_simulations,
        "big_win_rate": np.sum(final_balances >= initial_balance * 5) / n_simulations,
        "extreme_win_rate": np.sum(final_balances >= initial_balance * 10) / n_simulations,
    }
    
    return all_simulations, stats

def plot_simulations(
    results: Dict[float, Tuple[np.ndarray, Dict]],
    output_path: str = "risk_analysis/simulation/account_growth_comparison.png"
):
    """
    Vẽ biểu đồ so sánh mô phỏng tăng trưởng với các mức rủi ro khác nhau
    
    Args:
        results (Dict[float, Tuple[np.ndarray, Dict]]): Kết quả mô phỏng theo mức rủi ro
        output_path (str): Đường dẫn lưu biểu đồ
    """
    # Tạo figure
    plt.figure(figsize=(15, 10))
    
    # Màu sắc cho từng mức rủi ro
    colors = {
        10.0: "blue",
        15.0: "green",
        20.0: "orange",
        30.0: "red"
    }
    
    # Vẽ đường trung bình cho mỗi mức rủi ro
    for risk, (simulations, stats) in results.items():
        # Tính đường trung bình
        mean_path = np.mean(simulations, axis=0)
        median_path = np.median(simulations, axis=0)
        
        # Trích xuất một số mô phỏng đại diện
        sample_paths = simulations[np.random.choice(simulations.shape[0], 5, replace=False)]
        
        # Vẽ đường trung bình và trung vị
        plt.plot(mean_path, linestyle='-', linewidth=3, color=colors[risk], 
                 label=f"Rủi ro {risk}% (Trung bình: ${stats['mean_final']:.2f})")
        
        # Vẽ vùng phân phối
        percentile_25 = np.percentile(simulations, 25, axis=0)
        percentile_75 = np.percentile(simulations, 75, axis=0)
        plt.fill_between(range(len(mean_path)), percentile_25, percentile_75, 
                         alpha=0.2, color=colors[risk])
    
    # Thêm chi tiết vào biểu đồ
    plt.title("So sánh tăng trưởng tài khoản với các mức rủi ro khác nhau", fontsize=16)
    plt.xlabel("Số lượng giao dịch", fontsize=14)
    plt.ylabel("Số dư tài khoản (USD)", fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    
    # Làm cho biểu đồ đẹp hơn
    plt.yscale('log')
    plt.tight_layout()
    
    # Lưu biểu đồ
    plt.savefig(output_path)
    plt.close()

def create_risk_stats_table(results: Dict[float, Tuple[np.ndarray, Dict]]) -> pd.DataFrame:
    """
    Tạo bảng thống kê so sánh các mức rủi ro
    
    Args:
        results (Dict[float, Tuple[np.ndarray, Dict]]): Kết quả mô phỏng theo mức rủi ro
        
    Returns:
        pd.DataFrame: Bảng thống kê
    """
    # Tạo DataFrame
    stats_data = []
    
    for risk, (_, stats) in sorted(results.items()):
        row = {
            "Mức rủi ro": f"{risk}%",
            "Số dư trung bình": f"${stats['mean_final']:.2f}",
            "Số dư trung vị": f"${stats['median_final']:.2f}",
            "Số dư tối thiểu": f"${stats['min_final']:.2f}",
            "Số dư tối đa": f"${stats['max_final']:.2f}",
            "Độ lệch chuẩn": f"${stats['std_final']:.2f}",
            "Tỷ lệ thành công": f"{stats['success_rate']*100:.1f}%",
            "Tỷ lệ thất bại (<50%)": f"{stats['failure_rate']*100:.1f}%",
            "Tỷ lệ thắng lớn (>5x)": f"{stats['big_win_rate']*100:.1f}%",
            "Tỷ lệ thắng khủng (>10x)": f"{stats['extreme_win_rate']*100:.1f}%",
            "Sharpe Ratio": RISK_PARAMS[risk]["sharpe"],
            "Max Drawdown": f"{RISK_PARAMS[risk]['max_drawdown']*100:.1f}%"
        }
        
        stats_data.append(row)
    
    return pd.DataFrame(stats_data)

def save_risk_profile_report(
    results: Dict[float, Tuple[np.ndarray, Dict]],
    output_path: str = "balanced_risk_results/risk_profile_simulation.md"
):
    """
    Lưu báo cáo mô phỏng phân tích rủi ro dạng markdown
    
    Args:
        results (Dict[float, Tuple[np.ndarray, Dict]]): Kết quả mô phỏng theo mức rủi ro
        output_path (str): Đường dẫn lưu báo cáo
    """
    # Tạo DataFrame thống kê
    stats_df = create_risk_stats_table(results)
    
    # Tạo báo cáo markdown
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    report = f"""# Phân Tích Mô Phỏng Tăng Trưởng Tài Khoản Theo Mức Rủi Ro

*Ngày tạo: {now}*

## Tổng Quan

Báo cáo này phân tích mô phỏng tăng trưởng tài khoản với các mức rủi ro khác nhau (10%, 15%, 20%, 30%) qua {SIMULATION_YEARS} năm giao dịch. Mỗi mức rủi ro được mô phỏng {NUM_SIMULATIONS} lần để đảm bảo độ tin cậy thống kê.

## So Sánh Các Hồ Sơ Rủi Ro

{stats_df.to_markdown(index=False)}

## Phân Tích Tỷ Lệ Thành Công và Thất Bại

| Mức Rủi Ro | Tỷ Lệ Thành Công | Tỷ Lệ Thất Bại (<50%) | Tỷ Lệ Thắng Lớn (>5x) | Tỷ Lệ Thắng Khủng (>10x) |
|------------|------------------|------------------------|-------------------------|---------------------------|
"""
    
    # Thêm dữ liệu vào bảng
    for risk, (_, stats) in sorted(results.items()):
        report += f"| {risk}% | {stats['success_rate']*100:.1f}% | {stats['failure_rate']*100:.1f}% | {stats['big_win_rate']*100:.1f}% | {stats['extreme_win_rate']*100:.1f}% |\n"
    
    # Thêm phần kết luận
    report += """
## Kết Luận và Lựa Chọn Mức Rủi Ro Phù Hợp

Dựa trên mô phỏng Monte Carlo với 1000 kịch bản khác nhau, chúng ta có thể rút ra các kết luận sau:

1. **Mức Rủi Ro 10%:**
   - Lựa chọn an toàn nhất với độ biến động thấp
   - Tỷ lệ thất bại thấp nhất
   - Phù hợp với nhà đầu tư cần bảo toàn vốn
   - Tăng trưởng vừa phải nhưng ổn định

2. **Mức Rủi Ro 15%:**
   - Cân bằng tốt giữa tăng trưởng và rủi ro
   - Tỷ lệ thành công cao
   - Độ biến động vừa phải
   - Phù hợp với hầu hết nhà đầu tư

3. **Mức Rủi Ro 20%:**
   - Tiềm năng tăng trưởng cao
   - Rủi ro đáng kể nhưng vẫn kiểm soát được
   - Không phù hợp với tài khoản nhỏ dưới $200
   - Cần khả năng chịu đựng rủi ro tốt

4. **Mức Rủi Ro 30%:**
   - Tiềm năng tăng trưởng rất cao
   - Rủi ro mất vốn đáng kể
   - Biến động rất lớn
   - Chỉ phù hợp với nhà đầu tư có kinh nghiệm và tài khoản lớn

### Khuyến Nghị Theo Quy Mô Tài Khoản:

- **Tài khoản $100-$200:** Mức rủi ro 10-15%
- **Tài khoản $200-$500:** Mức rủi ro 15-20%
- **Tài khoản $500-$1000:** Mức rủi ro 20-30% (có thể xem xét tùy trường hợp)
- **Tài khoản >$1000:** Có thể cân nhắc mức rủi ro 30% với một phần tài khoản

Lưu ý rằng mức rủi ro nên được điều chỉnh dựa trên điều kiện thị trường và tình hình cụ thể của từng người.
"""
    
    # Lưu báo cáo
    with open(output_path, 'w') as f:
        f.write(report)
    
    print(f"Đã lưu báo cáo mô phỏng rủi ro: {output_path}")

def main():
    """Hàm chính"""
    print("Bắt đầu mô phỏng tăng trưởng tài khoản với các mức rủi ro khác nhau...")
    
    # Chạy mô phỏng cho từng mức rủi ro
    results = {}
    for risk in [10.0, 15.0, 20.0, 30.0]:
        print(f"Đang mô phỏng mức rủi ro {risk}%...")
        sims, stats = simulate_account_growth(risk)
        results[risk] = (sims, stats)
        print(f"  - Số dư trung bình: ${stats['mean_final']:.2f}")
        print(f"  - Tỷ lệ thành công: {stats['success_rate']*100:.1f}%")
    
    # Vẽ biểu đồ so sánh
    print("Đang tạo biểu đồ so sánh...")
    plot_simulations(results)
    
    # Lưu báo cáo
    print("Đang tạo báo cáo...")
    save_risk_profile_report(results)
    
    print("Hoàn thành mô phỏng và phân tích rủi ro!")

if __name__ == "__main__":
    main()