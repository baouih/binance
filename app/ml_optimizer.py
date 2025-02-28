import logging
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score
import joblib
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('ml_optimizer')

class MLOptimizer:
    def __init__(self):
        """Initialize the machine learning optimizer."""
        self.models = {}
        self.scaler = StandardScaler()
        self.trained = False
        self.features = None
        
    def train_models(self, X, y):
        """
        Train multiple models on the data.
        
        Args:
            X: Features
            y: Target labels
            
        Returns:
            dict: Dictionary of trained models with their performance metrics
        """
        if X is None or y is None or len(X) < 50:
            logger.warning("Insufficient historical data. Need at least 50 bars.")
            return False
            
        # Log indicator values for debugging
        self._log_feature_values(X)
        
        # Store features for later use
        self.features = X.columns.tolist()
        
        # Normalize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data into train and test sets
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
        
        logger.info(f"Training with {len(X_train) + len(X_test)} samples using {len(X.columns)} features")
        logger.info(f"Label distribution: {y.value_counts()}")
        
        # Define models to train
        models_to_train = {
            'random_forest': RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42),
            'gradient_boosting': GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, max_depth=3, random_state=42),
            'svm': SVC(kernel='rbf', C=1, probability=True, random_state=42)
        }
        
        # Train each model
        for name, model in models_to_train.items():
            logger.info(f"\nTraining {name}...")
            
            # Train the model
            model.fit(X_train, y_train)
            
            # Evaluate on train and test sets
            train_preds = model.predict(X_train)
            test_preds = model.predict(X_test)
            
            train_acc = accuracy_score(y_train, train_preds)
            test_acc = accuracy_score(y_test, test_preds)
            
            # Cross-validation score
            cv_scores = cross_val_score(model, X_scaled, y, cv=5)
            cv_mean = np.mean(cv_scores)
            cv_std = np.std(cv_scores)
            
            # Store model and metrics
            self.models[name] = {
                'model': model,
                'train_accuracy': train_acc,
                'test_accuracy': test_acc,
                'cv_score': cv_mean,
                'cv_std': cv_std
            }
            
            logger.info(f"Train accuracy: {train_acc:.4f}")
            logger.info(f"Test accuracy: {test_acc:.4f}")
            logger.info(f"CV Score: {cv_mean:.4f} (+/- {cv_std:.4f})")
            
        self.trained = True
        return True
        
    def predict(self, X, model_name='ensemble'):
        """
        Make predictions using trained models.
        
        Args:
            X: Features to predict on
            model_name: Which model to use ('ensemble' for average of all models)
            
        Returns:
            tuple: (predictions, probabilities)
        """
        if not self.trained:
            logger.warning("Models not trained yet.")
            return None, 0.5
            
        if len(X) < 50:
            logger.warning("Insufficient historical data. Need at least 50 bars.")
            return None, 0.5
            
        # Check if features match what the model was trained on
        if self.features and not all(feature in X.columns for feature in self.features):
            missing = [f for f in self.features if f not in X.columns]
            logger.warning(f"Missing features in prediction data: {missing}")
            # Add missing features with zeros
            for feature in missing:
                X[feature] = 0
                
        # Reorder columns to match training data
        if self.features:
            X = X[self.features]
            
        # Scale features
        X_scaled = self.scaler.transform(X)
        
        if model_name == 'ensemble':
            # Use all models and average their predictions
            all_probs = []
            
            for name, model_data in self.models.items():
                model = model_data['model']
                # Get class probabilities
                probs = model.predict_proba(X_scaled)
                all_probs.append(probs)
                
            # Average probabilities across models
            avg_probs = np.mean(all_probs, axis=0)
            
            # Get the class with highest probability
            predictions = np.argmax(avg_probs, axis=1)
            
            # Convert from 0, 1, 2 to -1, 0, 1
            predictions = predictions - 1
            
            # Get the max probability for the predicted class
            max_probs = np.max(avg_probs, axis=1)
            
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
            
    def save_models(self, directory='models'):
        """
        Save trained models to disk.
        
        Args:
            directory: Directory to save models in
        """
        if not self.trained:
            logger.warning("No trained models to save.")
            return
            
        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)
        
        # Save scaler
        joblib.dump(self.scaler, os.path.join(directory, 'scaler.pkl'))
        
        # Save feature list
        if self.features:
            pd.Series(self.features).to_csv(os.path.join(directory, 'features.csv'), index=False)
        
        # Save each model
        for name, model_data in self.models.items():
            model = model_data['model']
            joblib.dump(model, os.path.join(directory, f'{name}.pkl'))
            
        logger.info(f"Models saved to {directory}")
        
    def load_models(self, directory='models'):
        """
        Load trained models from disk.
        
        Args:
            directory: Directory to load models from
            
        Returns:
            bool: Success or failure
        """
        try:
            # Load scaler
            self.scaler = joblib.load(os.path.join(directory, 'scaler.pkl'))
            
            # Load feature list
            features_file = os.path.join(directory, 'features.csv')
            if os.path.exists(features_file):
                self.features = pd.read_csv(features_file).iloc[:, 0].tolist()
            
            # Load each model
            self.models = {}
            for model_name in ['random_forest', 'gradient_boosting', 'svm']:
                model_path = os.path.join(directory, f'{model_name}.pkl')
                if os.path.exists(model_path):
                    model = joblib.load(model_path)
                    self.models[model_name] = {'model': model}
                    
            self.trained = len(self.models) > 0
            logger.info(f"Loaded {len(self.models)} models")
            return self.trained
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
            return False
            
    def _log_feature_values(self, X):
        """Log feature values for debugging."""
        logger.info("\nCalculated Technical Indicators:")
        for col in X.columns:
            logger.info(f"{col}: {X[col].iloc[-1]:.4f}")
            
    def get_backtest_signals(self, X):
        """
        Get trading signals for backtesting.
        
        Args:
            X: Feature dataframe
            
        Returns:
            pandas.Series: Trading signals (-1, 0, 1)
        """
        if not self.trained:
            return pd.Series(0, index=X.index)
            
        # Make predictions
        predictions, _ = self.predict(X)
        
        if predictions is None:
            return pd.Series(0, index=X.index)
            
        return pd.Series(predictions, index=X.index)
