"""
Bayesian Modeling Module

This module implements the Bayesian GLMM analysis for keyboard layout optimization.
It provides functions for model training, validation, and comfort score generation.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import pymc as pm
import arviz as az
import matplotlib.pyplot as plt
from typing import Optional, Tuple, List, Any, Dict
from sklearn.preprocessing import StandardScaler
from scipy import stats
import json
import logging

from data_processing import ProcessedData

logger = logging.getLogger(__name__)

def validate_inputs(feature_matrix: pd.DataFrame, 
                   target_vector: np.ndarray, 
                   participants: Optional[np.ndarray]) -> bool:
    """
    Validate data inputs for Bayesian GLMM model fitting.
    
    Args:
        feature_matrix: DataFrame of feature values, where each row corresponds to a bigram pair
        target_vector: Array of comfort scores or preference ratings
        participants: Optional array of participant IDs for mixed effects modeling
        
    Returns:
        bool: True if validation passes, raises ValueError otherwise
        
    Raises:
        ValueError: If dimensions don't match or if feature matrix contains null values
    """
    if len(feature_matrix) != len(target_vector):
        raise ValueError("Feature matrix and target vector must have same length")
    if participants is not None and len(participants) != len(target_vector):
        raise ValueError("Participants array must match target vector length")
    if np.any(pd.isnull(feature_matrix)):
        raise ValueError("Feature matrix contains null values")
    return True

def evaluate_feature_sets(
    feature_matrix: pd.DataFrame,
    target_vector: np.ndarray,
    participants: np.ndarray,
    candidate_features: List[List[str]],
    feature_names: List[str],
    output_dir: Path,
    config: Dict[str, Any],
    n_splits: int = 5,
    n_samples: int = 1000
):
    """Evaluate different feature sets using cross-validation and information criteria."""
    cv_scores = {}
    waic_scores = {}
    loo_scores = {}

    # Validate input data
    if feature_matrix.empty:
        raise ValueError("Feature matrix is empty")
    if len(target_vector) == 0:
        raise ValueError("Target vector is empty")
        
    # Log data dimensions
    logger.info(f"Feature matrix shape: {feature_matrix.shape}")
    logger.info(f"Target vector length: {len(target_vector)}")
    logger.info(f"Participants array length: {len(participants)}")
    logger.info(f"Number of unique participants: {len(np.unique(participants))}")

    # Evaluate each feature set
    for set_idx, feature_set in enumerate(candidate_features):
        set_name = f"feature_set_{set_idx}"
        logger.info(f"Evaluating {set_name} with {len(feature_set)} features")
        
        # Get feature subset
        try:
            X_subset = feature_matrix[feature_set]
            logger.info(f"Feature subset shape: {X_subset.shape}")
        except KeyError as e:
            logger.error(f"Missing features in set {set_idx}: {e}")
            continue
        
        # Perform cross-validation
        try:
            cv_result = perform_cross_validation(
                feature_matrix=X_subset,
                target_vector=target_vector,
                participants=participants,
                n_splits=n_splits
            )
            cv_scores[set_name] = cv_result
        except Exception as e:
            logger.error(f"Cross-validation failed for {set_name}: {e}", exc_info=True)
            cv_scores[set_name] = [np.nan] * n_splits
        
        # Calculate WAIC and LOO
        try:
            waic_score, loo_score = calculate_waic_loo(X_subset, target_vector)
            waic_scores[set_name] = waic_score
            loo_scores[set_name] = loo_score
        except Exception as e:
            logger.error(f"WAIC/LOO computation failed for {set_name}: {e}")
            waic_scores[set_name] = np.nan
            loo_scores[set_name] = np.nan

    # Calculate feature importance and correlations
    feature_importance = calculate_feature_importance(feature_matrix, target_vector, feature_names)
    feature_correlations = calculate_feature_correlations(feature_matrix)

    return FeatureEvaluationResults(
        cv_scores=cv_scores,
        waic_scores=waic_scores,
        loo_scores=loo_scores,
        feature_correlations=feature_correlations,
        feature_importance=feature_importance,
        feature_groups=config['features']['groups'],
        interaction_scores=None,
        stability_metrics=None
    )

def train_bayesian_glmm(
   feature_matrix: pd.DataFrame,
   target_vector: np.ndarray,
   participants: np.ndarray,
   design_features: List[str],
   control_features: List[str],
   inference_method: str = 'nuts',
   num_samples: int = 1000,
   chains: int = 4
) -> Tuple:
   """
    Train Bayesian Generalized Linear Mixed Model (GLMM) for keyboard layout analysis.
    
    This function fits a hierarchical model that accounts for:
    - Fixed effects from design features (layout characteristics)
    - Fixed effects from control features (e.g., typing time)
    - Random effects per participant
    
    Args:
        feature_matrix: DataFrame of feature values for bigram pairs
        target_vector: Array of comfort scores or preference ratings
        participants: Array of participant IDs for random effects
        design_features: Names of features related to keyboard layout design
        control_features: Names of features to control for (e.g., typing time)
        inference_method: MCMC method to use ('nuts' recommended)
        num_samples: Number of posterior samples to draw
        chains: Number of independent MCMC chains
        
    Returns:
        Tuple containing:
        - trace: ArviZ InferenceData object with posterior samples
        - model: Fitted PyMC model
        - priors: Dictionary of model prior distributions
    """
   logger.info("Starting Bayesian GLMM training")

   # Scale features
   scaler = StandardScaler()
   X_scaled = pd.DataFrame(
       scaler.fit_transform(feature_matrix),
       columns=feature_matrix.columns
   )

   # Create participant mapping for indexing
   unique_participants = np.unique(participants)
   participant_map = {p: i for i, p in enumerate(unique_participants)}
   n_participants = len(unique_participants)

   with pm.Model() as model:
       # Priors for design features
       design_effects = {
           feat: pm.Normal(feat, mu=0, sigma=1)
           for feat in design_features
       }

       # Priors for control features
       control_effects = {
           feat: pm.Normal(feat, mu=0, sigma=1)
           for feat in control_features
       }

       # Random effects for participants
       participant_sigma = pm.HalfNormal('participant_sigma', sigma=1)
       participant_offset = pm.Normal('participant_offset',
                                    mu=0,
                                    sigma=participant_sigma,
                                    shape=n_participants)

       # Error term
       sigma = pm.HalfNormal('sigma', sigma=1)

       # Expected value combining fixed and random effects
       mu = 0
       # Add design feature effects
       for feat in design_features:
           mu += design_effects[feat] * X_scaled[feat]
       # Add control feature effects
       for feat in control_features:
           mu += control_effects[feat] * X_scaled[feat]
       # Add participant random effects
       mu += participant_offset[[participant_map[p] for p in participants]]

       # Likelihood
       likelihood = pm.Normal('likelihood', mu=mu, sigma=sigma, observed=target_vector)

       # Sample using NUTS
       logger.info(f"Using {inference_method} inference")
       trace = pm.sample(
            draws=num_samples,
            tune=2000,
            chains=chains,
            target_accept=0.99,
            return_inferencedata=True,
            compute_convergence_checks=True,
            cores=1
       )

       # Collect priors
       priors = {
           'design_effects': design_effects,
           'control_effects': control_effects,
           'participant_sigma': participant_sigma,
           'sigma': sigma
       }

       logger.info("Model training completed successfully")

       return trace, model, priors
   
def calculate_bigram_comfort_scores(
       trace: az.InferenceData,
       feature_matrix: pd.DataFrame,
       features_for_design: List[str],
       mirror_left_right_scores: bool = True) -> Dict[Tuple[str, str], float]:
   """
    Calculate comfort scores for bigram pairs using trained model parameters.
    
    Takes the posterior distributions from a trained model and computes expected
    comfort scores for bigram pairs. Can optionally mirror scores from left to
    right hand keys.
    
    Args:
        trace: ArviZ InferenceData object containing posterior samples
        feature_matrix: DataFrame of feature values for bigram pairs
        features_for_design: List of feature names to use for score calculation
        mirror_left_right_scores: If True, mirror scores from left to right hand keys
        
    Returns:
        Dictionary mapping bigram pairs to their predicted comfort scores
   """   
   # Extract design feature effects from posterior
   posterior_samples = {param: az.extract(trace, var_names=param).values
                       for param in features_for_design 
                       if param in feature_matrix.columns}
   
   # Verify all needed features exist
   missing = set(features_for_design) - set(feature_matrix.columns)
   if missing:
       raise ValueError(f"Missing features: {missing}")
       
   scores = {}
   for bigram, features in feature_matrix.iterrows():
       effect = np.zeros(len(next(iter(posterior_samples.values()))))
       for param, samples in posterior_samples.items():
           effect += samples * features[param]
       scores[bigram] = float(np.mean(effect))
   
   # Normalize and mirror if requested
   scores = normalize_scores(scores)
   if mirror_left_right_scores:
       scores = add_mirrored_scores(scores)
       
   return scores

def validate_comfort_scores(
   comfort_scores: Dict[Tuple[str, str], float],
   test_data: ProcessedData
) -> Dict[str, float]:
   """Validate comfort scores against held-out test data."""
   
   validation_metrics = {}
   
   # Convert scores to preferences
   predicted_prefs = []
   actual_prefs = []
   
   for (bigram1, bigram2), pref in test_data.bigram_pairs:
       if bigram1 in comfort_scores and bigram2 in comfort_scores:
           pred = comfort_scores[bigram1] - comfort_scores[bigram2]
           predicted_prefs.append(pred)
           actual_prefs.append(pref)
           
   predicted_prefs = np.array(predicted_prefs)
   actual_prefs = np.array(actual_prefs)
   
   # Calculate metrics
   validation_metrics['accuracy'] = np.mean(
       np.sign(predicted_prefs) == np.sign(actual_prefs)
   )
   validation_metrics['correlation'] = stats.spearmanr(
       predicted_prefs, actual_prefs
   )[0]
   
   return validation_metrics

def save_model_results(trace: az.InferenceData, 
                      model: pm.Model, 
                      base_filename: str) -> None:
    """Save model results to files."""
    # Save trace
    az.to_netcdf(trace, filename=f"{base_filename}_trace.nc")
    
    # Save point estimates
    point_estimates = az.summary(trace)
    point_estimates.to_csv(f"{base_filename}_point_estimates.csv")
    
    # Save model configuration
    model_config = {
        'input_vars': [var.name for var in model.named_vars.values() 
                      if hasattr(var, 'distribution')],
        'observed_vars': [var.name for var in model.observed_RVs],
        'free_vars': [var.name for var in model.free_RVs],
    }
    
    # Save prior information
    prior_info = {}
    for var in model.named_vars.values():
        if hasattr(var, 'distribution'):
            prior_info[var.name] = {
                'distribution': var.distribution.__class__.__name__,
                'parameters': {k: str(v) for k, v in var.distribution.parameters.items()
                             if k != 'name'}
            }
    
    model_info = {
        'config': model_config,
        'priors': prior_info
    }
    
    with open(f"{base_filename}_model_info.json", "w") as f:
        json.dump(model_info, f, indent=2)

def load_model_results(base_filename: str) -> Tuple[az.InferenceData, pd.DataFrame, Dict]:
    """Load saved model results."""
    trace = az.from_netcdf(f"{base_filename}_trace.nc")
    point_estimates = pd.read_csv(f"{base_filename}_point_estimates.csv", index_col=0)
    
    with open(f"{base_filename}_model_info.json", "r") as f:
        model_info = json.load(f)
    
    return trace, point_estimates, model_info

def perform_sensitivity_analysis(
        feature_matrix: pd.DataFrame,
        target_vector: np.ndarray,
        participants: np.ndarray,
        design_features: List[str],
        control_features: List[str],
        prior_scale_factors: List[float]) -> Dict[str, Any]:
    """Perform sensitivity analysis on model priors."""
    logger.info("Starting sensitivity analysis")
    
    parameter_estimates = {}
    convergence_metrics = {}
    sampling_issues = {}
    
    baseline_sds = {feature: np.std(feature_matrix[feature])
                   for feature in design_features + control_features}
    
    for scale in prior_scale_factors:
        config_name = f"scale_{scale:.1f}"
        logger.info(f"Testing prior scale factor: {scale}")
        
        try:
            trace, _, _ = train_bayesian_glmm(
                feature_matrix=feature_matrix,
                target_vector=target_vector,
                participants=participants,
                design_features=design_features,
                control_features=control_features,
                num_samples=1000,
                chains=2
            )
            
            summary = az.summary(trace)
            parameter_estimates[config_name] = summary
            
            convergence_metrics[config_name] = {
                'r_hat': summary['r_hat'].values,
                'ess_bulk': summary['ess_bulk'].values,
                'ess_tail': summary['ess_tail'].values
            }
            
        except Exception as e:
            logger.error(f"Error with scale factor {scale}: {str(e)}")
            sampling_issues[config_name] = str(e)
            continue
    
    results = {
        'parameter_estimates': parameter_estimates,
        'convergence_metrics': convergence_metrics,
        'sampling_issues': sampling_issues
    }
    
    return results

def plot_model_diagnostics(trace, output_base_path: str, inference_method: str) -> None:
    """Plot diagnostics with proper dimension handling."""
    try:
        # Get available variables excluding composite ones
        available_vars = [var for var in trace.posterior.variables 
                         if not any(dim in var for dim in ['chain', 'draw', 'dim'])]
        
        if available_vars:
            az.plot_trace(trace, var_names=available_vars)
            plt.savefig(output_base_path.format(inference_method=inference_method))
            plt.close()
        
        # Plot forest plot for parameters only
        param_vars = [var for var in available_vars 
                     if var not in ['participant_offset', 'participant_sigma', 'sigma']]
        if param_vars:
            az.plot_forest(trace, var_names=param_vars)
            plt.savefig(output_base_path.format(inference_method=inference_method)
                       .replace('diagnostics', 'forest'))
            plt.close()
            
    except Exception as e:
        logger.warning(f"Could not create some diagnostic plots: {str(e)}")

def evaluate_model_performance(predictions: np.ndarray, 
                            true_values: np.ndarray,
                            participants: np.ndarray) -> Dict[str, float]:
   """
   Evaluate model predictions against test data.
   
   Returns dict with metrics:
   - R² score
   - RMSE
   - Mean absolute error
   - Pairwise accuracy (% correctly predicted preferences)
   - Per-participant metrics
   """
   metrics = {}
   
   # Overall metrics
   ss_res = np.sum((true_values - predictions) ** 2)
   ss_tot = np.sum((true_values - np.mean(true_values)) ** 2)
   metrics['r2'] = 1 - (ss_res / ss_tot)
   metrics['rmse'] = np.sqrt(np.mean((true_values - predictions) ** 2))
   metrics['mae'] = np.mean(np.abs(true_values - predictions))
   
   # Pairwise accuracy
   correct_pairs = np.sign(predictions) == np.sign(true_values)
   metrics['pairwise_accuracy'] = np.mean(correct_pairs)
   
   # Per-participant breakdown
   unique_participants = np.unique(participants)
   participant_metrics = {}
   for p in unique_participants:
       mask = participants == p
       p_true = true_values[mask]
       p_pred = predictions[mask]
       participant_metrics[p] = {
           'r2': 1 - (np.sum((p_true - p_pred) ** 2) / 
                     np.sum((p_true - np.mean(p_true)) ** 2)),
           'accuracy': np.mean(np.sign(p_pred) == np.sign(p_true))
       }
   metrics['participant_breakdown'] = participant_metrics
   
   return metrics

def plot_sensitivity_analysis(parameter_estimates: Dict[str, pd.DataFrame],
                              design_features: List[str],
                              control_features: List[str],
                              output_path: str) -> None:
    """
    Create visualization of sensitivity analysis results.
    
    Args:
        parameter_estimates: Dictionary of parameter estimates
        design_features: List of design features
        control_features: List of control features
        output_path: Path to save the plot
    """
    plt.figure(figsize=(12, 6))
    
    # Design features plot
    plt.subplot(2, 1, 1)
    data = []
    labels = []
    for feature in design_features:
        means = [est.loc[feature, 'mean'] for est in parameter_estimates.values()]
        data.append(means)
        labels.append(feature)
    
    plt.boxplot(data, labels=labels)
    plt.title('Design Feature Effect Estimates')
    plt.ylabel('Effect Size')
    plt.grid(True, alpha=0.3)
    
    # Control features plot
    if control_features:
        plt.subplot(2, 1, 2)
        data = []
        labels = []
        for feature in control_features:
            means = [est.loc[feature, 'mean'] for est in parameter_estimates.values()]
            data.append(means)
            labels.append(feature)
        
        plt.boxplot(data, labels=labels)
        plt.title('Control Feature Effect Estimates')
        plt.ylabel('Effect Size')
        plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()

def normalize_scores(scores: Dict[Tuple[str, str], float]) -> Dict[Tuple[str, str], float]:
    """Normalize comfort scores to 0-1 range."""
    min_score = min(scores.values())
    max_score = max(scores.values())
    return {bigram: (score - min_score) / (max_score - min_score)
            for bigram, score in scores.items()}

def add_mirrored_scores(scores: Dict[Tuple[str, str], float]) -> Dict[Tuple[str, str], float]:
    """Add mirrored scores for right hand keys."""
    left_keys = "qwertasdfgzxcvb"
    right_keys = "poiuy;lkjh/.,mn"
    key_mapping = dict(zip(left_keys, right_keys))
    
    mirrored = {}
    for bigram, score in scores.items():
        right_bigram = (key_mapping.get(bigram[0], bigram[0]),
                       key_mapping.get(bigram[1], bigram[1]))
        mirrored[right_bigram] = score
    
    return {**scores, **mirrored}

