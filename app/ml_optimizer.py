import logging
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier, AdaBoostClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.feature_selection import SelectFromModel
from sklearn.decomposition import PCA
import joblib
import os
import time
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ml_optimizer')

class MLOptimizer:
    def __init__(self):
        """Initialize the enhanced machine learning optimizer."""
        self.models = {}
        self.scaler = RobustScaler()  # Improved scaler for outlier resistance
        self.trained = False
        self.features = None
        self.feature_importances = None
        self.market_regime = "unknown"
        self.regime_models = {}
        self.last_train_time = None
        self.pca = None
        self.use_pca = False
        self.pca_components = 0
        self.selected_features = None
        
    def train_models(self, X, y):
        """
        Train multiple models on the data with enhanced features.
        
        Args:
            X: Features dataframe
            y: Target labels
            
        Returns:
            dict: Dictionary of trained models with their performance metrics
        """
        if X is None or y is None or len(X) < 50:
            logger.warning("Insufficient historical data. Need at least 50 bars.")
            return False
            
        # Record training time
        self.last_train_time = datetime.now()
        
        # Log indicator values for debugging
        self._log_feature_values(X)
        
        # Store features for later use
        self.features = X.columns.tolist()
        
        # Apply feature selection if we have many features
        if len(self.features) > 10:
            logger.info("Performing feature selection...")
            self._perform_feature_selection(X, y)
            X = X[self.selected_features]
            logger.info(f"Selected {len(self.selected_features)} features: {self.selected_features}")
        else:
            self.selected_features = self.features
        
        # Normalize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Optionally apply PCA if needed
        if self.use_pca:
            logger.info(f"Applying PCA to reduce dimensionality to {self.pca_components} components")
            self.pca = PCA(n_components=self.pca_components)
            X_scaled = self.pca.fit_transform(X_scaled)
        
        # Split data into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=y)
        
        logger.info(f"Training with {len(X_train) + len(X_test)} samples using {X.shape[1]} features")
        logger.info(f"Label distribution: {y.value_counts()}")
        
        # Define enhanced models to train
        models_to_train = {
            'random_forest': RandomForestClassifier(
                n_estimators=200, 
                max_depth=7, 
                min_samples_split=5,
                min_samples_leaf=2,
                class_weight='balanced', 
                random_state=42
            ),
            'gradient_boosting': GradientBoostingClassifier(
                n_estimators=150, 
                learning_rate=0.05, 
                max_depth=5, 
                subsample=0.8,
                random_state=42
            ),
            'svm': SVC(
                kernel='rbf', 
                C=10, 
                gamma='scale',
                probability=True, 
                class_weight='balanced',
                random_state=42
            ),
            'neural_network': MLPClassifier(
                hidden_layer_sizes=(100, 50), 
                activation='relu',
                solver='adam', 
                alpha=0.0001,
                batch_size='auto',
                learning_rate='adaptive', 
                max_iter=1000,
                random_state=42
            ),
            'adaboost': AdaBoostClassifier(
                n_estimators=100,
                learning_rate=0.1,
                random_state=42
            )
        }
        
        # Train each model with detailed metrics
        for name, model in models_to_train.items():
            logger.info(f"\nTraining {name}...")
            start_time = time.time()
            
            # Train the model
            model.fit(X_train, y_train)
            
            # Evaluate on train and test sets
            train_preds = model.predict(X_train)
            test_preds = model.predict(X_test)
            
            train_acc = accuracy_score(y_train, train_preds)
            test_acc = accuracy_score(y_test, test_preds)
            
            # Additional metrics
            test_precision = precision_score(y_test, test_preds, average='weighted')
            test_recall = recall_score(y_test, test_preds, average='weighted')
            test_f1 = f1_score(y_test, test_preds, average='weighted')
            
            # Confusion matrix
            cm = confusion_matrix(y_test, test_preds)
            
            # Cross-validation score
            cv_scores = cross_val_score(model, X_scaled, y, cv=5)
            cv_mean = np.mean(cv_scores)
            cv_std = np.std(cv_scores)
            
            training_time = time.time() - start_time
            
            # Store model and metrics
            self.models[name] = {
                'model': model,
                'train_accuracy': train_acc,
                'test_accuracy': test_acc,
                'precision': test_precision,
                'recall': test_recall,
                'f1_score': test_f1,
                'confusion_matrix': cm,
                'cv_score': cv_mean,
                'cv_std': cv_std,
                'training_time': training_time
            }
            
            logger.info(f"Train accuracy: {train_acc:.4f}")
            logger.info(f"Test accuracy: {test_acc:.4f}")
            logger.info(f"Precision: {test_precision:.4f}")
            logger.info(f"Recall: {test_recall:.4f}")
            logger.info(f"F1 Score: {test_f1:.4f}")
            logger.info(f"CV Score: {cv_mean:.4f} (+/- {cv_std:.4f})")
            logger.info(f"Training time: {training_time:.2f} seconds")
            logger.info(f"Confusion Matrix:\n{cm}")
        
        # Create a voting ensemble from the trained models
        logger.info("\nCreating ensemble model...")
        ensemble = self._create_ensemble()
        
        # Train the ensemble
        ensemble.fit(X_train, y_train)
        
        # Evaluate the ensemble
        ensemble_train_preds = ensemble.predict(X_train)
        ensemble_test_preds = ensemble.predict(X_test)
        
        ensemble_train_acc = accuracy_score(y_train, ensemble_train_preds)
        ensemble_test_acc = accuracy_score(y_test, ensemble_test_preds)
        
        # Additional metrics for ensemble
        ensemble_precision = precision_score(y_test, ensemble_test_preds, average='weighted')
        ensemble_recall = recall_score(y_test, ensemble_test_preds, average='weighted')
        ensemble_f1 = f1_score(y_test, ensemble_test_preds, average='weighted')
        ensemble_cm = confusion_matrix(y_test, ensemble_test_preds)
        
        # Store ensemble model
        self.models['ensemble'] = {
            'model': ensemble,
            'train_accuracy': ensemble_train_acc,
            'test_accuracy': ensemble_test_acc,
            'precision': ensemble_precision,
            'recall': ensemble_recall,
            'f1_score': ensemble_f1,
            'confusion_matrix': ensemble_cm
        }
        
        logger.info(f"Ensemble Train accuracy: {ensemble_train_acc:.4f}")
        logger.info(f"Ensemble Test accuracy: {ensemble_test_acc:.4f}")
        logger.info(f"Ensemble Precision: {ensemble_precision:.4f}")
        logger.info(f"Ensemble Recall: {ensemble_recall:.4f}")
        logger.info(f"Ensemble F1 Score: {ensemble_f1:.4f}")
        logger.info(f"Ensemble Confusion Matrix:\n{ensemble_cm}")
        
        # Store feature importances if Random Forest was trained
        if 'random_forest' in self.models:
            rf_model = self.models['random_forest']['model']
            self.feature_importances = dict(zip(self.selected_features, rf_model.feature_importances_))
            top_features = sorted(self.feature_importances.items(), key=lambda x: x[1], reverse=True)
            logger.info("\nFeature Importances:")
            for feature, importance in top_features:
                logger.info(f"{feature}: {importance:.4f}")
        
        self.trained = True
        logger.info(f"Model training completed successfully")
        return True
    
    def _perform_feature_selection(self, X, y):
        """Perform feature selection using Random Forest"""
        selector = SelectFromModel(RandomForestClassifier(n_estimators=100, random_state=42), threshold='median')
        selector.fit(X, y)
        
        # Get selected features
        selected_features_mask = selector.get_support()
        self.selected_features = X.columns[selected_features_mask].tolist()
    
    def _create_ensemble(self):
        """Create a Voting Classifier ensemble from individually trained models"""
        estimators = []
        
        # Add models to the ensemble
        for name, model_data in self.models.items():
            estimators.append((name, model_data['model']))
        
        # Create and return the voting classifier
        return VotingClassifier(estimators=estimators, voting='soft')
        
    def predict(self, X, model_name='ensemble'):
        """
        Make predictions using trained models with enhanced error handling.
        
        Args:
            X: Features to predict on
            model_name: Which model to use ('ensemble' for average of all models)
            
        Returns:
            tuple: (predictions, probabilities)
        """
        if not self.trained:
            logger.warning("Models not trained yet.")
            return None, 0.5
        
        try:
            # Handle empty dataframe
            if X is None or X.empty:
                logger.warning("Empty feature dataframe provided")
                return None, 0.5
            
            # Deep copy to avoid modifying original
            X = X.copy()
            
            # Check if features match what the model was trained on
            if self.selected_features and not all(feature in X.columns for feature in self.selected_features):
                missing = [f for f in self.selected_features if f not in X.columns]
                logger.warning(f"Missing features in prediction data: {missing}")
                # Add missing features with zeros
                for feature in missing:
                    X[feature] = 0
            
            # Handle extra features not used in training
            extra_features = [f for f in X.columns if f not in self.selected_features]
            if extra_features:
                logger.debug(f"Removing extra features not used in training: {extra_features}")
                X = X[self.selected_features]
            
            # Reorder columns to match training data
            X = X[self.selected_features]
            
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Apply PCA if it was used in training
            if self.use_pca and self.pca is not None:
                X_scaled = self.pca.transform(X_scaled)
            
            # Detect current market regime for regime-specific models
            self._detect_market_regime(X)
            
            # Use regime-specific model if available
            if model_name == 'regime' and self.market_regime in self.regime_models:
                logger.info(f"Using {self.market_regime} regime-specific model")
                model_data = self.regime_models[self.market_regime]
                model = model_data['model']
                
                # Get predictions
                predictions = model.predict(X_scaled)
                probabilities = model.predict_proba(X_scaled)
                max_probs = np.max(probabilities, axis=1)
                
                return predictions, max_probs
            
            # Use ensemble (default) or specific model
            if model_name == 'ensemble' and 'ensemble' in self.models:
                model = self.models['ensemble']['model']
                
                # Get predictions
                predictions = model.predict(X_scaled)
                probabilities = model.predict_proba(X_scaled)
                
                # Get max probability for each prediction
                max_probs = np.max(probabilities, axis=1)
                
                return predictions, max_probs
                
            elif model_name in self.models:
                model = self.models[model_name]['model']
                
                # Get predictions and probabilities
                predictions = model.predict(X_scaled)
                probabilities = model.predict_proba(X_scaled)
                
                # Get the max probability for each prediction
                max_probs = np.max(probabilities, axis=1)
                
                return predictions, max_probs
            else:
                logger.warning(f"Model {model_name} not found. Available models: {list(self.models.keys())}")
                return None, 0.5
                
        except Exception as e:
            logger.error(f"Error during prediction: {str(e)}")
            return None, 0.5
    
    def _detect_market_regime(self, X):
        """Detect current market regime based on technical indicators"""
        try:
            # Extract the latest row
            latest = X.iloc[-1]
            
            # Check for trend indicators if available
            volatility = latest.get('Price_Volatility', 0)
            trend_strength = latest.get('Trend_Strength', 0)
            volume_trend = latest.get('Volume_Trend', 0)
            adx = latest.get('ADX', 0)
            
            # Detect regime
            if volatility > 0.03 and abs(trend_strength) < 0.3:
                self.market_regime = "volatile"
            elif adx > 25 and trend_strength > 0.5:
                self.market_regime = "trending_up"
            elif adx > 25 and trend_strength < -0.5:
                self.market_regime = "trending_down"
            elif abs(trend_strength) < 0.2 and volatility < 0.02:
                self.market_regime = "ranging"
            else:
                self.market_regime = "neutral"
                
            logger.debug(f"Detected market regime: {self.market_regime}")
            
        except Exception as e:
            logger.error(f"Error detecting market regime: {str(e)}")
            self.market_regime = "unknown"
            
    def save_models(self, directory='models'):
        """
        Save trained models to disk with enhanced metadata.
        
        Args:
            directory: Directory to save models in
        """
        if not self.trained:
            logger.warning("No trained models to save.")
            return
            
        try:
            # Create directory if it doesn't exist
            os.makedirs(directory, exist_ok=True)
            
            # Save scaler
            joblib.dump(self.scaler, os.path.join(directory, 'scaler.pkl'))
            
            # Save feature list
            if self.selected_features:
                pd.Series(self.selected_features).to_csv(os.path.join(directory, 'features.csv'), index=False)
            
            # Save PCA if used
            if self.use_pca and self.pca is not None:
                joblib.dump(self.pca, os.path.join(directory, 'pca.pkl'))
            
            # Save feature importances if available
            if self.feature_importances:
                pd.Series(self.feature_importances).to_csv(os.path.join(directory, 'feature_importances.csv'))
            
            # Save metadata
            metadata = {
                'training_time': self.last_train_time.isoformat() if self.last_train_time else None,
                'feature_count': len(self.selected_features) if self.selected_features else 0,
                'use_pca': self.use_pca,
                'pca_components': self.pca_components if self.use_pca else 0,
                'model_metrics': {name: {k: v for k, v in data.items() if k != 'model'} 
                                 for name, data in self.models.items()},
                'market_regimes': list(self.regime_models.keys())
            }
            pd.Series(metadata).to_json(os.path.join(directory, 'metadata.json'))
            
            # Save each model
            for name, model_data in self.models.items():
                model = model_data['model']
                joblib.dump(model, os.path.join(directory, f'{name}.pkl'))
            
            # Save regime-specific models
            for regime, model_data in self.regime_models.items():
                model = model_data['model']
                joblib.dump(model, os.path.join(directory, f'regime_{regime}.pkl'))
                
            logger.info(f"Models saved to {directory}")
            
        except Exception as e:
            logger.error(f"Error saving models: {str(e)}")
        
    def load_models(self, directory='models'):
        """
        Load trained models from disk with enhanced error handling.
        
        Args:
            directory: Directory to load models from
            
        Returns:
            bool: Success or failure
        """
        try:
            # Load scaler
            scaler_path = os.path.join(directory, 'scaler.pkl')
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
            else:
                logger.warning(f"Scaler file not found: {scaler_path}")
                return False
            
            # Load feature list
            features_file = os.path.join(directory, 'features.csv')
            if os.path.exists(features_file):
                self.selected_features = pd.read_csv(features_file).iloc[:, 0].tolist()
                self.features = self.selected_features
            
            # Load PCA if it exists
            pca_path = os.path.join(directory, 'pca.pkl')
            if os.path.exists(pca_path):
                self.pca = joblib.load(pca_path)
                self.use_pca = True
                if self.pca:
                    self.pca_components = self.pca.n_components_
            
            # Load feature importances if available
            importances_file = os.path.join(directory, 'feature_importances.csv')
            if os.path.exists(importances_file):
                importances = pd.read_csv(importances_file)
                self.feature_importances = dict(zip(importances.iloc[:, 0], importances.iloc[:, 1]))
            
            # Load main models
            self.models = {}
            model_names = ['random_forest', 'gradient_boosting', 'svm', 'neural_network', 'adaboost', 'ensemble']
            loaded_count = 0
            
            for model_name in model_names:
                model_path = os.path.join(directory, f'{model_name}.pkl')
                if os.path.exists(model_path):
                    try:
                        model = joblib.load(model_path)
                        self.models[model_name] = {'model': model}
                        loaded_count += 1
                    except Exception as e:
                        logger.warning(f"Could not load model {model_name}: {str(e)}")
            
            # Load regime-specific models
            self.regime_models = {}
            for regime in ['trending_up', 'trending_down', 'volatile', 'ranging', 'neutral']:
                regime_path = os.path.join(directory, f'regime_{regime}.pkl')
                if os.path.exists(regime_path):
                    try:
                        model = joblib.load(regime_path)
                        self.regime_models[regime] = {'model': model}
                    except Exception as e:
                        logger.warning(f"Could not load regime model {regime}: {str(e)}")
            
            # Load metadata if available
            metadata_file = os.path.join(directory, 'metadata.json')
            if os.path.exists(metadata_file):
                try:
                    metadata = pd.read_json(metadata_file, typ='series')
                    if 'training_time' in metadata and metadata['training_time']:
                        self.last_train_time = datetime.fromisoformat(metadata['training_time'])
                    
                    # Add model metrics from metadata
                    if 'model_metrics' in metadata:
                        metrics = metadata['model_metrics']
                        for model_name, model_metrics in metrics.items():
                            if model_name in self.models:
                                self.models[model_name].update(model_metrics)
                except Exception as e:
                    logger.warning(f"Could not load metadata: {str(e)}")
            
            self.trained = loaded_count > 0
            logger.info(f"Loaded {loaded_count} models and {len(self.regime_models)} regime-specific models")
            return self.trained
            
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
            return False
    
    def train_regime_specific_model(self, X, y, regime):
        """
        Train a model specific to a market regime.
        
        Args:
            X: Features
            y: Target labels
            regime: Market regime string (e.g., 'trending_up', 'volatile')
            
        Returns:
            bool: Success status
        """
        try:
            logger.info(f"Training regime-specific model for {regime}...")
            
            # Apply feature selection
            if len(X.columns) > 10:
                selector = SelectFromModel(RandomForestClassifier(n_estimators=100, random_state=42), threshold='median')
                selector.fit(X, y)
                
                # Get selected features
                selected_features_mask = selector.get_support()
                selected_features = X.columns[selected_features_mask].tolist()
                X = X[selected_features]
                logger.info(f"Selected {len(selected_features)} features for {regime} model")
            
            # Scale features
            X_scaled = self.scaler.transform(X)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42, stratify=y)
            
            # Define a regime-optimized model
            if regime == 'trending_up' or regime == 'trending_down':
                # For trending markets, use GradientBoosting
                model = GradientBoostingClassifier(
                    n_estimators=150, 
                    learning_rate=0.05, 
                    max_depth=5,
                    subsample=0.8, 
                    random_state=42
                )
            elif regime == 'volatile':
                # For volatile markets, use Random Forest with deeper trees
                model = RandomForestClassifier(
                    n_estimators=200, 
                    max_depth=8, 
                    min_samples_split=5,
                    class_weight='balanced', 
                    random_state=42
                )
            elif regime == 'ranging':
                # For ranging markets, use SVM
                model = SVC(
                    kernel='rbf', 
                    C=10, 
                    gamma='scale',
                    probability=True, 
                    class_weight='balanced',
                    random_state=42
                )
            else:  # neutral
                # For neutral markets, use ensemble
                model = VotingClassifier(estimators=[
                    ('rf', RandomForestClassifier(n_estimators=100, random_state=42)),
                    ('gb', GradientBoostingClassifier(n_estimators=100, random_state=42)),
                    ('svm', SVC(probability=True, random_state=42))
                ], voting='soft')
            
            # Train the model
            model.fit(X_train, y_train)
            
            # Evaluate
            train_preds = model.predict(X_train)
            test_preds = model.predict(X_test)
            
            train_acc = accuracy_score(y_train, train_preds)
            test_acc = accuracy_score(y_test, test_preds)
            
            # Calculate additional metrics
            test_precision = precision_score(y_test, test_preds, average='weighted')
            test_recall = recall_score(y_test, test_preds, average='weighted')
            test_f1 = f1_score(y_test, test_preds, average='weighted')
            
            # Log performance
            logger.info(f"{regime} model performance:")
            logger.info(f"Train accuracy: {train_acc:.4f}")
            logger.info(f"Test accuracy: {test_acc:.4f}")
            logger.info(f"Precision: {test_precision:.4f}")
            logger.info(f"Recall: {test_recall:.4f}")
            logger.info(f"F1 Score: {test_f1:.4f}")
            
            # Store the model
            self.regime_models[regime] = {
                'model': model,
                'train_accuracy': train_acc,
                'test_accuracy': test_acc,
                'precision': test_precision,
                'recall': test_recall,
                'f1_score': test_f1
            }
            
            return True
            
        except Exception as e:
            logger.error(f"Error training regime-specific model for {regime}: {str(e)}")
            return False
            
    def _log_feature_values(self, X):
        """Log feature values for debugging with improved formatting."""
        logger.info("\nCalculated Technical Indicators:")
        
        # Format in a table-like structure for better readability
        if not X.empty:
            latest = X.iloc[-1]
            
            # Group features by type
            price_features = [col for col in X.columns if 'price' in col.lower() or 'close' in col.lower()]
            trend_features = [col for col in X.columns if 'trend' in col.lower() or 'ema' in col.lower() or 'ma' in col.lower()]
            oscillator_features = [col for col in X.columns if 'rsi' in col.lower() or 'macd' in col.lower() or 'stoch' in col.lower()]
            volume_features = [col for col in X.columns if 'volume' in col.lower()]
            volatility_features = [col for col in X.columns if 'volatility' in col.lower() or 'atr' in col.lower() or 'bb' in col.lower()]
            other_features = [col for col in X.columns if col not in price_features + trend_features + oscillator_features + volume_features + volatility_features]
            
            feature_groups = [
                ("Price", price_features),
                ("Trend", trend_features),
                ("Oscillators", oscillator_features),
                ("Volume", volume_features),
                ("Volatility", volatility_features),
                ("Other", other_features)
            ]
            
            for group_name, features in feature_groups:
                if features:
                    logger.info(f"--- {group_name} Indicators ---")
                    for feature in features:
                        value = latest.get(feature, np.nan)
                        if isinstance(value, (int, float)) and not np.isnan(value):
                            logger.info(f"{feature}: {value:.4f}")
                        else:
                            logger.info(f"{feature}: {value}")
            
    def get_backtest_signals(self, X):
        """
        Get trading signals for backtesting with enhanced regime detection.
        
        Args:
            X: Feature dataframe
            
        Returns:
            pandas.Series: Trading signals (-1, 0, 1)
        """
        if not self.trained:
            return pd.Series(0, index=X.index)
        
        try:
            # Detect market regimes first
            regimes = []
            signals = []
            probas = []
            
            # Process each row individually to detect regime changes
            for i in range(len(X)):
                row_df = X.iloc[[i]]
                
                # Detect regime for this specific time point
                self._detect_market_regime(row_df)
                regimes.append(self.market_regime)
                
                # Use regime-specific model if available
                if self.market_regime in self.regime_models:
                    regime_model = self.regime_models[self.market_regime]['model']
                    
                    # Prepare the data (ensure all required features are present)
                    if self.selected_features and not all(feature in row_df.columns for feature in self.selected_features):
                        missing = [f for f in self.selected_features if f not in row_df.columns]
                        for feature in missing:
                            row_df[feature] = 0
                    
                    row_scaled = self.scaler.transform(row_df[self.selected_features])
                    
                    # Apply PCA if used in training
                    if self.use_pca and self.pca is not None:
                        row_scaled = self.pca.transform(row_scaled)
                    
                    # Get prediction
                    pred = regime_model.predict(row_scaled)[0]
                    proba = np.max(regime_model.predict_proba(row_scaled)[0])
                    
                else:
                    # Use ensemble model as fallback
                    pred, proba = self.predict(row_df)
                    if pred is None:
                        pred = 0
                        proba = 0.5
                    else:
                        pred = pred[0]
                        proba = proba[0]
                
                signals.append(pred)
                probas.append(proba)
            
            # Create a DataFrame with signals and regimes
            result_df = pd.DataFrame({
                'signal': signals,
                'probability': probas,
                'regime': regimes
            }, index=X.index)
            
            # Apply confidence filtering - only keep high confidence signals
            threshold = 0.65  # Minimum probability threshold
            result_df['filtered_signal'] = np.where(
                result_df['probability'] >= threshold,
                result_df['signal'],
                0  # Hold when confidence is low
            )
            
            # Add support for reducing signal frequency to avoid overtrading
            # (optional, can be enabled if needed)
            # result_df['smoothed_signal'] = result_df['filtered_signal'].rolling(3).apply(lambda x: x[2] if x[0] == x[1] == x[2] else 0)
            
            return result_df['filtered_signal']
            
        except Exception as e:
            logger.error(f"Error generating backtest signals: {str(e)}")
            return pd.Series(0, index=X.index)

    def optimize_hyperparameters(self, X, y, model_type='random_forest'):
        """
        Optimize hyperparameters for a specific model type.
        
        Args:
            X: Features
            y: Target labels
            model_type: Type of model to optimize
            
        Returns:
            dict: Optimized parameters
        """
        logger.info(f"Optimizing hyperparameters for {model_type}...")
        
        # Apply feature selection first
        if len(X.columns) > 10:
            selector = SelectFromModel(RandomForestClassifier(n_estimators=100, random_state=42), threshold='median')
            selector.fit(X, y)
            selected_features_mask = selector.get_support()
            selected_features = X.columns[selected_features_mask].tolist()
            X = X[selected_features]
            
        # Normalize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Define parameter grids for different models
        param_grids = {
            'random_forest': {
                'n_estimators': [100, 200, 300],
                'max_depth': [None, 5, 7, 10],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4],
                'class_weight': [None, 'balanced']
            },
            'gradient_boosting': {
                'n_estimators': [100, 150, 200],
                'learning_rate': [0.01, 0.05, 0.1],
                'max_depth': [3, 5, 7],
                'subsample': [0.7, 0.8, 0.9]
            },
            'svm': {
                'C': [0.1, 1, 10, 100],
                'gamma': ['scale', 'auto', 0.01, 0.1],
                'kernel': ['rbf', 'poly'],
                'class_weight': [None, 'balanced']
            },
            'neural_network': {
                'hidden_layer_sizes': [(50,), (100,), (50, 50), (100, 50)],
                'activation': ['relu', 'tanh'],
                'alpha': [0.0001, 0.001, 0.01],
                'learning_rate': ['constant', 'adaptive']
            }
        }
        
        # Base models
        base_models = {
            'random_forest': RandomForestClassifier(random_state=42),
            'gradient_boosting': GradientBoostingClassifier(random_state=42),
            'svm': SVC(probability=True, random_state=42),
            'neural_network': MLPClassifier(max_iter=1000, random_state=42)
        }
        
        if model_type not in param_grids:
            logger.warning(f"Model type {model_type} not supported for optimization")
            return None
        
        # Run grid search
        grid_search = GridSearchCV(
            base_models[model_type],
            param_grids[model_type],
            cv=5,
            scoring='f1_weighted',
            n_jobs=-1,
            verbose=1
        )
        
        grid_search.fit(X_scaled, y)
        
        # Get best parameters
        best_params = grid_search.best_params_
        best_score = grid_search.best_score_
        
        logger.info(f"Best parameters for {model_type}: {best_params}")
        logger.info(f"Best CV score: {best_score:.4f}")
        
        return best_params
