# model.py
"""
Hierarchical Bayesian model for keyboard layout preference learning.

Core functionality:
  - Bayesian inference using Bradley-Terry preference model structure:
    - Feature-based comfort score estimation
    - Participant-level random effects
    - Uncertainty quantification via MCMC sampling
    - Stan backend integration
    - Automated resource management

Key components:
  1. Sequential Feature Selection:
    - Round-robin comparison of features
    - Context-aware evaluation with previously selected features
    - Three independent metrics:
      * Model effect magnitude
      * Effect consistency across cross-validation
      * Predictive power
    - Feature interaction handling
    - Control feature separation

  2. Model Operations:
    - Efficient data preparation for Stan
    - MCMC sampling with diagnostics
    - Cross-validation with participant grouping
    - Feature weight extraction and caching
    - Memory usage optimization

  3. Prediction Pipeline:
    - Bigram comfort score estimation
    - Preference probability prediction
    - Uncertainty quantification
    - Cached predictions for efficiency
    - Baseline model handling

  4. Evaluation Mechanisms:
    - Classification metrics (accuracy, AUC)
    - Effect size estimation
    - Cross-validation stability
    - Model diagnostics
    - Transitivity checks
    - Parameter convergence monitoring

  5. Output Handling:
    - Detailed metric reporting
    - State serialization
    - Comprehensive logging
    - CSV export capabilities
    - Diagnostic information export

Classes:
    PreferenceModel: Main class implementing the Bayesian preference learning pipeline
        Methods:
            fit(): Train model on preference data
            predict_preference(): Generate predictions for bigram pairs
            evaluate(): Compute model performance metrics
            cross_validate(): Perform cross-validation analysis
            save()/load(): Model serialization

Example:
    >>> model = PreferenceModel(config)
    >>> model.fit(dataset)
    >>> prediction = model.predict_preference("th", "he")
    >>> print(f"Preference probability: {prediction.probability:.2f} ± {prediction.uncertainty:.2f}")

Notes:
    - Features are pre-normalized except typing_time
    - Uses participant-based cross-validation splits
    - Thread-safe Stan implementation
    - Comprehensive error handling
    - Detailed logging system
    - Automatic resource cleanup
    - Memory usage monitoring
    - Temporary file management

Dependencies:
    - cmdstanpy: Stan model compilation and sampling
    - numpy: Numerical computations
    - pandas: Data management
    - sklearn: Evaluation metrics
    - psutil: Resource monitoring
"""
import cmdstanpy
import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import KFold
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import pandas as pd
import time  # Needed for computation_time in predict_preference
import pickle
import copy
from pathlib import Path
from itertools import combinations
import traceback
from collections import defaultdict
import tempfile
import shutil
import psutil
from tenacity import retry, stop_after_attempt, wait_fixed
import gc
from contextlib import contextmanager

from engram3.utils.config import Config, NotFittedError, FeatureError, ModelPrediction
from engram3.data import PreferenceDataset
from engram3.features.feature_importance import FeatureImportanceCalculator
from engram3.utils.visualization import PlottingUtils
from engram3.utils.caching import CacheManager
from engram3.utils.logging import LoggingManager
logger = LoggingManager.getLogger(__name__)

class PreferenceModel:
    # Class variable for cache storage
    _feature_data_cache_: Dict[str, Dict[str, np.ndarray]] = {}

    #--------------------------------------------
    # Core model methods
    #--------------------------------------------   
    def __init__(self, config: Union[Dict, Config] = None):
        """Initialize PreferenceModel."""
        if config is None:
            raise ValueError("Config is required")
        
        self.config = config if isinstance(config, Config) else Config(**config)
        
        # Initialize basic attributes
        self.fit_result = None
        self.feature_names = None
        self.selected_features = []
        self.interaction_metadata = {}
        self.dataset = None
        self.feature_weights = None
        self.feature_extractor = None
        self.is_baseline_model = False
        self._importance_calculator = None  # Use underscore for private attribute
        
        # Initialize caches
        self.feature_cache = CacheManager()
        self.prediction_cache = CacheManager()
        
        # Initialize visualization
        self.plotting = PlottingUtils(self.config.paths.plots_dir)

        # Initialize Stan model
        try:
            model_path = Path(__file__).parent / "models" / "preference_model.stan"
            if not model_path.exists():
                raise FileNotFoundError(f"Stan model file not found: {model_path}")
                
            output_dir = Path(self.config.paths.root_dir) / "stan_temp"
            output_dir.mkdir(parents=True, exist_ok=True)
                
            self.model = cmdstanpy.CmdStanModel(
                stan_file=str(model_path),
                cpp_options={'STAN_THREADS': True},
                stanc_options={'warn-pedantic': True}
            )
                
            if hasattr(self.model, 'exe_file'):
                exe_path = Path(self.model.exe_file)
                if exe_path.exists():
                    exe_path.chmod(0o755)

        except Exception as e:
            print(f"Error initializing Stan model: {str(e)}")
            raise

    @property 
    def importance_calculator(self):
        if self._importance_calculator is None:
            self._importance_calculator = FeatureImportanceCalculator(self.config, self)
        return self._importance_calculator

    @importance_calculator.setter
    def importance_calculator(self, value):
        self._importance_calculator = value
               
    # Property decorators
    @property
    def feature_scale(self) -> float:
        """Prior scale for feature weights."""
        return self.config.model.feature_scale
        
    @property
    def participant_scale(self) -> float:
        """Prior scale for participant effects."""
        return self.config.model.participant_scale
        
    @property
    def _feature_data_cache(self) -> Dict[str, Dict[str, np.ndarray]]:
        """Access feature data cache with initialization check."""
        return self._feature_data_cache_

    def _create_temp_model(self):
        """Create a temporary model copy for evaluation."""
        temp_model = type(self)(config=self.config)
        # Copy necessary attributes
        temp_model.feature_extractor = self.feature_extractor
        temp_model.dataset = self.dataset
        temp_model.prediction_cache = CacheManager()
        
        # Copy dataset attributes
        for attr in ['column_map', 'row_map', 'finger_map', 
                    'engram_position_values', 'row_position_values',
                    'angles', 'bigrams', 'bigram_frequencies_array']:
            if hasattr(self.dataset, attr):
                setattr(temp_model.dataset, attr, getattr(self.dataset, attr))
        
        # Create context manager for cleanup
        class ModelContext:
            def __init__(self, model):
                self.model = model
            def __enter__(self):
                return self.model
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.model.cleanup()
                if hasattr(self.model, 'prediction_cache'):
                    self.model.prediction_cache.clear()
                    
        return ModelContext(temp_model)

    # Remaining class methods
    def clear_caches(self) -> None:
        """Clear all caches to free memory."""
        self.feature_cache.clear()
        self.prediction_cache.clear()

    def _check_memory(self, required_gb=8):
        """Check available system memory"""
        mem = psutil.virtual_memory()
        if mem.available < required_gb * 1024**3:
            raise RuntimeError(f"Insufficient memory: {mem.available/(1024**3):.1f}GB free, need {required_gb}GB")

    def _check_temp_space(self):
        required_mb = self.config.model.required_temp_mb  # Default value is already 2000
        temp_dir = Path(tempfile.gettempdir())
        total, used, free = shutil.disk_usage(temp_dir)
        free_mb = free // (1024 * 1024)
        if free_mb < required_mb:
            raise RuntimeError(f"Insufficient temporary space: {free_mb}MB free, need {required_mb}MB")
                    
    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2))
    def _sample_with_retry(self, **kwargs):
        """Attempt sampling with retries on failure"""
        return self.model.sample(**kwargs)

    def fit(self, dataset: PreferenceDataset, features: Optional[List[str]] = None,
            fit_purpose: Optional[str] = None) -> None:
        """Fit model with specified features."""
        try:
            # Store feature names
            self.feature_names = features
            
            # Compute and store feature statistics
            self.feature_stats = self._compute_feature_statistics(dataset)

            # Cleanup before fitting
            for attr in ['fit_result', 'feature_weights']:
                if hasattr(self, attr):
                    delattr(self, attr)

            if fit_purpose:
                logger.info(f"Fitting model: {fit_purpose}")

            # Store dataset and feature extractor
            self.dataset = dataset
            self.feature_extractor = dataset.feature_extractor
            
            # Validate and process features
            if not features:
                features = dataset.get_feature_names()
            if not features:
                raise ValueError("No features provided and none available from dataset")
            
            # Ensure proper feature handling
            control_features = self.config.features.control_features
            main_features = [f for f in features if f not in control_features]
            
            logger.info(f"Main features ({len(main_features)}): {main_features}")
            logger.info(f"Control features ({len(control_features)}): {control_features}")

            # Prepare feature matrices for Stan
            processed_data = self._prepare_feature_matrices(
                dataset=dataset,
                main_features=main_features,
                control_features=control_features
            )

            # Store feature information
            self.feature_names = main_features + list(control_features)
            self.selected_features = main_features + list(control_features)

            # Log data dimensions
            #logger.info("Data dimensions:")
            #logger.info(f"  Preferences: {processed_data['N']}")
            #logger.info(f"  Participants: {processed_data['P']}")  # Changed to use 'P'
            #if not main_features:
            #    logger.info("  Using dummy main feature for control-only model")
            #logger.info(f"  Main features: {processed_data['F']}")
            #logger.info(f"  Control features: {processed_data['C']}")

            # Log sampling configuration
            #logger.info("Starting sampling with "
            #        f"{self.config.model.chains} chains, "
            #        f"{self.config.model.warmup} warmup iterations, "
            #        f"{self.config.model.n_samples} sampling iterations"
            #        f"{f' ({fit_purpose})' if fit_purpose else ''}")

            # Stan sampling
            self.fit_result = self._sample_with_retry(
                data=processed_data,
                chains=self.config.model.chains,
                iter_warmup=self.config.model.warmup,
                iter_sampling=self.config.model.n_samples,
                adapt_delta=self.config.model.adapt_delta,
                max_treedepth=self.config.model.max_treedepth
            )

            self._update_feature_weights()

        except Exception as e:
            logger.error(f"Error in fit: {str(e)}")
            logger.error("Traceback:", exc_info=True)
            raise
                    
    def _update_feature_weights(self) -> None:
        """Update feature weights from fitted model for both main and control features."""
        try:
            self.feature_weights = {}
            
            if not hasattr(self, 'fit_result'):
                raise ValueError("Model not fitted. Call fit() first.")
            
            # Get main feature weights (beta) if any exist
            main_features = list(dict.fromkeys(
                [f for f in self.feature_names if f not in self.config.features.control_features]
            ))
            
            if main_features:  # Only process beta if we have main features
                beta = self.fit_result.stan_variable('beta')
                logger.debug(f"Beta shape: {beta.shape}")
                logger.debug(f"Main features: {main_features}")
                
                if beta.shape[1] != len(main_features):
                    raise ValueError(f"Beta shape mismatch: {beta.shape[1]} != {len(main_features)}")
                
                # Update weights for main features
                for i, feature in enumerate(main_features):
                    self.feature_weights[feature] = (
                        float(np.mean(beta[:, i])),
                        float(np.std(beta[:, i]))
                    )
            
            # Get control feature weights (gamma) if any exist
            control_features = list(dict.fromkeys(self.config.features.control_features))
            if control_features:
                try:
                    gamma = self.fit_result.stan_variable('gamma')
                    if gamma.shape[1] != len(control_features):
                        raise ValueError(f"Gamma shape mismatch: {gamma.shape[1]} != {len(control_features)}")
                        
                    for i, feature in enumerate(control_features):
                        self.feature_weights[feature] = (
                            float(np.mean(gamma[:, i])),
                            float(np.std(gamma[:, i]))
                        )
                except Exception as e:
                    logger.error(f"Error processing control features: {str(e)}")
                    raise

            logger.debug("Updated weights:")
            for feature, (mean, std) in self.feature_weights.items():
                feature_type = "control" if feature in control_features else "main"
                logger.debug(f"  {feature} ({feature_type}): {mean:.4f} ± {std:.4f}")
                    
        except Exception as e:
            logger.error(f"Error updating feature weights: {str(e)}")
            raise
                                                                            
    def evaluate(self, dataset: PreferenceDataset) -> Dict[str, float]:
        """Evaluate model performance."""
        try:
            if not hasattr(self, 'fit_result'):
                raise ValueError("Model not fitted")
            
            # Get predictions
            predictions = []
            true_labels = []
            
            for pref in dataset.preferences:
                # Get prediction
                pred = self.predict_preference(pref.bigram1, pref.bigram2)
                
                # Store logit for AUC calculation
                logit = -np.log(1/pred.probability - 1)
                predictions.append(logit)
                true_labels.append(float(pref.preferred))
                
            predictions = np.array(predictions)
            true_labels = np.array(true_labels)
            
            # Compute metrics
            accuracy = np.mean((predictions > 0) == true_labels)  # Use 0 as threshold for logits
            auc = roc_auc_score(true_labels, predictions)
            
            logger.info(f"Prediction distribution:")
            logger.info(f"  Mean: {np.mean(predictions):.4f}")
            logger.info(f"  Std: {np.std(predictions):.4f}")
            logger.info(f"  Min: {np.min(predictions):.4f}")
            logger.info(f"  Max: {np.max(predictions):.4f}")
            
            return {
                'accuracy': float(accuracy),
                'auc': float(auc),
                'mean_pred': float(np.mean(predictions)),
                'std_pred': float(np.std(predictions))
            }
        
        except Exception as e:
            logger.error(f"Error in evaluate: {str(e)}")
            return {'accuracy': 0.5, 'auc': 0.5, 'mean_pred': 0.0, 'std_pred': 1.0}
                                                        
    def cross_validate(self, dataset: PreferenceDataset, n_splits: Optional[int] = None) -> Dict[str, Any]:
        """Perform cross-validation with multiple validation strategies."""
        feature_names = dataset.get_feature_names()
        logger.debug(f"Features for cross-validation (including interactions): {feature_names}")
        
        metrics = defaultdict(list)
        feature_effects = defaultdict(list)
        
        # Get CV splits using shared method
        for fold, (train_idx, val_idx) in enumerate(self._get_cv_splits(dataset, n_splits)):
            try:
                # Clear caches before each fold to prevent memory buildup
                self.clear_caches()
                logger.info(f"Processing fold {fold + 1}/{n_splits}")
                
                # Create train/val datasets
                train_data = dataset._create_subset_dataset(train_idx)
                val_data = dataset._create_subset_dataset(val_idx)
                
                if len(train_data.preferences) == 0 or len(val_data.preferences) == 0:
                    logger.warning(f"Empty split in fold {fold + 1}, skipping")
                    continue
                
                # Fit Bayesian model on training data
                self.fit_result(train_data)
                
                # Get predictions with uncertainty on validation set
                val_predictions = []
                val_uncertainties = []
                val_true = []
                
                for pref in val_data.preferences:
                    try:
                        prediction = self.predict_preference(pref.bigram1, pref.bigram2)
                        pred_prob = prediction.probability
                        pred_std = prediction.uncertainty
                        if not np.isnan(pred_prob):
                            val_predictions.append(pred_prob)
                            val_uncertainties.append(pred_std)
                            val_true.append(1.0 if pref.preferred else 0.0)
                    except Exception as e:
                        logger.warning(f"Prediction failed for {pref.bigram1}-{pref.bigram2}: {str(e)}")
                        continue
                
                if not val_predictions:
                    logger.warning(f"No valid predictions in fold {fold + 1}, skipping")
                    continue
                
                val_predictions = np.array(val_predictions)
                val_true = np.array(val_true)
                
                # Calculate metrics
                metrics['accuracy'].append(accuracy_score(val_true, val_predictions > 0.5))
                metrics['auc'].append(roc_auc_score(val_true, val_predictions))
                metrics['mean_uncertainty'].append(np.mean(val_uncertainties))
                
                # Store feature weights with uncertainty
                weights = self.get_feature_weights()
                if weights:
                    logger.debug(f"Fold {fold + 1} weights: {weights}")
                    for feature, (weight_mean, weight_std) in weights.items():
                        if not np.isnan(weight_mean):
                            feature_effects[feature].append({
                                'mean': weight_mean,
                                'std': weight_std
                            })
                else:
                    logger.warning(f"No weights obtained in fold {fold + 1}")
                        
            finally:
                # Clear caches after cross-validation
                self.clear_caches()
                    
        # Process feature effects and calculate importance
        processed_effects = {}
        importance_metrics = {}
        
        for feature in feature_names:
            # Calculate importance using aligned effects method
            importance = self._calculate_feature_importance(
                feature=feature,
                dataset=dataset,
                current_features=self.selected_features
            )
            
            # Store results
            effects = feature_effects.get(feature, [])
            if effects:
                effect_means = [e['mean'] for e in effects]
                effect_stds = [e['std'] for e in effects]
                
                processed_effects[feature] = {
                    'mean': float(np.mean(effect_means)),
                    'std': float(np.mean(effect_stds)),
                    'values': effect_means
                }
            
            importance_metrics[feature] = {'importance': importance}
        
        # Log results
        self._log_feature_selection_results(
            self.selected_features, importance_metrics)
        
        # Save metrics to CSV
        self.save_metrics_report(
            metrics_dict={feature: {
                **processed_effects.get(feature, {}),
                'importance': importance_metrics[feature]['importance']
            } for feature in feature_names},
            output_file=self.config.feature_selection.metrics_file
        )
        
        return {
            'metrics': metrics,
            'selected_features': self.selected_features,
            'feature_effects': processed_effects,
            'importance_metrics': importance_metrics,
            'fold_uncertainties': dict(metrics['mean_uncertainty'])
        }
    
    def _log_feature_selection_results(self, 
                                    selected_features: List[str],
                                    importance_metrics: Dict[str, Dict]) -> None:
        """Log feature selection results."""
        logger.info("Selected Features:")
        for feature in selected_features:
            metrics = importance_metrics.get(feature, {})
            logger.info(f"  {feature}:")

    #--------------------------------------------
    # Data preparation and feature methods
    #--------------------------------------------
    def _get_feature_data(self, feature: str, dataset: Optional[PreferenceDataset] = None) -> Dict[str, np.ndarray]:
        """
        Centralized method for getting feature data with caching.
        Only normalizes typing_time, assumes other features (including control features) are pre-normalized.
        """
        dataset = dataset or self.dataset
        cache_key = f"{dataset.file_path}_{feature}"
        
        if hasattr(self, '_feature_data_cache') and cache_key in self._feature_data_cache:
            return self._feature_data_cache[cache_key]
            
        if '_x_' in feature:
            # Handle interaction features (already normalized through components)
            feat1, feat2 = feature.split('_x_')
            data1 = self._get_feature_data(feat1, dataset)
            data2 = self._get_feature_data(feat2, dataset)
            
            values = data1['values'] * data2['values']
            differences = data1['differences'] * data2['differences']
            raw_features = {}
            for bigram in set(data1['raw_features']) | set(data2['raw_features']):
                raw_features[bigram] = data1['raw_features'].get(bigram, 0.0) * data2['raw_features'].get(bigram, 0.0)
            
        else:
            # Handle base features
            values = []
            differences = []
            raw_features = {}
            
            if feature == 'typing_time':
                # Only typing_time needs normalization
                all_times = []
                for pref in dataset.preferences:
                    if pref.typing_time1 is not None:
                        all_times.append(pref.typing_time1)
                    if pref.typing_time2 is not None:
                        all_times.append(pref.typing_time2)
                
                if all_times:  # Only calculate if we have valid times
                    time_mean = np.mean(all_times)
                    time_std = np.std(all_times)
                else:
                    time_mean = 0.0
                    time_std = 1.0
                
                for pref in dataset.preferences:
                    time1 = pref.typing_time1
                    time2 = pref.typing_time2
                    
                    # Replace None values with mean
                    time1 = time_mean if time1 is None else time1
                    time2 = time_mean if time2 is None else time2
                    
                    # Z-score normalize timing values
                    time1_norm = (time1 - time_mean) / time_std
                    time2_norm = (time2 - time_mean) / time_std
                    
                    values.extend([time1_norm, time2_norm])
                    differences.append(time1_norm - time2_norm)
                    raw_features[pref.bigram1] = time1_norm
                    raw_features[pref.bigram2] = time2_norm

            else:
                # All other features (including control features) are already normalized
                for pref in dataset.preferences:
                    feat1 = self.feature_extractor.extract_bigram_features(
                        pref.bigram1[0], pref.bigram1[1]).get(feature, 0.0)
                    feat2 = self.feature_extractor.extract_bigram_features(
                        pref.bigram2[0], pref.bigram2[1]).get(feature, 0.0)
                    
                    values.extend([feat1, feat2])
                    differences.append(feat1 - feat2)
                    raw_features[pref.bigram1] = feat1
                    raw_features[pref.bigram2] = feat2
                    
        result = {
            'values': np.array(values),
            'differences': np.array(differences),
            'raw_features': raw_features
        }
        
        if not hasattr(self, '_feature_data_cache'):
            self._feature_data_cache = {}
        self._add_to_cache(self._feature_data_cache, cache_key, result)
        
        return result

    def _add_to_cache(self, cache: Dict, key: str, value: Any) -> None:
        """Add item to cache with size management."""
        if len(cache) > 1000:  # Arbitrary limit
            # Remove oldest 10% of entries
            remove_count = len(cache) // 10
            for k in list(cache.keys())[:remove_count]:
                del cache[k]
        cache[key] = value
    
    def prepare_data(self, dataset: PreferenceDataset, features: Optional[List[str]] = None) -> Dict:
            """
            Prepare data for Stan model with standardization, validation and cleaning.
            Handles both main features and control features separately.
            """
            try:
                processed_features = set()

                # Get feature names and separate control features
                self.feature_names = list(dict.fromkeys(
                    features if features is not None else dataset.get_feature_names()
                ))
                control_features = self.config.features.control_features
                
                # Main features are those not in control_features - deduplicate
                main_features = list(dict.fromkeys(
                    [f for f in self.feature_names if f not in control_features]
                ))
                
                # Check if this is a control-only model
                is_control_only = not main_features and all(f in control_features for f in self.feature_names)
                
                if not is_control_only and not main_features:
                    raise ValueError("No main features provided for model fitting")
                    
                logger.info(f"Main features ({len(main_features)}): {main_features}")
                logger.info(f"Control features ({len(control_features)}): {control_features}")
                
                # Create participant ID mapping
                participant_ids = sorted(list(dataset.participants))
                participant_map = {pid: i+1 for i, pid in enumerate(participant_ids)}
                
                # Track feature statistics for standardization
                feature_stats = defaultdict(lambda: {'values': [], 'mean': None, 'std': None})
                
                # First pass: collect values and standardize
                logger.info("First pass: collect values and standardize")
                for pref in dataset.preferences:
                    # Collect main feature values
                    if not is_control_only:
                        for feature in main_features:

                            if feature not in processed_features:
                                logger.debug(f"Processing base feature: {feature}")
                                processed_features.add(feature)

                            if '_x_' in feature:
                                # Split interaction name into component features
                                # e.g., 'same_finger_x_sum_finger_values_x_rows_apart' -> 
                                # ['same_finger', 'sum_finger_values', 'rows_apart']
                                components = feature.split('_x_')
                                
                                # For each component feature, collect its values for both bigrams in the preference
                                # This maintains statistics for the base features themselves
                                for component in components:
                                    # Get values for this component from both bigrams in the preference
                                    feat1 = pref.features1.get(component, 0.0)  # Value for first bigram
                                    feat2 = pref.features2.get(component, 0.0)  # Value for second bigram
                                    # Store both values for computing statistics on the base feature
                                    feature_stats[component]['values'].extend([feat1, feat2])
                                
                                # Now compute the interaction value for each bigram
                                # For each bigram, multiply together all its component feature values
                                feat1_interaction = 1.0  # Will hold product of all components for first bigram
                                feat2_interaction = 1.0  # Will hold product of all components for second bigram
                                for component in components:
                                    # Multiply each component's value into the running product for each bigram
                                    feat1_interaction *= pref.features1.get(component, 0.0)  # First bigram's product
                                    feat2_interaction *= pref.features2.get(component, 0.0)  # Second bigram's product
                                
                                # Store both interaction values (one per bigram) for computing interaction statistics
                                feature_stats[feature]['values'].extend([feat1_interaction, feat2_interaction])
                            else:
                                # For base features, simply get and store the value from each bigram
                                feat1 = pref.features1.get(feature, 0.0)  # Value from first bigram
                                feat2 = pref.features2.get(feature, 0.0)  # Value from second bigram
                                if feature == 'typing_time' and (feat1 is None or feat2 is None):
                                    feat1 = 0.0
                                    feat2 = 0.0
                                feature_stats[feature]['values'].extend([feat1, feat2])

                    # Collect control feature values
                    for feature in control_features:

                        if feature not in processed_features:
                            logger.debug(f"Processing base feature: {feature}")
                            processed_features.add(feature)

                        feat1 = pref.features1.get(feature, 0.0)
                        feat2 = pref.features2.get(feature, 0.0)
                        feature_stats[feature]['values'].extend([feat1, feat2])
                # Calculate standardization parameters
                for feature, stats in feature_stats.items():
                    values = np.array(stats['values'])

                    # Filter out None values before calculating statistics
                    values = np.array([v for v in values if v is not None])

                    if len(values) > 0:
                        stats['mean'] = float(np.mean(values))
                        stats['std'] = float(np.std(values))
                    else:
                        # Handle case where all values are None
                        stats['mean'] = 0.0
                        stats['std'] = 1.0

                    logger.debug(f"Feature {feature} stats - mean: {stats['mean']}, std: {stats['std']}")

                # Second pass: build standardized matrices
                processed_features.clear()  # Reset before second pass
                logger.info("Second pass: build standardized matrices")
                X1, X2 = [], []  # Main feature matrices
                C1, C2 = [], []  # Control feature matrices
                participant = []
                y = []
                
                skipped_count = 0
                for pref in dataset.preferences:
                    try:
                        # Process main features
                        if is_control_only:
                            features1_main = [0.0]  # Dummy feature
                            features2_main = [0.0]
                        else:
                            features1_main = []
                            features2_main = []
                            for feature in main_features:

                                if feature not in processed_features:
                                    logger.debug(f"Processing base feature: {feature}")
                                    processed_features.add(feature)

                                try:

                                    if '_x_' in feature:
                                        # Add detailed logging
                                        logger.debug(f"Processing interaction feature: {feature}")
                                        components = feature.split('_x_')
                                        logger.debug(f"Components: {components}")
                                        
                                        # Get standardized base features with error checking
                                        for component in components:
                                            if component not in feature_stats:
                                                logger.error(f"Missing statistics for component: {component}")
                                                raise ValueError(f"Missing statistics for component: {component}")
                                        
                                        # Initialize products for interaction
                                        feat1_interaction = 1.0
                                        feat2_interaction = 1.0
                                        
                                        # Multiply standardized values for each component
                                        for component in components:
                                            feat1 = pref.features1.get(component, 0.0)
                                            feat2 = pref.features2.get(component, 0.0)
                                            if component == 'typing_time' and (feat1 is None or feat2 is None):
                                                feat1 = 0.0
                                                feat2 = 0.0
                                            
                                            feat1_base = (feat1 - feature_stats[component]['mean']) / feature_stats[component]['std']
                                            feat2_base = (feat2 - feature_stats[component]['mean']) / feature_stats[component]['std']
                                            
                                            feat1_interaction *= feat1_base
                                            feat2_interaction *= feat2_base
                                        
                                        features1_main.append(feat1_interaction)
                                        features2_main.append(feat2_interaction)
                                    else:
                                        # Add logging for base features
                                        logger.debug(f"Processing base feature: {feature}")
                                        if feature not in feature_stats:
                                            logger.error(f"Missing statistics for feature: {feature}")
                                            raise ValueError(f"Missing statistics for feature: {feature}")
                                        
                                        feat1 = pref.features1.get(feature, 0.0)
                                        feat2 = pref.features2.get(feature, 0.0)
                                        if feature == 'typing_time' and (feat1 is None or feat2 is None):
                                            feat1 = 0.0
                                            feat2 = 0.0

                                        # Always standardize, even if we've set values to zero
                                        feat1 = (feat1 - feature_stats[feature]['mean']) / feature_stats[feature]['std']
                                        feat2 = (feat2 - feature_stats[feature]['mean']) / feature_stats[feature]['std']
                                        
                                        features1_main.append(feat1)
                                        features2_main.append(feat2)

                                except Exception as e:
                                    logger.error(f"Error processing feature {feature}: {str(e)}")
                                    raise  # Re-raise to be caught by outer try-except
                                    
                        # Process control features with error checking
                        features1_control = []
                        features2_control = []
                        for feature in control_features:

                            if feature not in processed_features:
                                logger.debug(f"Processing base feature: {feature}")
                                processed_features.add(feature)

                            if feature not in feature_stats:
                                logger.error(f"Missing statistics for control feature: {feature}")
                                raise ValueError(f"Missing statistics for control feature: {feature}")
                                
                            feat1 = (pref.features1.get(feature, 0.0) - feature_stats[feature]['mean']) / feature_stats[feature]['std']
                            feat2 = (pref.features2.get(feature, 0.0) - feature_stats[feature]['mean']) / feature_stats[feature]['std']
                            features1_control.append(feat1)
                            features2_control.append(feat2)
                            
                        # Add arrays only if we got here without errors
                        X1.append(features1_main)
                        X2.append(features2_main)
                        C1.append(features1_control)
                        C2.append(features2_control)
                        participant.append(participant_map[pref.participant_id])
                        y.append(1 if pref.preferred else 0)
                        
                    except Exception as e:
                        logger.warning(f"Skipping preference due to error: {str(e)}")
                        logger.warning(f"Preference details: bigram1={pref.bigram1}, bigram2={pref.bigram2}")
                        logger.warning(f"Features1: {pref.features1}")
                        logger.warning(f"Features2: {pref.features2}")
                        skipped_count += 1
                        continue

                if skipped_count == len(dataset.preferences):
                    logger.error("All preferences were skipped due to errors")
                    raise ValueError("No valid preferences remained after processing")
                elif skipped_count > 0:
                    logger.warning(f"Skipped {skipped_count} preferences due to invalid features")

                # Convert to numpy arrays
                X1 = np.array(X1, dtype=np.float64)
                X2 = np.array(X2, dtype=np.float64)
                C1 = np.array(C1, dtype=np.float64)
                C2 = np.array(C2, dtype=np.float64)
                participant = np.array(participant, dtype=np.int32)
                y = np.array(y, dtype=np.int32)

                # Check if we have any valid data
                if len(X1) == 0:
                    logger.error("No valid preferences after processing")
                    raise ValueError("No valid preferences remained after processing")

                # Reshape arrays if needed
                if is_control_only:
                    if len(X1) > 0 and X1.ndim == 1:
                        X1 = X1.reshape(-1, 1)
                        X2 = X2.reshape(-1, 1)
                else:
                    if len(X1) > 0 and X1.ndim == 1 and len(main_features) > 0:
                        X1 = X1.reshape(-1, len(main_features))
                        X2 = X2.reshape(-1, len(main_features))

                if len(C1) > 0 and C1.ndim == 1 and len(control_features) > 0:
                    C1 = C1.reshape(-1, len(control_features))
                    C2 = C2.reshape(-1, len(control_features))

                # Verify dimensions and check for NaNs
                if not is_control_only:
                    if X1.shape[1] != len(main_features):
                        raise ValueError(f"Main feature dimension mismatch: {X1.shape[1]} != {len(main_features)}")
                else:
                    if X1.shape[1] != 1:
                        raise ValueError("Invalid dummy feature dimension for control-only model")
                        
                if C1.shape[1] != len(control_features):
                    raise ValueError(f"Control feature dimension mismatch: {C1.shape[1]} != {len(control_features)}")
                    
                if np.any(np.isnan(X1)) or np.any(np.isnan(X2)) or np.any(np.isnan(C1)) or np.any(np.isnan(C2)):
                    raise ValueError("NaN values found in feature matrices")

                # Log dimensions and statistics
                logger.info(f"Data dimensions:")
                logger.info(f"  Preferences: {len(y)}")
                logger.info(f"  Participants: {len(participant_ids)}")
                if is_control_only:
                    logger.info("  Using dummy main feature for control-only model")
                logger.info(f"  Main features: {1 if is_control_only else len(main_features)}")
                logger.info(f"  Control features: {len(control_features)}")

                # Log original and standardized statistics
                logger.info("Feature statistics:")
                if not is_control_only:
                    for i, feature in enumerate(main_features):
                        logger.info(f"{feature} (main):")
                        if feature in feature_stats:
                            logger.info(f"  Original - mean: {feature_stats[feature]['mean']:.3f}, "
                                    f"std: {feature_stats[feature]['std']:.3f}")
                        logger.info(f"  Standardized - mean: {np.mean(X1[:, i]):.3f}, "
                                f"std: {np.std(X1[:, i]):.3f}")

                for i, feature in enumerate(control_features):
                    logger.info(f"{feature} (control):")
                    logger.info(f"  Original - mean: {feature_stats[feature]['mean']:.3f}, "
                            f"std: {feature_stats[feature]['std']:.3f}")
                    logger.info(f"  Standardized - mean: {np.mean(C1[:, i]):.3f}, "
                            f"std: {np.std(C1[:, i]):.3f}")

                return {
                    'N': len(y),
                    'P': len(participant_ids),
                    'F': 1 if is_control_only else len(main_features),
                    'C': len(control_features),
                    'X1': X1,
                    'X2': X2,
                    'C1': C1,
                    'C2': C2,
                    'participant': participant,
                    'y': y,
                    'feature_scale': self.config.model.feature_scale,
                    'participant_scale': self.config.model.participant_scale
                }

            except Exception as e:
                logger.error(f"Error preparing data: {str(e)}")
                raise

    def _extract_features(self, bigram: str) -> Dict[str, float]:
        """
        Extract features for a bigram using feature extractor with caching.
        
        Args:
            bigram: Two-character string to extract features for
            
        Returns:
            Dictionary mapping feature names to their values
            
        Raises:
            NotFittedError: If feature extractor is not initialized
            ValueError: If bigram is not exactly 2 characters
            FeatureError: If feature extraction fails
        """
        # Input validation
        if not isinstance(bigram, str):
            raise ValueError(f"Bigram must be a string, got {type(bigram)}")
            
        if len(bigram) != 2:
            raise ValueError(f"Bigram must be exactly 2 characters, got '{bigram}'")
            
        if not self.feature_extractor:
            raise NotFittedError("Feature extractor not initialized. Call fit() first.")

        try:
            # Use cache if available
            cache_key = str(bigram)  # Ensure string key for cache
            cached_features = self.feature_cache.get(cache_key)
            if cached_features is not None:
                return cached_features.copy()  # Return copy to prevent modification
            
            # Extract base features
            try:
                features = self.feature_extractor.extract_bigram_features(
                    char1=bigram[0],
                    char2=bigram[1]
                )
            except Exception as e:
                raise FeatureError(f"Feature extraction failed for bigram '{bigram}': {str(e)}")
                
            # Validate extracted features
            if not isinstance(features, dict):
                raise FeatureError(f"Feature extractor returned {type(features)}, expected dict")
                
            if not features:
                logger.warning(f"No features extracted for bigram '{bigram}'")
            
            # Add interaction features
            for interaction in self.config.features.interactions:
                # Get name for this interaction (sorted for consistency)
                interaction_name = '_x_'.join(sorted(interaction))
                
                # Compute interaction value by multiplying component features
                interaction_value = 1.0
                for component in interaction:
                    if component not in features:
                        logger.warning(f"Component feature '{component}' missing for interaction in bigram '{bigram}'")
                        interaction_value = 0.0
                        break
                    interaction_value *= features[component]
                    
                # Add interaction to features
                features[interaction_name] = interaction_value
            
            # Cache result
            self.feature_cache.set(cache_key, features.copy())
            
            return features.copy()
            
        except (NotFittedError, ValueError, FeatureError):
            # Re-raise these specific exceptions
            raise
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"Unexpected error extracting features for bigram '{bigram}': {str(e)}")
            raise FeatureError(f"Feature extraction failed: {str(e)}")
        
    def get_bigram_comfort_scores(self, bigram: str) -> Tuple[float, float]:
        """
        Get comfort score and uncertainty for a single bigram.
        Accounts for both main features and control features.
        
        Returns:
            Tuple of (mean score, standard deviation)
        """
        try:
            # Extract features for bigram
            features = self._extract_features(bigram)
            
            # Get feature weights from posterior, including control features
            weights = self.get_feature_weights(include_control=True)
            
            # Separate main and control features
            main_features = [f for f in self.selected_features 
                            if f not in self.config.features.control_features]
            control_features = self.config.features.control_features
            
            # Calculate main feature contribution
            main_score = 0.0
            main_uncertainty = 0.0
            for feature in main_features:
                if feature in weights:
                    value = features.get(feature, 0.0)
                    weight_mean, weight_std = weights[feature]
                    main_score += value * weight_mean
                    main_uncertainty += (value * weight_std) ** 2
            
            # Calculate control feature contribution
            control_score = 0.0
            control_uncertainty = 0.0
            for feature in control_features:
                if feature in weights:
                    value = features.get(feature, 0.0)
                    weight_mean, weight_std = weights[feature]
                    control_score += value * weight_mean
                    control_uncertainty += (value * weight_std) ** 2
            
            # Combine scores and uncertainties
            total_score = main_score + control_score
            total_uncertainty = np.sqrt(main_uncertainty + control_uncertainty)
            
            return float(total_score), float(total_uncertainty)
            
        except Exception as e:
            logger.error(f"Error calculating comfort scores: {str(e)}")
            return 0.0, 1.0
        
    def get_feature_weights(self, include_control: bool = True) -> Dict[str, Tuple[float, float]]:
        """Get feature weights and their uncertainties."""
        if not hasattr(self, 'fit_result'):
            raise ValueError("Model not fitted. Call fit() first.")
            
        try:
            weights = {}
            
            # Get main feature weights (beta)
            main_features = [f for f in self.feature_names 
                            if f not in self.config.features.control_features]
            
            if main_features:  # Only process beta if we have main features
                beta = self.fit_result.stan_variable('beta')
                
                if beta.shape[1] != len(main_features):
                    raise ValueError(f"Beta shape mismatch: {beta.shape[1]} != {len(main_features)}")
                
                for i, feature in enumerate(main_features):
                    weights[feature] = (
                        float(np.mean(beta[:, i])),
                        float(np.std(beta[:, i]))
                    )
            
            # Get control feature weights (gamma) if requested
            if include_control:
                control_features = self.config.features.control_features
                if control_features:
                    gamma = self.fit_result.stan_variable('gamma')
                    
                    if gamma.shape[1] != len(control_features):
                        raise ValueError(f"Gamma shape mismatch: {gamma.shape[1]} != {len(control_features)}")
                    
                    for i, feature in enumerate(control_features):
                        weights[feature] = (
                            float(np.mean(gamma[:, i])),
                            float(np.std(gamma[:, i]))
                        )
            
            return weights
            
        except Exception as e:
            logger.error(f"Error getting feature weights: {str(e)}")
            return {}
        
    def calculate_storage_requirements(self, dataset: PreferenceDataset, all_features: List[str]) -> int:
        """
        Calculate approximate storage requirements for the entire feature selection process.
        
        Returns:
            Required storage in MB
        """
        bytes_per_param = 8  # Double precision float
        n_participants = len(dataset.participants)
        n_preferences = len(dataset.preferences)
        n_features = len(all_features)
        n_chains = self.config.model.chains
        n_samples = self.config.model.warmup + self.config.model.n_samples
        
        logger.info(f"Storage calculation details:")
        logger.info(f"  Participants: {n_participants}")
        logger.info(f"  Preferences: {n_preferences}")
        logger.info(f"  Features: {n_features}")
        logger.info(f"  Chains: {n_chains}")
        logger.info(f"  Total samples: {n_samples}")
        
        # Storage per model fit
        params_per_chain = (n_participants * n_features) + n_preferences + n_features
        chain_storage = params_per_chain * bytes_per_param * n_chains * n_samples
        
        logger.info(f"  Parameters per chain: {params_per_chain}")
        logger.info(f"  Storage per full model fit: {chain_storage / (1024 * 1024):.1f} MB")
        
        # Number of model fits needed
        total_fits = 1 + n_features + (5 * n_features)
        logger.info(f"  Total model fits needed: {total_fits}")
        logger.info(f"    - Initial baseline: 1")
        logger.info(f"    - Feature evaluations: {n_features}")
        logger.info(f"    - Cross-validation fits: {5 * n_features}")
        
        # Total storage including overhead for temp files
        total_bytes = chain_storage * total_fits * 1.5  # 50% overhead
        total_mb = int(total_bytes / (1024 * 1024))
        
        logger.info(f"  Total storage needed (with 50% overhead): {total_mb} MB")
        
        return total_mb

    def check_total_storage(self, dataset: PreferenceDataset, all_features: List[str]) -> None:
        """
        Check if enough storage is available for the entire feature selection process.
        Raises RuntimeError if insufficient space.
        """
        required_mb = self.calculate_storage_requirements(dataset, all_features)
        
        # Check temp directory space
        temp_dir = Path(tempfile.gettempdir())
        total, used, free = shutil.disk_usage(temp_dir)
        free_mb = free // (1024 * 1024)
        
        logger.info(f"Storage requirements:")
        logger.info(f"  Required space: {required_mb} MB")
        logger.info(f"  Available space: {free_mb} MB")
        
        if free_mb < required_mb:
            raise RuntimeError(
                f"Insufficient storage space for feature selection.\n"
                f"Required: {required_mb} MB\n"
                f"Available: {free_mb} MB\n"
                f"Consider:\n"
                f"- Freeing up temporary space\n"
                f"- Reducing number of chains ({self.config.model.chains})\n"
                f"- Reducing number of samples ({self.config.model.n_samples})\n"
                f"- Reducing number of features to evaluate ({len(all_features)})"
            )
                                                
    #--------------------------------------------
    # Feature selection and evaluation methods
    #--------------------------------------------  
    def predict_preference(self, bigram1: str, bigram2: str) -> ModelPrediction:
        """Predict preference between two bigrams."""
        try:
            if not hasattr(self, 'fit_result'):
                raise NotFittedError("Model must be fit before making predictions")

            # Get features for both bigrams
            features1 = self.feature_extractor.extract_bigram_features(bigram1[0], bigram1[1])
            features2 = self.feature_extractor.extract_bigram_features(bigram2[0], bigram2[1])

            # Standardize features using stored statistics
            X1 = []
            X2 = []
            for feature in self.feature_names:
                feat1 = features1.get(feature, 0.0)
                feat2 = features2.get(feature, 0.0)

                # 'typing_time' feature
                # If either timing is None (meaning no timing data available),
                # sets both timings to 0.0 to handle missing data
                if feature == 'typing_time' and (feat1 is None or feat2 is None):
                    feat1 = 0.0
                    feat2 = 0.0
                
                mean = self.feature_stats[feature]['mean']
                std = self.feature_stats[feature]['std']
                
                X1.append((feat1 - mean) / std)
                X2.append((feat2 - mean) / std)

            X1 = np.array(X1).reshape(1, -1)
            X2 = np.array(X2).reshape(1, -1)

            # Get model predictions using y_pred from Stan results
            y_pred = self.fit_result.stan_variable('y_pred')  # Use stan_variable instead of get
        
            # Convert to probability
            probability = 1 / (1 + np.exp(-y_pred))
            
            # Get prediction uncertainty
            uncertainty = np.std(y_pred) if isinstance(y_pred, np.ndarray) else 0.0

            return ModelPrediction(
                probability=float(np.mean(probability)),
                uncertainty=float(uncertainty),
                features_used=list(self.feature_names),
                computation_time=0.0
            )

        except Exception as e:
            logger.error(f"Error in predict_preference: {str(e)}")
            raise
            
    def select_features(self, dataset: PreferenceDataset, all_features: List[str]) -> List[str]:
        """Select features by evaluating their importance for prediction."""
        try:
            self.dataset = dataset
            
            # Preprocess dataset
            logger.info("Preprocessing dataset for feature selection...")
            valid_prefs = []
            for pref in dataset.preferences:
                valid = True
                for feature in all_features:
                    if (pref.features1.get(feature) is None or 
                        pref.features2.get(feature) is None):
                        valid = False
                        break
                if valid:
                    valid_prefs.append(pref)
            
            # Create processed dataset
            self.processed_dataset = PreferenceDataset.__new__(PreferenceDataset)
            self.processed_dataset.preferences = valid_prefs
            self.processed_dataset.participants = {p.participant_id for p in valid_prefs}
            self.processed_dataset.file_path = dataset.file_path
            self.processed_dataset.config = dataset.config
            self.processed_dataset.control_features = dataset.control_features
            self.processed_dataset.feature_extractor = dataset.feature_extractor
            self.processed_dataset.feature_names = dataset.feature_names
            self.processed_dataset.all_bigrams = dataset.all_bigrams
            self.processed_dataset.all_bigram_features = dataset.all_bigram_features
            
            # Initialize feature sets
            control_features = self.config.features.control_features
            candidate_features = [f for f in all_features if f not in control_features]
            selected_features = list(control_features)  # Start with control features

            # Log initial state
            logger.info("\nStarting feature selection:")
            logger.info(f"Control features: {selected_features}")
            logger.info(f"Candidate features: {len(candidate_features)}")
            
            # Keep selecting features until no more useful ones found
            round_num = 1
            while candidate_features:
                logger.info(f"\nSelection Round {round_num}")
                logger.info(f"Current features: {selected_features}")
                logger.info(f"Remaining candidates: {len(candidate_features)}")
                
                best_feature = None
                best_importance = -float('inf')
                
                # Evaluate each candidate
                for feature in candidate_features:
                    importance = self._calculate_feature_importance(
                        feature=feature,
                        dataset=self.processed_dataset,
                        current_features=selected_features
                    )
                    
                    # If feature helps predictions more than our threshold
                    if importance > self.config.feature_selection.importance_threshold:
                        if importance > best_importance:
                            best_importance = importance
                            best_feature = feature
                
                if best_feature is None:
                    logger.info("No remaining features improve predictions sufficiently.")
                    break
                    
                # Add best feature and continue
                logger.info(f"\nSelected feature {best_feature} with importance {best_importance:.4f}")
                selected_features.append(best_feature)
                candidate_features.remove(best_feature)
                round_num += 1

            logger.info("\nFeature selection complete:")
            logger.info(f"Selected features: {selected_features}")
            self.selected_features = selected_features
            return selected_features
            
        except Exception as e:
            logger.error(f"Error in select_features: {str(e)}")
            logger.error("Traceback:", exc_info=True)
            raise

    def _get_evaluation_context(self, feature: str, current_selected: List[str], 
                            control_features: List[str]) -> Optional[List[str]]:
        """Get evaluation context for a feature."""
        if '_x_' in feature:
            components = feature.split('_x_')
            if not all(c in current_selected for c in components):
                return None
        
        # Build context with no duplicates
        context = list(dict.fromkeys(
            control_features +  # Control features first
            current_selected +  # Currently selected features
            [feature]          # Feature being evaluated
        ))
        
        return context
                                                                                                                                                                                                                                                       
    def _prepare_feature_matrices(self, dataset: PreferenceDataset,
                                main_features: List[str],
                                control_features: List[str]) -> Dict[str, Any]:
        """Prepare feature matrices for Stan model."""
        try:
            # First collect all feature values
            feature_values = defaultdict(list)
            for feature in main_features + control_features:
                for pref in dataset.preferences:
                    feat1 = pref.features1.get(feature, 0.0)
                    feat2 = pref.features2.get(feature, 0.0)
                    if feature == 'typing_time' and (feat1 is None or feat2 is None):
                        feat1 = 0.0
                        feat2 = 0.0
                    feature_values[feature].extend([feat1, feat2])

            # Calculate statistics and standardize
            feature_stats = {}
            for feature in main_features + control_features:
                values = np.array([v for v in feature_values[feature] if v is not None])
                mean = float(np.mean(values)) if len(values) > 0 else 0.0
                std = float(np.std(values)) if len(values) > 0 else 1.0
                feature_stats[feature] = {'mean': mean, 'std': std}
                
                logger.info(f"{feature} ({'main' if feature in main_features else 'control'}):")
                logger.info(f"Original - mean: {mean:.3f}, std: {std:.3f}")

            # Build standardized matrices
            X1, X2 = [], []  # Main feature matrices
            C1, C2 = [], []  # Control feature matrices
            participant = []
            y = []

            for pref in dataset.preferences:
                # Process main features
                if not main_features:
                    features1_main = [0.0]  # Dummy feature
                    features2_main = [0.0]
                else:
                    features1_main = []
                    features2_main = []
                    for feature in main_features:
                        feat1 = pref.features1.get(feature, 0.0)
                        feat2 = pref.features2.get(feature, 0.0)
                        if feature == 'typing_time' and (feat1 is None or feat2 is None):
                            feat1 = 0.0
                            feat2 = 0.0
                        mean = feature_stats[feature]['mean']
                        std = feature_stats[feature]['std']
                        features1_main.append((feat1 - mean) / std)
                        features2_main.append((feat2 - mean) / std)

                # Process control features
                features1_control = []
                features2_control = []
                for feature in control_features:
                    feat1 = pref.features1.get(feature, 0.0)
                    feat2 = pref.features2.get(feature, 0.0)
                    mean = feature_stats[feature]['mean']
                    std = feature_stats[feature]['std']
                    features1_control.append((feat1 - mean) / std)
                    features2_control.append((feat2 - mean) / std)

                X1.append(features1_main)
                X2.append(features2_main)
                C1.append(features1_control)
                C2.append(features2_control)
                participant.append(pref.participant_id)
                y.append(1 if pref.preferred else 0)

            # Convert to numpy arrays
            X1 = np.array(X1, dtype=np.float64)
            X2 = np.array(X2, dtype=np.float64)
            C1 = np.array(C1, dtype=np.float64)
            C2 = np.array(C2, dtype=np.float64)
            
            # Map participant IDs to integers
            unique_participants = sorted(set(participant))
            participant_map = {pid: i for i, pid in enumerate(unique_participants)}
            participant = np.array([participant_map[p] for p in participant], dtype=np.int32)
            y = np.array(y, dtype=np.int32)

            # Log standardization results
            for feature in main_features + control_features:
                mean = np.mean(np.concatenate([
                    X1[:, main_features.index(feature)] if feature in main_features 
                    else C1[:, control_features.index(feature)],
                    X2[:, main_features.index(feature)] if feature in main_features
                    else C2[:, control_features.index(feature)]
                ]))
                std = np.std(np.concatenate([
                    X1[:, main_features.index(feature)] if feature in main_features
                    else C1[:, control_features.index(feature)],
                    X2[:, main_features.index(feature)] if feature in main_features
                    else C2[:, control_features.index(feature)]
                ]))
                #logger.info(f"  Standardized - mean: {mean:.3f}, std: {std:.3f}")

            return {
                'N': len(y),
                'P': len(unique_participants),  # Changed from 'J' to 'P' to match Stan model
                'F': X1.shape[1],
                'C': C1.shape[1],
                'participant': participant + 1,  # Stan uses 1-based indexing
                'X1': X1,
                'X2': X2,
                'C1': C1,
                'C2': C2,
                'y': y,
                'feature_scale': self.config.model.feature_scale,    # Add feature scale parameter
                'participant_scale': self.config.model.participant_scale  # Add participant scale parameter
            }

        except Exception as e:
            logger.error(f"Error preparing feature matrices: {str(e)}")
            logger.error("Traceback:", exc_info=True)
            raise
                                                                
    def save_metrics_report(self, metrics_dict: Dict[str, Dict[str, float]], output_file: str):
        """Generate and save a detailed metrics report."""
        report_df = pd.DataFrame([
            {
                'Feature': feature,
                'Model Effect': metrics['model_effect'],
                'Effect Consistency': metrics['effect_consistency'],
                'Predictive Power': metrics['predictive_power']
            }
            for feature, metrics in metrics_dict.items()
        ])
        
        # Save to CSV
        report_df.to_csv(output_file, index=False)

    #--------------------------------------------
    # Statistical and model diagnostic methods
    #--------------------------------------------
    def _calculate_feature_importance(self, feature: str, dataset: PreferenceDataset, 
                                      current_features: List[str]) -> float:
        """Calculate feature importance based on prediction improvement."""
        try:
            # Fit models with and without the feature
            with self._create_temp_model() as baseline_model:
                baseline_model.fit(dataset, current_features)
            with self._create_temp_model() as feature_model:
                feature_model.fit(dataset, current_features + [feature])

            # Calculate aligned effects across cross-validation splits
            cv_splits = self._get_cv_splits(dataset, n_splits=5)
            cv_aligned_effects = []
            
            for fold, (train_idx, val_idx) in enumerate(cv_splits, 1):
                logger.info(f"Evaluating fold {fold}/5")
                val_data = dataset._create_subset_dataset(val_idx)
                
                # Calculate aligned effects for validation set
                for pref in val_data.preferences:
                    # Get predictions in logit space
                    base_pred = baseline_model.predict_preference(pref.bigram1, pref.bigram2)
                    base_logit = -np.log(1/base_pred.probability - 1)
                    
                    feat_pred = feature_model.predict_preference(pref.bigram1, pref.bigram2)
                    feat_logit = -np.log(1/feat_pred.probability - 1)
                    
                    # Calculate effect
                    effect = feat_logit - base_logit
                    
                    # Align effect with preference
                    aligned_effect = effect if pref.preferred else -effect
                    cv_aligned_effects.append(aligned_effect)

            cv_aligned_effects = np.array(cv_aligned_effects)

            # Calculate metrics
            mean_aligned_effect = np.mean(cv_aligned_effects)
            effect_std = np.std(cv_aligned_effects)
            
            # Calculate importance as magnitude of effect scaled by consistency
            effect_magnitude = abs(mean_aligned_effect)
            effect_consistency = 1 - (effect_std / (effect_magnitude + 1e-6))
            importance = effect_magnitude * max(0, effect_consistency)  # Only use positive consistency
            
            # Log results
            logger.info(f"Feature importance analysis for {feature}:")
            logger.info(f"  Mean aligned effect: {mean_aligned_effect:.4f}")
            logger.info(f"  Effect consistency: {effect_consistency:.4f}")
            logger.info(f"  Importance: {importance:.4f}")
            
            return float(importance)
        
        except Exception as e:
            logger.error(f"  Error calculating feature importance: {str(e)}")
            return -float('inf')
                                                                                       
    #--------------------------------------------
    # Cross-validation and splitting methods
    #--------------------------------------------
    def _get_cv_splits(self, dataset: PreferenceDataset, n_splits: int) -> List[Tuple[np.ndarray, np.ndarray]]:
        """Get cross-validation splits preserving participant structure with validation."""
        from sklearn.model_selection import KFold
        
        # Check for dataset size consistency
        if not hasattr(self, '_dataset_size'):
            self._dataset_size = len(dataset.preferences)
            self._dataset_participants = len(dataset.participants)
        else:
            if len(dataset.preferences) != self._dataset_size:
                raise ValueError(f"Dataset size changed: {len(dataset.preferences)} vs {self._dataset_size}")
            if len(dataset.participants) != self._dataset_participants:
                raise ValueError(f"Participant count changed: {len(dataset.participants)} vs {self._dataset_participants}")
        
        # Get unique participants and their preferences
        participants = list(dataset.participants)
        participant_to_indices = {}
        for i, pref in enumerate(dataset.preferences):
            if pref.participant_id not in participant_to_indices:
                participant_to_indices[pref.participant_id] = []
            participant_to_indices[pref.participant_id].append(i)
        
        # Create participant splits
        kf = KFold(n_splits=n_splits, shuffle=True, random_state=42)
        
        splits = []
        total_preferences = len(dataset.preferences)
        used_indices = set()
        
        for train_part_idx, val_part_idx in kf.split(participants):
            # Get participant IDs for each split
            train_participants = {participants[i] for i in train_part_idx}
            val_participants = {participants[i] for i in val_part_idx}
            
            # Verify participant split
            if train_participants & val_participants:
                raise ValueError("Participant overlap detected in CV splits")
            
            # Get preference indices for each split
            train_indices = []
            val_indices = []
            
            for participant, indices in participant_to_indices.items():
                if participant in train_participants:
                    train_indices.extend(indices)
                elif participant in val_participants:
                    val_indices.extend(indices)
            
            # Verify preference split
            if set(train_indices) & set(val_indices):
                raise ValueError("Preference index overlap detected in CV splits")
            
            train_indices = np.array(train_indices)
            val_indices = np.array(val_indices)
            
            # Update used indices tracking
            used_indices.update(train_indices)
            used_indices.update(val_indices)
            
            splits.append((train_indices, val_indices))
        
        # Verify all preferences are used
        if len(used_indices) != total_preferences:
            raise ValueError(f"Not all preferences used in CV splits: {len(used_indices)} vs {total_preferences}")
            
        return splits
                            
    #--------------------------------------------
    # Output and visualization methods
    #--------------------------------------------
    def save(self, path: Path) -> None:
        """Save model state to file."""
        logger.info("=== Saving model state ===")
        logger.info(f"Selected features: {self.selected_features}")
        logger.info(f"Feature names: {self.feature_names}")
        logger.info(f"Feature weights: {self.feature_weights}")
        
        save_dict = {
            'config': self.config,
            'feature_names': self.feature_names,
            'selected_features': self.selected_features,
            'feature_weights': self.feature_weights,
            'fit_result': self.fit_result,
            'interaction_metadata': self.interaction_metadata
        }
        with open(path, 'wb') as f:
            pickle.dump(save_dict, f)
        logger.info(f"Model saved to {path}")

    @classmethod
    def load(cls, path: Path) -> 'PreferenceModel':
        """Load model state from file."""
        logger.info("=== Loading model state ===")
        try:
            with open(path, 'rb') as f:
                save_dict = pickle.load(f)
            
            model = cls(config=save_dict['config'])
            try:
                model.feature_names = save_dict['feature_names']
                model.selected_features = save_dict['selected_features']
                model.feature_weights = save_dict['feature_weights']
                model.fit_result = save_dict['fit_result']
                model.interaction_metadata = save_dict['interaction_metadata']
                return model
            except Exception:
                model.cleanup()
                raise
        except Exception:
            logger.error(f"Error loading model from {path}")
            raise

    def cleanup(self) -> None:
        """Clean up temporary files and resources."""
        try:
            # Clean Stan temp directory if it exists in config
            if hasattr(self.config.paths, 'stan_temp'):
                output_dir = Path(self.config.paths.stan_temp)
                if output_dir.exists():
                    for file in output_dir.glob("preference_model-*"):
                        try:
                            file.unlink()
                        except Exception as e:
                            logger.warning(f"Could not remove temp file {file}: {str(e)}")
            # Clear caches
            self.clear_caches()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except:
            pass  # Suppress errors during garbage collection

