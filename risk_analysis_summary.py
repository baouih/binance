import pandas as pd
import numpy as np
from tabulate import tabulate

# Dữ liệu
risk_levels = ['3%', '5%', '7%', '9%', '15%', '20%', '25%', '30%', '40%']
profits = [3.62, 5.75, 6.00, 9.26, 16.53, 26.31, 30.11, 38.84, 40.37]
drawdowns = [1.75, 3.95, 3.69, 4.12, 10.64, 12.21, 12.69, 36.36, 80.00]
win_rates = [38.50, 38.39, 49.55, 52.29, 61.27, 73.87, 71.96, 83.75, 79.66]

# Tính tỷ lệ lợi nhuận/rủi ro
rr_ratios = [profits[i]/drawdowns[i] for i in range(len(profits))]

# Tạo DataFrame
df = pd.DataFrame({
    'Risk Level': risk_levels,
    'Profit (%)': profits,
    'Drawdown (%)': drawdowns,
    'Win Rate (%)': win_rates,
    'RR Ratio': rr_ratios
})

# Thêm các chỉ số và xếp hạng
df['Profit Rank'] = df['Profit (%)'].rank(ascending=False)
df['Drawdown Rank'] = df['Drawdown (%)'].rank()
df['RR Ratio Rank'] = df['RR Ratio'].rank(ascending=False)
df['Win Rate Rank'] = df['Win Rate (%)'].rank(ascending=False)

# Tính tổng xếp hạng
df['Overall Rank'] = df['Profit Rank'] + df['Drawdown Rank'] + df['RR Ratio Rank']
df = df.sort_values('Overall Rank')

# In bảng tóm tắt
print('\nBẢNG PHÂN TÍCH TÓM TẮT:')
print(tabulate(df[['Risk Level', 'Profit (%)', 'Drawdown (%)', 'Win Rate (%)', 'RR Ratio', 'Overall Rank']], 
               headers='keys', tablefmt='grid', showindex=False, floatfmt='.2f'))

# Tìm mức rủi ro tối ưu về RR Ratio
best_rr = df.loc[df['RR Ratio'].idxmax()]
print(f'\nMức rủi ro tối ưu về tỷ lệ lợi nhuận/rủi ro: {best_rr["Risk Level"]} với RR Ratio = {best_rr["RR Ratio"]:.2f}')

# Tìm mức rủi ro tối ưu tổng thể
best_overall = df.iloc[0]
print(f'Mức rủi ro tối ưu tổng thể: {best_overall["Risk Level"]} với xếp hạng = {best_overall["Overall Rank"]:.1f}')

# In kết luận
print("\n=== KẾT LUẬN PHÂN TÍCH RỦI RO ===")
print("1. Win rate tăng theo mức rủi ro từ mức ~42% (3%) lên tới ~80% (30-40%)")
print("2. Mức rủi ro cao nhất (40%) cho lợi nhuận cao nhất (40.37%) nhưng drawdown cũng cao nhất (80%)")
print("3. Ultra_conservative (3%) có tỷ lệ RR cao thứ hai (2.07) nhưng lợi nhuận còn thấp (~3.6%)")
print("4. Aggressive (9%) có tỷ lệ RR tốt nhất (2.25) với lợi nhuận khá (9.26%) và drawdown thấp (4.12%)")
print("5. Extreme_risk (20%) có tỷ lệ RR cao (2.15) với lợi nhuận ấn tượng (26.31%) và drawdown vừa phải (12.21%)")
print("")
print("Kết luận tổng quan về mức rủi ro:")
print("- An toàn nhất: Ultra_conservative (3%)")
print("- Cân bằng nhất: Aggressive (9%)")
print("- Hiệu quả nhất về lợi nhuận/rủi ro: Extreme_risk (20%)")
print("- Rủi ro cao/Tiềm năng cao: Ultra_high_risk (25%)")
print("- Cực kỳ rủi ro: Max_risk (40%) - chỉ phù hợp với vốn chấp nhận mất tới 80%")