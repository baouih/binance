# Tổng hợp các chiến thuật giao dịch

*Báo cáo được tạo lúc: 2025-03-27 14:44:55*

## Tổng quan

Hệ thống có tổng cộng **66** file thuật toán và chiến lược, phân loại như sau:

- **Core Strategies**: 19 thuật toán
- **Market Analysis**: 17 thuật toán
- **Technical Indicators**: 1 thuật toán
- **Risk Management**: 8 thuật toán
- **Optimizers & Backtesting**: 18 thuật toán
- **Machine Learning**: 1 thuật toán
- **Utility & Integration**: 2 thuật toán

## Chi tiết từng nhóm

### Core Strategies

#### 1. adaptive_exit_strategy.py

Adaptive Exit Strategy - Chiến lược thoát lệnh thích ứng theo chế độ thị trường

Module này cung cấp các chiến lược thoát lệnh khác nhau tối ưu cho từng chế độ thị trường,
giúp tối đa hóa lợi nhuận và giảm thiểu rủi ro....

**Các lớp chính:**

- `AdaptiveExitStrategy`

**Các hàm chính:**

- `determine_exit_strategy()`
- `calculate_exit_points()`
- `get_exit_signal()`
- `visualize_exit_points()`
- `update_strategy_config()`
- ... và 2 hàm khác

#### 2. adaptive_mode_selector.py

Module thích ứng tự động lựa chọn giữa chế độ hedge mode và single direction
dựa trên điều kiện thị trường hiện tại và backtest...

**Các lớp chính:**

- `AdaptiveModeSelector`

**Các hàm chính:**

- `load_config()`
- `save_config()`
- `load_performance_history()`
- `save_performance_history()`
- `is_analysis_needed()`
- ... và 5 hàm khác

#### 3. adaptive_mode_trader.py

Thực hiện chiến lược giao dịch thích ứng với Hedge Mode và Single Direction
tự động lựa chọn dựa trên điều kiện thị trường...

**Các lớp chính:**

- `AdaptiveModeTrader`

**Các hàm chính:**

- `load_config()`
- `save_config()`
- `save_positions()`
- `load_positions()`
- `start()`
- ... và 14 hàm khác

#### 4. adaptive_multi_symbol_controller.py

Bộ điều khiển giao dịch đa cặp tiền thích ứng

Module này điều phối chiến lược giao dịch trên nhiều cặp tiền khác nhau, 
với khả năng phân bổ vốn, quản lý rủi ro động, và lọc tín hiệu giao dịch 
theo thanh khoản thị trường....

**Các lớp chính:**

- `AdaptiveMultiSymbolController`

**Các hàm chính:**

- `update_market_data()`
- `generate_trading_signals()`
- `execute_trading_signals()`
- `update_trailing_stops()`
- `run()`
- ... và 1 hàm khác

#### 5. adaptive_stop_loss_manager.py

Module quản lý stop loss thích ứng dựa trên phân tích đa khung thời gian

Module này quản lý stop loss và take profit thích ứng dựa trên:
1. Biến động thị trường hiện tại
2. Phân tích đa khung thời gian (5m, 1h, 4h)...

**Các lớp chính:**

- `AdaptiveStopLossManager`

**Các hàm chính:**

- `load_config()`
- `get_active_positions()`
- `analyze_position_volatility()`
- `calculate_optimal_stop_loss()`
- `update_active_positions_sltp()`
- ... và 2 hàm khác

#### 6. adaptive_strategy_selector.py

Module chọn chiến lược thích ứng (Adaptive Strategy Selector)

Module này tự động chọn chiến lược giao dịch phù hợp dựa trên chế độ thị trường,
đồng thời tối ưu hóa quá trình tính toán chỉ báo bằng cách sử dụng bộ nhớ cache....

**Các lớp chính:**

- `AdaptiveStrategySelector`

**Các hàm chính:**

- `save_config()`
- `get_market_regime()`
- `get_strategies_for_regime()`
- `get_strategy_parameters()`
- `get_risk_adjustment()`
- ... và 4 hàm khác

#### 7. adaptive_volatility_threshold.py

Module điều chỉnh ngưỡng biến động thông minh (Adaptive Volatility Threshold)

Module này cung cấp các hàm để tính toán ngưỡng biến động thông minh cho từng cặp tiền,
dựa trên dữ liệu lịch sử và các đặc điểm riêng của từng đồng coin....

**Các lớp chính:**

- `AdaptiveVolatilityThreshold`

**Các hàm chính:**

- `save_config()`
- `get_volatility_threshold()`
- `update_volatility_history()`
- `set_static_threshold()`
- `toggle_adaptive_threshold()`
- ... và 2 hàm khác

#### 8. check_strategy_status.py

Không có mô tả

**Các hàm chính:**

- `main()`

#### 9. composite_trading_strategy.py

Module chiến thuật giao dịch tổng hợp nâng cao (Composite Trading Strategy)

Module này triển khai một chiến thuật giao dịch tổng hợp tiên tiến, kết hợp nhiều chiến lược 
giao dịch với trọng số động, tự động điều chỉnh theo chế độ thị trường và hiệu suất gần đây.
Cung cấp khả năng thích ứng với điều kiện thị trường thay đổi để cải thiện hiệu suất....

**Các lớp chính:**

- `CompositeTradingStrategy`

**Các hàm chính:**

- `analyze_market()`
- `get_trading_signal()`
- `get_market_regime()`
- `get_suitable_strategies()`
- `get_optimal_parameters()`
- ... và 6 hàm khác

#### 10. enhanced_adaptive_trailing_stop.py

Module Enhanced Adaptive Trailing Stop (EATS)

Module này cung cấp các chiến lược trailing stop nâng cao với khả năng tự động
thích nghi với điều kiện thị trường, bao gồm:
...

**Các lớp chính:**

- `EnhancedAdaptiveTrailingStop`

**Các hàm chính:**

- `update_volatility()`
- `initialize_trailing_stop()`
- `update_trailing_stop()`
- `check_stop_condition()`
- `close_position()`
- ... và 7 hàm khác

#### 11. micro_trading_strategy.py

Module chiến lược giao dịch cho tài khoản nhỏ (Micro Trading Strategy)

Module này cung cấp các chiến lược giao dịch được tối ưu hóa cho tài khoản có vốn nhỏ
(100-200 USD) kết hợp với đòn bẩy cao (x10-x20) trên thị trường Futures....

**Các lớp chính:**

- `MicroTradingStrategy`

**Các hàm chính:**

- `generate_signal()`
- `calculate_position_size()`
- `execute_trade()`

#### 12. mtf_optimized_strategy.py

Chiến lược giao dịch Bitcoin đa khung thời gian tối ưu hóa

Module này cung cấp chiến lược giao dịch thích ứng đa khung thời gian (MTF), kết hợp phân tích
từ nhiều khung thời gian khác nhau để tạo ra tín hiệu giao dịch chính xác hơn và giảm thiểu
tín hiệu giả....

**Các lớp chính:**

- `MTFOptimizedStrategy`

**Các hàm chính:**

- `calculate_indicators()`
- `detect_market_regime()`
- `analyze_multi_timeframe()`
- `calculate_signal_strength()`
- `generate_signal()`
- ... và 6 hàm khác

#### 13. optimized_entry_scheduler.py

Scheduler tự động cho điểm vào lệnh tối ưu

Module này lên lịch thực thi các chiến lược giao dịch dựa trên thời gian tối ưu,
giúp tự động hóa quá trình vào lệnh theo các khung thời gian cụ thể....

**Các lớp chính:**

- `TelegramNotifier`
- `OptimizedEntryScheduler`

**Các hàm chính:**

- `handle_scheduled_event()`
- `send_session_reminder()`
- `send_daily_summary()`
- `send_weekend_alert()`
- `schedule_all_jobs()`
- ... và 6 hàm khác

#### 14. optimized_entry_strategy.py

Script tối ưu hóa chiến lược vào lệnh 3-5 lệnh/ngày

Script này phân tích thời điểm tối ưu để vào lệnh trong ngày
và tạo lịch trình vào lệnh để đạt tỷ lệ thắng cao nhất....

**Các hàm chính:**

- `calculate_optimal_entry_times()`
- `optimize_daily_entries()`
- `assign_coins_to_entries()`
- `optimize_weekly_schedule()`
- `generate_entry_strategy()`
- ... và 4 hàm khác

#### 15. optimized_strategy.py

Chiến lược giao dịch Bitcoin tối ưu hóa thích ứng với chế độ thị trường

Module này cung cấp chiến lược giao dịch tối ưu hóa dựa trên phân tích chế độ thị trường,
tập trung vào cải thiện win rate trong các giai đoạn thị trường khác nhau.
Chiến lược được tối ưu hóa để hoạt động tốt nhất trong thị trường trending, vô hiệu hóa...

**Các lớp chính:**

- `OptimizedStrategy`

**Các hàm chính:**

- `calculate_indicators()`
- `detect_market_regime()`
- `calculate_signal_strength()`
- `generate_signal()`
- `update_performance()`
- ... và 5 hàm khác

#### 16. sideways_market_strategy.py

Chiến lược chuyên biệt cho thị trường đi ngang (Sideways Market)
    Tối ưu hóa để nâng cao tỷ lệ thắng trong điều kiện thị trường không có xu hướng rõ ràng...

**Các lớp chính:**

- `ta`
- `SidewaysMarketStrategy`

**Các hàm chính:**

- `SMA()`
- `EMA()`
- `STDDEV()`
- `RSI()`
- `ATR()`
- ... và 16 hàm khác

#### 17. start_adaptive_trader.py

Script khởi động Adaptive Mode Trader - tự động chọn giữa Hedge Mode và Single Direction...

**Các hàm chính:**

- `main()`

#### 18. strategy_conflict_checker.py

Strategy Conflict Checker - Công cụ kiểm tra xung đột giữa các chiến lược giao dịch
Phát hiện mâu thuẫn tín hiệu, xung đột vị thế và vấn đề chồng chéo lệnh...

**Các lớp chính:**

- `StrategyConflictChecker`

**Các hàm chính:**

- `load_config()`
- `load_strategy_signals()`
- `check_conflicts()`
- `main()`

#### 19. time_optimized_strategy.py

Chiến lược giao dịch tối ưu hóa theo thời gian

Module này tối ưu hóa chiến lược giao dịch dựa trên thời gian
để tăng tỷ lệ thành công và tổng lợi nhuận....

**Các lớp chính:**

- `TimeOptimizedStrategy`

**Các hàm chính:**

- `is_optimal_time()`
- `get_recommended_direction()`
- `calculate_confidence_score()`
- `analyze_entry_opportunity()`
- `record_trade()`
- ... và 6 hàm khác


### Market Analysis

#### 1. activate_market_analyzer.py

Activate Market Analyzer
-----------------------
Script để kích hoạt hệ thống phân tích thị trường và gửi thông báo qua Telegram...

**Các lớp chính:**

- `MarketAnalyzerActivator`

**Các hàm chính:**

- `run_market_analysis()`
- `start()`
- `stop()`
- `run_once()`
- `main()`

#### 2. enhanced_market_regime_detector.py

Enhanced Market Regime Detector - Bộ phát hiện chế độ thị trường nâng cao...

**Các lớp chính:**

- `MarketRegimeType`
- `EnhancedMarketRegimeDetector`

**Các hàm chính:**

- `prepare_features()`
- `analyze_current_market()`
- `detect_regime_changes()`
- `save()`
- `load()`

#### 3. liquidity_analyzer.py

Module phân tích thanh khoản thị trường (Liquidity Analyzer)

Module này cung cấp các hàm phân tích chi tiết về thanh khoản thị trường,
bao gồm độ sâu của order book, spread, và khối lượng giao dịch,
để đánh giá liệu một cặp tiền có đủ thanh khoản để giao dịch hay không....

**Các lớp chính:**

- `LiquidityAnalyzer`

**Các hàm chính:**

- `save_config()`
- `check_liquidity_conditions()`
- `update_min_liquidity_score()`
- `update_score_weights()`
- `main()`

#### 4. market_analyzer.py

Module phân tích thị trường...

**Các lớp chính:**

- `Client`
- `BinanceAPIException`
- `ModuleStub`
- `MarketAnalyzer`

**Các hàm chính:**

- `get_current_price()`
- `get_market_overview()`
- `get_historical_data()`
- `calculate_sma()`
- `calculate_ema()`
- ... và 10 hàm khác

#### 5. market_regime_detector.py

Market Regime Detector - Phát hiện chế độ thị trường...

**Các lớp chính:**

- `MarketRegimeDetector`

**Các hàm chính:**

- `detect_regimes()`
- `detect_regime_changes()`
- `get_current_regime()`

#### 6. market_regime_performance_analyzer.py

Script phân tích hiệu suất theo chế độ thị trường từ kết quả backtest

Script này tải các kết quả backtest, phân tích hiệu suất theo từng chế độ thị trường,
và tạo các báo cáo và biểu đồ để so sánh hiệu suất....

**Các lớp chính:**

- `MarketRegimePerformanceAnalyzer`

**Các hàm chính:**

- `analyze_market_regimes()`
- `load_results()`
- `analyze_regime_performance()`
- `create_regime_performance_chart()`
- `create_regime_comparison_report()`
- ... và 2 hàm khác

#### 7. market_sentiment_analyzer.py

Module phân tích cảm xúc thị trường (Market Sentiment Analyzer)

Module này phân tích cảm xúc thị trường dựa trên nhiều nguồn dữ liệu và
chỉ số kỹ thuật, tạo ra một chỉ số cảm xúc tổng hợp và biểu thị trực quan
bằng emoji....

**Các lớp chính:**

- `MarketSentimentAnalyzer`

**Các hàm chính:**

- `analyze_technical_indicators()`
- `update_market_sentiment()`
- `get_current_sentiment()`
- `get_sentiment_trend()`
- `get_sentiment_widget_data()`
- ... và 1 hàm khác

#### 8. multi_timeframe_analyzer.py

Module phân tích đa khung thời gian (Multi-timeframe Analysis)

Module này cung cấp các công cụ để phân tích thị trường trên nhiều khung thời gian
khác nhau và tổng hợp kết quả để có tín hiệu giao dịch chính xác hơn....

**Các lớp chính:**

- `MultiTimeframeAnalyzer`

**Các hàm chính:**

- `get_data()`
- `analyze_rsi()`
- `analyze_trend()`
- `consolidate_signals()`
- `update_weights_based_on_performance()`
- ... và 1 hàm khác

#### 9. multi_timeframe_volatility_analyzer.py

Mô-đun phân tích biến động đa khung thời gian

Module này phân tích biến động thị trường trên nhiều khung thời gian (5m, 1h, 4h)
và điều chỉnh các ngưỡng stop loss phù hợp để tránh bị stopped out quá sớm....

**Các lớp chính:**

- `MultiTimeframeVolatilityAnalyzer`

**Các hàm chính:**

- `fetch_market_data()`
- `add_atr()`
- `calculate_weighted_volatility()`
- `recommend_stop_loss()`
- `analyze()`
- ... và 2 hàm khác

#### 10. regime_performance_analyzer.py

Regime Performance Analyzer - Phân tích hiệu suất hệ thống giao dịch theo chế độ thị trường

Module này cung cấp các công cụ để phân tích hiệu suất giao dịch tách biệt 
theo từng chế độ thị trường khác nhau, giúp tối ưu hóa chiến lược giao dịch
cho từng chế độ cụ thể....

**Các lớp chính:**

- `RegimePerformanceAnalyzer`

**Các hàm chính:**

- `analyze_trades_by_regime()`
- `generate_performance_report()`
- `get_best_regimes()`

#### 11. rsi_divergence_detector.py

RSI Divergence Detector

Module này giúp phát hiện sự phân kỳ (divergence) giữa giá và chỉ báo RSI,
đặc biệt hữu ích trong thị trường đi ngang....

**Các lớp chính:**

- `RSIDivergenceDetector`

**Các hàm chính:**

- `find_pivots()`
- `prepare_data()`
- `detect_divergence()`
- `get_trading_signal()`
- `visualize_divergence()`

#### 12. sideways_market_detector.py

Phát hiện thị trường đi ngang (sideways market) và tối ưu hóa giao dịch...

**Các lớp chính:**

- `SidewaysMarketDetector`

**Các hàm chính:**

- `calculate_indicators()`
- `detect_sideways_market()`
- `optimize_trading_params()`
- `generate_sideways_signals()`
- `plot_sideways_periods()`
- ... và 2 hàm khác

#### 13. signal_consistency_analyzer.py

Signal Consistency Analyzer - Công cụ phân tích tính nhất quán của tín hiệu giao dịch 
từ các thuật toán khác nhau để đảm bảo không có xung đột khi vào lệnh...

**Các lớp chính:**

- `SignalConsistencyAnalyzer`

**Các hàm chính:**

- `load_config()`
- `load_signals()`
- `analyze_consistency()`
- `main()`

#### 14. start_enhanced_market_analyzer.py

Script khởi động hệ thống phân tích thị trường nâng cao

Script này khởi động các module nâng cao để phân tích tất cả các cặp tiền 
và gửi thông báo Telegram theo định kỳ với đầy đủ thông tin....

**Các hàm chính:**

- `parse_arguments()`
- `save_pid()`
- `save_uptime_info()`
- `main()`

#### 15. technical_reversal_detector.py

Module phát hiện đảo chiều kỹ thuật (Technical Reversal Detector)

Module này cung cấp các phương pháp để phát hiện tín hiệu đảo chiều kỹ thuật trong thị trường,
cho phép vào lệnh ngược với xu hướng chính khi có tín hiệu đảo chiều đáng tin cậy....

**Các lớp chính:**

- `TechnicalReversalDetector`

**Các hàm chính:**

- `save_config()`
- `detect_reversal()`
- `check_technical_reversal()`
- `main()`

#### 16. volume_profile_analyzer.py

Volume Profile Analyzer - Phân tích cấu trúc khối lượng theo giá

Module này cung cấp công cụ phân tích Volume Profile để xác định vùng giá
tập trung giao dịch, hỗ trợ nhận diện vùng hỗ trợ, kháng cự và khả năng bứt phá....

**Các lớp chính:**

- `VolumeProfileAnalyzer`

**Các hàm chính:**

- `calculate_volume_profile()`
- `get_key_levels()`
- `analyze_trading_range()`
- `identify_support_resistance()`
- `visualize_volume_profile()`

#### 17. volume_profile_analyzer_extended.py

Volume Profile Analyzer - Phân tích cấu trúc khối lượng theo giá

Module này cung cấp công cụ phân tích Volume Profile để xác định vùng giá
tập trung giao dịch, hỗ trợ nhận diện vùng hỗ trợ, kháng cự và khả năng bứt phá....

**Các lớp chính:**

- `VolumeProfileAnalyzer`

**Các hàm chính:**

- `calculate_volume_profile()`
- `get_key_levels()`
- `analyze_trading_range()`
- `identify_support_resistance()`
- `identify_vwap_zones()`
- ... và 2 hàm khác


### Technical Indicators

#### 1. improved_rsi_strategy.py

Phiên bản cải tiến của chiến lược RSI với các biện pháp bảo vệ tốt hơn...

**Các hàm chính:**

- `generate_sample_data()`
- `backtest_rsi_strategy()`
- `main()`


### Risk Management

#### 1. account_size_based_strategy.py

Module chiến lược giao dịch dựa trên kích thước tài khoản

Module này triển khai các chiến lược giao dịch thích ứng theo kích thước tài khoản,
với các tối ưu riêng cho từng mức vốn từ $100 đến $1000, tự động điều chỉnh
đòn bẩy, quản lý rủi ro và lựa chọn cặp giao dịch phù hợp nhất....

**Các lớp chính:**

- `AccountSizeStrategy`

**Các hàm chính:**

- `update_market_data()`
- `detect_market_regime()`
- `select_optimal_strategy()`
- `calculate_position_size()`
- `calculate_stop_loss_take_profit()`
- ... và 5 hàm khác

#### 2. adaptive_risk_allocation.py

Phân bổ vốn động dựa trên hiệu suất gần đây giữa các mức rủi ro
    Tự động điều chỉnh tỷ lệ vốn phân bổ cho từng mức rủi ro dựa trên hiệu suất, drawdown và trạng thái thị trường...

**Các lớp chính:**

- `AdaptiveRiskAllocator`

**Các hàm chính:**

- `update_performance()`
- `calculate_performance_scores()`
- `reallocate()`
- `get_allocation()`
- `get_performance_stats()`
- ... và 3 hàm khác

#### 3. adaptive_risk_allocator.py

Module quản lý rủi ro thích ứng

Module này điều chỉnh mức rủi ro dựa vào điều kiện thị trường hiện tại,
phân tích xu hướng, và các thông số biến động để tối ưu hóa tỉ lệ lợi nhuận/rủi ro....

**Các lớp chính:**

- `AdaptiveRiskAllocator`

**Các hàm chính:**

- `load_config()`
- `save_config()`
- `get_risk_for_market_condition()`
- `analyze_market_condition()`
- `calculate_position_risk()`
- ... và 3 hàm khác

#### 4. adaptive_risk_levels.py

Quản lý rủi ro thích ứng với nhiều cấp độ rủi ro khác nhau...

**Các lớp chính:**

- `AdaptiveRiskManager`

**Các hàm chính:**

- `load_or_create_config()`
- `save_config()`
- `update_trade_result()`
- `get_current_risk_percentage()`
- `calculate_position_size()`
- ... và 3 hàm khác

#### 5. adaptive_risk_manager.py

Quản lý rủi ro tự động thích ứng dựa trên ATR và volatility...

**Các lớp chính:**

- `AdaptiveRiskManager`

**Các hàm chính:**

- `load_config()`
- `save_config()`
- `set_risk_level()`
- `get_current_risk_config()`
- `calculate_atr()`
- ... và 11 hàm khác

#### 6. multi_coin_risk_analyzer.py

Script phân tích hiệu suất của các mức rủi ro khác nhau trên nhiều đồng coin

Script này kiểm tra hiệu suất của các mức rủi ro khác nhau (10%, 15%, 20%, 30%)
trên các đồng coin thanh khoản cao như BTC, ETH, BNB, SOL......

**Các hàm chính:**

- `load_backtest_results()`
- `analyze_all_coins()`
- `calculate_summary_metrics()`
- `find_best_performers()`
- `analyze_risk_performance()`
- ... và 4 hàm khác

#### 7. multi_risk_strategy.py

Chiến lược giao dịch đa mức rủi ro với khả năng thích ứng theo điều kiện thị trường...

**Các lớp chính:**

- `MultiRiskStrategy`

**Các hàm chính:**

- `calculate_indicators()`
- `generate_signals()`
- `apply_strategy()`
- `backtest()`
- `test_multi_risk_strategy()`

#### 8. optimized_risk_manager.py

Quản lý rủi ro tối ưu hóa với chỉ 4 mức rủi ro phù hợp: 10%, 15%, 20%, 25%
    Mặc định là mức 20-25% dựa trên điều kiện thị trường...

**Các lớp chính:**

- `OptimizedRiskManager`

**Các hàm chính:**

- `update_market_state()`
- `update_performance()`
- `get_risk_level()`
- `get_position_size()`
- `get_performance_stats()`
- ... và 6 hàm khác


### Optimizers & Backtesting

#### 1. adaptive_strategy_backtest.py

Backtest chiến lược thích ứng kết hợp MA crossover và tối ưu hóa thị trường đi ngang...

**Các lớp chính:**

- `DateTimeEncoder`

**Các hàm chính:**

- `load_risk_config()`
- `calculate_indicators()`
- `ma_crossover_signals()`
- `apply_atr_based_stops()`
- `calculate_position_size()`
- ... và 5 hàm khác

#### 2. adaptive_strategy_backtester.py

Script backtest nâng cao với chiến lược thích ứng và tự động điều chỉnh

Script này thực hiện backtest với khả năng:
1. Kết hợp nhiều chiến lược giao dịch (RSI, MACD, Bollinger, v.v.)
2. Tự động phát hiện chế độ thị trường (trending, ranging, volatile)...

**Các lớp chính:**

- `MarketRegimeDetector`
- `StrategiesManager`
- `RiskManager`

**Các hàm chính:**

- `detect_regime()`
- `get_regime_description()`
- `get_suitable_strategies()`
- `get_optimal_parameters()`
- `initialize_strategies()`
- ... và 15 hàm khác

#### 3. backtest_small_account_strategy.py

Khởi tạo backtester
        
        Args:
            start_date (str): Ngày bắt đầu (YYYY-MM-DD)
            end_date (str): Ngày kết thúc (YYYY-MM-DD)...

**Các lớp chính:**

- `SmallAccountBacktester`

**Các hàm chính:**

- `load_config()`
- `fetch_historical_data()`
- `fetch_complete_historical_data()`
- `calculate_indicators()`
- `generate_signals()`
- ... và 8 hàm khác

#### 4. debug_adaptive_backtest.py

Debug cho adaptive backtest...

**Các hàm chính:**

- `main()`

#### 5. ml_strategy_tester.py

Công cụ kiểm thử chiến lược ML và đánh giá hiệu suất
So sánh với các chiến lược truyền thống và chiến lược rủi ro cao...

**Các lớp chính:**

- `MLStrategyTester`

**Các hàm chính:**

- `load_model()`
- `prepare_data_for_backtesting()`
- `backtest_strategy()`
- `compare_strategies()`
- `compare_multiple_ml_models()`
- ... và 2 hàm khác

#### 6. optimized_strategy_backtester.py

Script kiểm tra hiệu quả chiến lược tối ưu với tất cả các coin

Script này chạy backtest trên tất cả các coin sử dụng chiến lược tối ưu
3-5 lệnh/ngày và so sánh với chiến lược cơ bản để xem tỷ lệ thắng có tăng không....

**Các hàm chính:**

- `load_data()`
- `calculate_indicators()`
- `is_in_optimal_time()`
- `detect_breakout_after_consolidation()`
- `detect_double_bottom_top()`
- ... và 9 hàm khác

#### 7. quick_test_strategy.py

Script kiểm tra nhanh hiệu quả chiến lược tối ưu trên một số coin

Script này chạy test nhanh trên một số coin và khung thời gian để xem
liệu chiến lược vào lệnh tối ưu có nâng cao tỷ lệ thắng so với cơ bản không....

**Các hàm chính:**

- `generate_test_data()`
- `create_report()`
- `main()`

#### 8. run_adaptive_backtest.py

Script thực thi backtest với hệ thống thích ứng thông minh

Script này thực hiện backtest với hệ thống giao dịch thích ứng theo chế độ thị trường
và tự động chọn chiến lược tối ưu dựa trên điều kiện hiện tại....

**Các hàm chính:**

- `create_sample_data()`
- `run_backtest()`
- `create_summary_report()`
- `main()`

#### 9. run_multi_coin_adaptive_test.py

Script chạy kiểm thử đa coin với nhiều mức rủi ro khác nhau

Script này sẽ thực hiện backtest trên nhiều cặp tiền và nhiều mức rủi ro
để so sánh hiệu suất và tìm ra cấu hình tối ưu....

**Các hàm chính:**

- `run_backtest()`
- `create_sample_backtest_result()`
- `run_all_tests()`
- `generate_report()`
- `main()`

#### 10. run_multi_strategy_backtest.py

Script kiểm thử nhiều chiến lược trên nhiều cặp tiền và khung thời gian

Script này sử dụng dữ liệu mẫu để kiểm thử hiệu suất của nhiều chiến lược giao dịch 
khác nhau trên nhiều cặp tiền và khung thời gian, từ đó lựa chọn chiến lược tối ưu....

**Các lớp chính:**

- `Strategy`
- `RSIStrategy`
- `MACDStrategy`
- `BollingerBandsStrategy`
- `StochasticStrategy`
- `EMACrossStrategy`
- `ADXStrategy`
- `CompositeStrategy`

**Các hàm chính:**

- `load_sample_data()`
- `calculate_indicators()`
- `generate_signal()`
- `get_info()`
- `generate_signal()`
- ... và 15 hàm khác

#### 11. strategy_optimizer.py

Công cụ tối ưu hóa chiến lược giao dịch tự động
Sử dụng Grid Search để tìm các tham số tối ưu cho mỗi chiến lược...

**Các lớp chính:**

- `StrategyOptimizer`

**Các hàm chính:**

- `optimize_all_strategies()`
- `optimize_rsi()`
- `optimize_macd()`
- `optimize_ema_cross()`
- `optimize_bbands()`
- ... và 3 hàm khác

#### 12. test_adaptive_risk.py

Tải dữ liệu lịch sử từ file CSV hoặc từ API
    
    Args:
        symbol (str): Mã cặp giao dịch
        timeframe (str): Khung thời gian...

**Các hàm chính:**

- `load_historical_data()`
- `test_atr_calculation()`
- `test_risk_parameters()`
- `plot_volatility_levels()`
- `plot_atr_based_sl_tp()`
- ... và 1 hàm khác

#### 13. test_data_analyzer.py

Script phân tích chi tiết kết quả test đa mức rủi ro

Script này đọc và phân tích dữ liệu từ các file kết quả backtest,
cung cấp thông tin chi tiết về hiệu suất của từng mức rủi ro và so sánh....

**Các hàm chính:**

- `load_result_file()`
- `extract_regime_performance()`
- `analyze_trades()`
- `analyze_risk_adjustments()`
- `get_risk_level_from_filename()`
- ... và 2 hàm khác

#### 14. test_integrated_strategy.py

Test Script cho Chiến lược Tích hợp Mới

Script này chạy backtest sử dụng chiến lược tích hợp mới với các tính năng:
- RSI phân loại 3 mức
- Fibonacci retracement...

**Các hàm chính:**

- `main()`

#### 15. test_market_analyzer.py

Test script cho MarketAnalyzer...

**Các hàm chính:**

- `main()`

#### 16. test_rsi_divergence.py

Test RSI Divergence Detector

Script này thực hiện kiểm thử bộ phát hiện RSI Divergence trên dữ liệu thị trường thật....

**Các hàm chính:**

- `load_data()`
- `test_rsi_divergence_detector()`
- `test_integrated_analysis()`
- `main()`

#### 17. test_rsi_strategy.py

Test RSI Strategy để kiểm tra lãi/lỗ...

**Các hàm chính:**

- `backtest_rsi_strategy()`
- `main()`

#### 18. testnet_adaptive_backtest.py

Script chạy backtest với chiến lược thích ứng trên dữ liệu thực từ Binance Testnet

Script này thực hiện:
1. Kết nối với Binance Testnet API để lấy dữ liệu thực
2. Xử lý dữ liệu và tính toán các chỉ báo kỹ thuật...

**Các lớp chính:**

- `BinanceTestnetAPI`

**Các hàm chính:**

- `get_server_time()`
- `get_exchange_info()`
- `get_historical_klines()`
- `get_historical_data()`
- `calculate_indicators()`
- ... và 3 hàm khác


### Machine Learning

#### 1. market_regime_ml_optimized.py

Hệ thống giao dịch thích ứng theo chế độ thị trường với ML

Module này xây dựng một hệ thống giao dịch thích ứng theo chế độ thị trường,
sử dụng học máy để phát hiện chế độ và tối ưu hóa chiến lược phù hợp.
Việc này giúp nâng cao tỷ lệ thắng bằng cách chỉ giao dịch trong các điều kiện...

**Các lớp chính:**

- `MarketRegimeDetector`
- `StrategySelector`
- `Strategy`
- `RSIStrategy`
- `MACDStrategy`
- `BollingerBandsStrategy`
- `EMACrossStrategy`
- `ADXStrategy`
- `CompositeStrategy`
- `AdaptiveTrader`

**Các hàm chính:**

- `extract_features()`
- `detect_regime_rule_based()`
- `detect_regime()`
- `train()`
- `prepare_training_data()`
- ... và 24 hàm khác


### Utility & Integration

#### 1. strategy_factory.py

Module tạo chiến lược (Strategy Factory)

Module này cung cấp các lớp và hàm để tạo ra các đối tượng chiến lược giao dịch
theo mẫu thiết kế Factory Pattern. Mỗi chiến lược được tạo ra từ factory đều
tuân theo cùng một giao diện (interface), giúp code dễ mở rộng và bảo trì hơn....

**Các lớp chính:**

- `BaseStrategy`
- `RSIStrategy`
- `MACDStrategy`
- `EMACrossStrategy`
- `BollingerBandsStrategy`
- `CompositeStrategy`
- `AutoStrategy`
- `StrategyFactory`

**Các hàm chính:**

- `generate_signal()`
- `update_parameters()`
- `get_name()`
- `get_parameters()`
- `update_performance()`
- ... và 18 hàm khác

#### 2. strategy_integration.py

Module tích hợp chiến thuật giao dịch (Strategy Integration)

Module này tích hợp các chiến thuật giao dịch vào hệ thống chính, đảm bảo rằng
các tín hiệu giao dịch được tạo ra đúng cách và được ghi log đầy đủ....

**Các lớp chính:**

- `StrategyIntegration`

**Các hàm chính:**

- `analyze_market()`
- `get_trading_signal()`
- `analyze_all_markets()`
- `get_market_summary()`
- `get_market_regime()`
- ... và 6 hàm khác


## Tóm tắt các chiến thuật chính

### adaptive_exit_strategy.py

Adaptive Exit Strategy - Chiến lược thoát lệnh thích ứng theo chế độ thị trường

Module này cung cấp các chiến lược thoát lệnh khác nhau tối ưu cho từng chế độ thị trường,...

### adaptive_mode_selector.py

Module thích ứng tự động lựa chọn giữa chế độ hedge mode và single direction
dựa trên điều kiện thị trường hiện tại và backtest...

### adaptive_mode_trader.py

Thực hiện chiến lược giao dịch thích ứng với Hedge Mode và Single Direction
tự động lựa chọn dựa trên điều kiện thị trường...

### adaptive_multi_symbol_controller.py

Bộ điều khiển giao dịch đa cặp tiền thích ứng

Module này điều phối chiến lược giao dịch trên nhiều cặp tiền khác nhau, ...

### adaptive_stop_loss_manager.py

Module quản lý stop loss thích ứng dựa trên phân tích đa khung thời gian

Module này quản lý stop loss và take profit thích ứng dựa trên:...

### adaptive_strategy_selector.py

Module chọn chiến lược thích ứng (Adaptive Strategy Selector)

Module này tự động chọn chiến lược giao dịch phù hợp dựa trên chế độ thị trường,...

### adaptive_volatility_threshold.py

Module điều chỉnh ngưỡng biến động thông minh (Adaptive Volatility Threshold)

Module này cung cấp các hàm để tính toán ngưỡng biến động thông minh cho từng cặp tiền,...

### check_strategy_status.py

Không có mô tả

### composite_trading_strategy.py

Module chiến thuật giao dịch tổng hợp nâng cao (Composite Trading Strategy)

Module này triển khai một chiến thuật giao dịch tổng hợp tiên tiến, kết hợp nhiều chiến lược ...

### enhanced_adaptive_trailing_stop.py

Module Enhanced Adaptive Trailing Stop (EATS)

Module này cung cấp các chiến lược trailing stop nâng cao với khả năng tự động...

### micro_trading_strategy.py

Module chiến lược giao dịch cho tài khoản nhỏ (Micro Trading Strategy)

Module này cung cấp các chiến lược giao dịch được tối ưu hóa cho tài khoản có vốn nhỏ...

### mtf_optimized_strategy.py

Chiến lược giao dịch Bitcoin đa khung thời gian tối ưu hóa

Module này cung cấp chiến lược giao dịch thích ứng đa khung thời gian (MTF), kết hợp phân tích...

### optimized_entry_scheduler.py

Scheduler tự động cho điểm vào lệnh tối ưu

Module này lên lịch thực thi các chiến lược giao dịch dựa trên thời gian tối ưu,...

### optimized_entry_strategy.py

Script tối ưu hóa chiến lược vào lệnh 3-5 lệnh/ngày

Script này phân tích thời điểm tối ưu để vào lệnh trong ngày...

### optimized_strategy.py

Chiến lược giao dịch Bitcoin tối ưu hóa thích ứng với chế độ thị trường

Module này cung cấp chiến lược giao dịch tối ưu hóa dựa trên phân tích chế độ thị trường,...

### sideways_market_strategy.py

Chiến lược chuyên biệt cho thị trường đi ngang (Sideways Market)
    Tối ưu hóa để nâng cao tỷ lệ thắng trong điều kiện thị trường không có xu hướng rõ ràng...

### start_adaptive_trader.py

Script khởi động Adaptive Mode Trader - tự động chọn giữa Hedge Mode và Single Direction...

### strategy_conflict_checker.py

Strategy Conflict Checker - Công cụ kiểm tra xung đột giữa các chiến lược giao dịch
Phát hiện mâu thuẫn tín hiệu, xung đột vị thế và vấn đề chồng chéo lệnh...

### time_optimized_strategy.py

Chiến lược giao dịch tối ưu hóa theo thời gian

Module này tối ưu hóa chiến lược giao dịch dựa trên thời gian...

