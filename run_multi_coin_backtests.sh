#!/bin/bash

# Script để chạy backtest tự động cho nhiều đồng coin với nhiều chiến lược
# Cách dùng: ./run_multi_coin_backtests.sh [interval]
# Nếu không có interval được chỉ định, mặc định sẽ là "1h"

# Thiết lập khung thời gian mặc định
INTERVAL=${1:-"1h"}

# Danh sách các đồng coin
COINS=("BTCUSDT" "ETHUSDT" "BNBUSDT" "ADAUSDT" "SOLUSDT" "DOTUSDT" "XRPUSDT" "LTCUSDT")
# Không chạy PIUSDT vì chưa có dữ liệu

# Danh sách các chiến lược
STRATEGIES=("rsi" "macd" "ema" "bbands" "auto" "combined")

# Danh sách các khoảng thời gian (theo số tháng)
PERIODS=("1" "3" "6" "9")

# Tạo thư mục kết quả nếu chưa tồn tại
mkdir -p backtest_results
mkdir -p backtest_charts
mkdir -p backtest_summary

# Tạo file CSV tổng hợp kết quả
SUMMARY_FILE="backtest_summary/all_results_${INTERVAL}.csv"
echo "Coin,Strategy,Period,Win Rate,Profit Factor,Sharpe Ratio,Expectancy,Profit Amount,Profit Percent,Max Drawdown" > $SUMMARY_FILE

# Tạo file HTML cho bảng xếp hạng
RANKING_FILE="backtest_summary/strategies_ranking_${INTERVAL}.html"
cat > $RANKING_FILE << 'EOL'
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Xếp hạng chiến lược giao dịch</title>
    <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
    <style>
        body {
            padding: 20px;
            font-family: Arial, sans-serif;
        }
        .strategy-card {
            margin-bottom: 20px;
            border-radius: 5px;
            overflow: hidden;
        }
        .strategy-header {
            padding: 10px 15px;
            font-weight: bold;
        }
        .primary {
            background-color: var(--bs-primary);
            color: white;
        }
        .secondary {
            background-color: var(--bs-secondary);
            color: white;
        }
        .success {
            background-color: var(--bs-success);
            color: white;
        }
        .danger {
            background-color: var(--bs-danger);
            color: white;
        }
        .warning {
            background-color: var(--bs-warning);
            color: black;
        }
        .info {
            background-color: var(--bs-info);
            color: white;
        }
        .dark {
            background-color: var(--bs-dark);
            color: white;
        }
    </style>
</head>
<body data-bs-theme="dark">
    <div class="container">
        <h1 class="mb-4">Xếp hạng chiến lược giao dịch</h1>
        <p class="lead">Phân tích kết quả backtest cho khung thời gian: <span id="interval"></span></p>
        
        <h2 class="mt-5 mb-3">Xếp hạng dựa trên lợi nhuận</h2>
        <div id="profit-ranking">
            <!-- Bảng xếp hạng dựa trên lợi nhuận sẽ được thêm vào đây -->
        </div>
        
        <h2 class="mt-5 mb-3">Xếp hạng dựa trên Sharpe Ratio</h2>
        <div id="sharpe-ranking">
            <!-- Bảng xếp hạng dựa trên Sharpe Ratio sẽ được thêm vào đây -->
        </div>
        
        <h2 class="mt-5 mb-3">Xếp hạng dựa trên Win Rate</h2>
        <div id="winrate-ranking">
            <!-- Bảng xếp hạng dựa trên Win Rate sẽ được thêm vào đây -->
        </div>
        
        <h2 class="mt-5 mb-3">So sánh chiến lược</h2>
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>Tên chiến lược</th>
                        <th>Số đồng</th>
                        <th>Win Rate trung bình</th>
                        <th>Lợi nhuận trung bình</th>
                        <th>Sharpe Ratio trung bình</th>
                    </tr>
                </thead>
                <tbody id="strategy-comparison">
                    <!-- Phân tích dựa trên chiến lược sẽ được thêm vào đây -->
                </tbody>
            </table>
        </div>
        
        <h2 class="mt-5 mb-3">Hiệu suất theo đồng coin</h2>
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>Coin</th>
                        <th>Chiến lược tốt nhất</th>
                        <th>Lợi nhuận cao nhất</th>
                        <th>Win Rate cao nhất</th>
                    </tr>
                </thead>
                <tbody id="coin-performance">
                    <!-- Phân tích dựa trên coin sẽ được thêm vào đây -->
                </tbody>
            </table>
        </div>
        
        <h2 class="mt-5 mb-3">Kết quả chi tiết</h2>
        <div class="table-responsive">
            <table class="table table-striped table-hover">
                <thead>
                    <tr>
                        <th>Coin</th>
                        <th>Chiến lược</th>
                        <th>Khoảng thời gian</th>
                        <th>Win Rate</th>
                        <th>Profit Factor</th>
                        <th>Sharpe Ratio</th>
                        <th>Lợi nhuận (%)</th>
                    </tr>
                </thead>
                <tbody id="detailed-results">
                    <!-- Kết quả chi tiết sẽ được thêm vào đây -->
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        // JavaScript sẽ được thêm vào đây để phân tích và hiển thị kết quả
        document.getElementById('interval').textContent = '%INTERVAL%';
        
        // Dữ liệu tổng hợp
        const allResults = [
            // Dữ liệu sẽ được thêm vào đây
            %DATA%
        ];
        
        // Xử lý dữ liệu và hiển thị kết quả
        function processData() {
            // Xếp hạng dựa trên lợi nhuận
            const profitRanking = [...allResults]
                .sort((a, b) => b.profitPercent - a.profitPercent)
                .slice(0, 10);
            
            let profitHTML = '<div class="row">';
            profitRanking.forEach((item, index) => {
                const colorClass = index < 3 ? 'success' : (index < 6 ? 'primary' : 'secondary');
                profitHTML += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card strategy-card">
                        <div class="strategy-header ${colorClass}">
                            ${index + 1}. ${item.coin} - ${item.strategy} (${item.period} tháng)
                        </div>
                        <div class="card-body">
                            <p class="card-text">Lợi nhuận: <strong>${item.profitPercent.toFixed(2)}%</strong></p>
                            <p class="card-text">Win Rate: ${item.winRate.toFixed(2)}%</p>
                            <p class="card-text">Sharpe Ratio: ${item.sharpeRatio.toFixed(2)}</p>
                        </div>
                    </div>
                </div>`;
            });
            profitHTML += '</div>';
            document.getElementById('profit-ranking').innerHTML = profitHTML;
            
            // Xếp hạng dựa trên Sharpe Ratio
            const sharpeRanking = [...allResults]
                .sort((a, b) => b.sharpeRatio - a.sharpeRatio)
                .slice(0, 10);
            
            let sharpeHTML = '<div class="row">';
            sharpeRanking.forEach((item, index) => {
                const colorClass = index < 3 ? 'info' : (index < 6 ? 'primary' : 'secondary');
                sharpeHTML += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card strategy-card">
                        <div class="strategy-header ${colorClass}">
                            ${index + 1}. ${item.coin} - ${item.strategy} (${item.period} tháng)
                        </div>
                        <div class="card-body">
                            <p class="card-text">Sharpe Ratio: <strong>${item.sharpeRatio.toFixed(2)}</strong></p>
                            <p class="card-text">Lợi nhuận: ${item.profitPercent.toFixed(2)}%</p>
                            <p class="card-text">Win Rate: ${item.winRate.toFixed(2)}%</p>
                        </div>
                    </div>
                </div>`;
            });
            sharpeHTML += '</div>';
            document.getElementById('sharpe-ranking').innerHTML = sharpeHTML;
            
            // Xếp hạng dựa trên Win Rate
            const winRateRanking = [...allResults]
                .sort((a, b) => b.winRate - a.winRate)
                .slice(0, 10);
            
            let winRateHTML = '<div class="row">';
            winRateRanking.forEach((item, index) => {
                const colorClass = index < 3 ? 'warning' : (index < 6 ? 'primary' : 'secondary');
                winRateHTML += `
                <div class="col-md-6 col-lg-4 mb-3">
                    <div class="card strategy-card">
                        <div class="strategy-header ${colorClass}">
                            ${index + 1}. ${item.coin} - ${item.strategy} (${item.period} tháng)
                        </div>
                        <div class="card-body">
                            <p class="card-text">Win Rate: <strong>${item.winRate.toFixed(2)}%</strong></p>
                            <p class="card-text">Lợi nhuận: ${item.profitPercent.toFixed(2)}%</p>
                            <p class="card-text">Sharpe Ratio: ${item.sharpeRatio.toFixed(2)}</p>
                        </div>
                    </div>
                </div>`;
            });
            winRateHTML += '</div>';
            document.getElementById('winrate-ranking').innerHTML = winRateHTML;
            
            // So sánh chiến lược
            const strategySummary = {};
            allResults.forEach(item => {
                if (!strategySummary[item.strategy]) {
                    strategySummary[item.strategy] = {
                        count: 0,
                        totalWinRate: 0,
                        totalProfit: 0,
                        totalSharpe: 0
                    };
                }
                strategySummary[item.strategy].count++;
                strategySummary[item.strategy].totalWinRate += item.winRate;
                strategySummary[item.strategy].totalProfit += item.profitPercent;
                strategySummary[item.strategy].totalSharpe += item.sharpeRatio;
            });
            
            let strategyHTML = '';
            Object.keys(strategySummary).forEach(strategy => {
                const summary = strategySummary[strategy];
                strategyHTML += `
                <tr>
                    <td>${strategy.toUpperCase()}</td>
                    <td>${summary.count}</td>
                    <td>${(summary.totalWinRate / summary.count).toFixed(2)}%</td>
                    <td>${(summary.totalProfit / summary.count).toFixed(2)}%</td>
                    <td>${(summary.totalSharpe / summary.count).toFixed(2)}</td>
                </tr>`;
            });
            document.getElementById('strategy-comparison').innerHTML = strategyHTML;
            
            // Hiệu suất theo đồng coin
            const coinSummary = {};
            allResults.forEach(item => {
                if (!coinSummary[item.coin]) {
                    coinSummary[item.coin] = {
                        bestStrategy: '',
                        highestProfit: -Infinity,
                        bestWinRateStrategy: '',
                        highestWinRate: -Infinity
                    };
                }
                
                if (item.profitPercent > coinSummary[item.coin].highestProfit) {
                    coinSummary[item.coin].bestStrategy = item.strategy;
                    coinSummary[item.coin].highestProfit = item.profitPercent;
                }
                
                if (item.winRate > coinSummary[item.coin].highestWinRate) {
                    coinSummary[item.coin].bestWinRateStrategy = item.strategy;
                    coinSummary[item.coin].highestWinRate = item.winRate;
                }
            });
            
            let coinHTML = '';
            Object.keys(coinSummary).forEach(coin => {
                const summary = coinSummary[coin];
                coinHTML += `
                <tr>
                    <td>${coin}</td>
                    <td>${summary.bestStrategy.toUpperCase()}</td>
                    <td>${summary.highestProfit.toFixed(2)}%</td>
                    <td>${summary.highestWinRate.toFixed(2)}% (${summary.bestWinRateStrategy.toUpperCase()})</td>
                </tr>`;
            });
            document.getElementById('coin-performance').innerHTML = coinHTML;
            
            // Kết quả chi tiết
            let detailedHTML = '';
            allResults.forEach(item => {
                detailedHTML += `
                <tr>
                    <td>${item.coin}</td>
                    <td>${item.strategy.toUpperCase()}</td>
                    <td>${item.period} tháng</td>
                    <td>${item.winRate.toFixed(2)}%</td>
                    <td>${item.profitFactor.toFixed(2)}</td>
                    <td>${item.sharpeRatio.toFixed(2)}</td>
                    <td>${item.profitPercent.toFixed(2)}%</td>
                </tr>`;
            });
            document.getElementById('detailed-results').innerHTML = detailedHTML;
        }
        
        // Chạy xử lý dữ liệu khi trang được tải
        processData();
    </script>
</body>
</html>
EOL

# Thay interval trong file HTML
sed -i "s/%INTERVAL%/$INTERVAL/g" $RANKING_FILE

# Biến đếm để theo dõi tiến trình
TOTAL_TESTS=$((${#COINS[@]} * ${#STRATEGIES[@]} * ${#PERIODS[@]}))
COMPLETED_TESTS=0

# Mảng để lưu dữ liệu JSON cho file HTML
JSON_DATA=()

echo "=== Bắt đầu chạy backtest cho nhiều đồng coin và chiến lược ==="
echo "Khung thời gian: $INTERVAL"
echo "Số lượng coins: ${#COINS[@]}"
echo "Số lượng chiến lược: ${#STRATEGIES[@]}"
echo "Số lượng khoảng thời gian: ${#PERIODS[@]}"
echo "Tổng số test sẽ chạy: $TOTAL_TESTS"
echo "-------------------------------------------------"

# Thời gian bắt đầu
START_TIME=$(date +%s)

# Lặp qua từng đồng coin
for COIN in "${COINS[@]}"; do
    echo "Chạy backtest cho $COIN..."
    
    # Lặp qua từng chiến lược
    for STRATEGY in "${STRATEGIES[@]}"; do
        
        # Lặp qua từng khoảng thời gian
        for PERIOD in "${PERIODS[@]}"; do
            # Tính ngày bắt đầu
            START_DATE=$(date -d "$(date +%Y-%m-%d) - $PERIOD months" +%Y-%m-%d)
            END_DATE=$(date +%Y-%m-%d)
            
            echo "  + Đang chạy: $COIN - $STRATEGY - $PERIOD tháng ($START_DATE đến $END_DATE)"
            
            # Thiết lập tiền tố output
            OUTPUT_PREFIX="${PERIOD}month_${COIN}_${STRATEGY}_"
            
            # Chạy backtest
            python enhanced_backtest.py --symbol $COIN --interval $INTERVAL --strategy $STRATEGY \
                --start_date $START_DATE --end_date $END_DATE \
                --output_prefix $OUTPUT_PREFIX > /dev/null 2>&1
            
            # Trích xuất kết quả
            RESULT_JSON="backtest_results/${OUTPUT_PREFIX}${COIN}_${INTERVAL}_${STRATEGY}_results.json"
            
            if [ -f "$RESULT_JSON" ]; then
                # Trích xuất các chỉ số hiệu suất từ file JSON
                WIN_RATE=$(cat $RESULT_JSON | grep -o '"win_rate": [0-9.]*' | cut -d' ' -f2)
                PROFIT_FACTOR=$(cat $RESULT_JSON | grep -o '"profit_factor": [0-9.]*' | cut -d' ' -f2)
                SHARPE_RATIO=$(cat $RESULT_JSON | grep -o '"sharpe_ratio": [0-9.]*' | cut -d' ' -f2)
                EXPECTANCY=$(cat $RESULT_JSON | grep -o '"expectancy": [0-9.]*' | cut -d' ' -f2)
                PROFIT_AMOUNT=$(cat $RESULT_JSON | grep -o '"profit_amount": [0-9.]*' | cut -d' ' -f2)
                PROFIT_PERCENT=$(cat $RESULT_JSON | grep -o '"profit_percent": [0-9.]*' | cut -d' ' -f2)
                MAX_DRAWDOWN=$(cat $RESULT_JSON | grep -o '"max_drawdown": [0-9.]*' | cut -d' ' -f2)
                
                # Thêm vào file CSV
                echo "$COIN,$STRATEGY,$PERIOD,$WIN_RATE,$PROFIT_FACTOR,$SHARPE_RATIO,$EXPECTANCY,$PROFIT_AMOUNT,$PROFIT_PERCENT,$MAX_DRAWDOWN" >> $SUMMARY_FILE
                
                # Thêm vào mảng JSON data
                JSON_DATA+=("{coin: '$COIN', strategy: '$STRATEGY', period: $PERIOD, winRate: $WIN_RATE, profitFactor: $PROFIT_FACTOR, sharpeRatio: $SHARPE_RATIO, expectancy: $EXPECTANCY, profitAmount: $PROFIT_AMOUNT, profitPercent: $PROFIT_PERCENT, maxDrawdown: $MAX_DRAWDOWN}")
                
                echo "    Win Rate: $WIN_RATE%, Lợi nhuận: $PROFIT_PERCENT%, Sharpe: $SHARPE_RATIO"
            else
                echo "    [THẤT BẠI] Không tìm thấy file kết quả cho $COIN - $STRATEGY - $PERIOD tháng"
            fi
            
            # Cập nhật tiến trình
            COMPLETED_TESTS=$((COMPLETED_TESTS + 1))
            PCT_COMPLETE=$((100 * COMPLETED_TESTS / TOTAL_TESTS))
            
            # Thời gian đã trôi qua
            CURRENT_TIME=$(date +%s)
            ELAPSED_TIME=$((CURRENT_TIME - START_TIME))
            
            # Ước tính thời gian còn lại
            if [ $COMPLETED_TESTS -gt 0 ]; then
                REMAINING_TESTS=$((TOTAL_TESTS - COMPLETED_TESTS))
                TIME_PER_TEST=$((ELAPSED_TIME / COMPLETED_TESTS))
                REMAINING_TIME=$((REMAINING_TESTS * TIME_PER_TEST))
                
                # Định dạng thời gian còn lại
                REMAINING_HOURS=$((REMAINING_TIME / 3600))
                REMAINING_MINUTES=$(((REMAINING_TIME % 3600) / 60))
                
                echo "    Tiến trình: $COMPLETED_TESTS/$TOTAL_TESTS ($PCT_COMPLETE%) - Còn lại: ${REMAINING_HOURS}h ${REMAINING_MINUTES}m"
            fi
            
            echo "-------------------------------------------------"
        done
    done
done

# Thêm dữ liệu JSON vào file HTML
JSON_DATA_STR=$(IFS=","; echo "${JSON_DATA[*]}")
sed -i "s/%DATA%/$JSON_DATA_STR/g" $RANKING_FILE

echo "=== Đã hoàn thành tất cả backtest ==="
echo "Tổng số test đã chạy: $COMPLETED_TESTS/$TOTAL_TESTS"
echo "Kết quả tổng hợp đã được lưu vào file: $SUMMARY_FILE"
echo "Báo cáo phân tích chi tiết đã được lưu vào file: $RANKING_FILE"

# Tính tổng thời gian chạy
END_TIME=$(date +%s)
TOTAL_TIME=$((END_TIME - START_TIME))
TOTAL_HOURS=$((TOTAL_TIME / 3600))
TOTAL_MINUTES=$(((TOTAL_TIME % 3600) / 60))
TOTAL_SECONDS=$((TOTAL_TIME % 60))

echo "Tổng thời gian chạy: ${TOTAL_HOURS}h ${TOTAL_MINUTES}m ${TOTAL_SECONDS}s"