"""
Main script for keyboard layout analysis pipeline.

This script orchestrates the entire keyboard layout analysis process:
1. Data preprocessing
2. Feature extraction
3. Full dataset analyses:
   - Timing and frequency analysis
   - Feature space analysis
4. Train/test splitting
5. Split dataset analyses:
   - Feature evaluation (using test_data)
   - Bayesian model training (using train_data)
   - Bayesian model testing (using test_data)
"""
import logging
import argparse
from pathlib import Path
import yaml
from typing import Dict, Any
import pandas as pd

from data_processing import DataPreprocessor, generate_train_test_splits, manage_data_splits
from bigram_frequency_timing import (plot_frequency_timing_relationship, plot_timing_by_frequency_groups,
                                     save_timing_analysis)
from bigram_feature_definitions import (column_map, row_map, finger_map, engram_position_values,
                                        row_position_values, bigrams, bigram_frequencies_array)
from bigram_feature_extraction import (precompute_all_bigram_features, precompute_bigram_feature_differences)
from bigram_pair_feature_evaluation import evaluate_feature_sets
from bigram_pair_recommendations import (analyze_feature_space, save_feature_space_analysis_results)
from bayesian_modeling import (train_bayesian_glmm, calculate_bigram_comfort_scores, 
                               save_model_results, plot_model_diagnostics, evaluate_model_performance, 
                               validate_comfort_scores)

logger = logging.getLogger(__name__)

def validate_config(config: Dict[str, Any]) -> None:
    """
    Validate configuration structure and required fields.
    
    Args:
        config: Configuration dictionary to validate
        
    Raises:
        ValueError: If required configuration is missing or invalid
    """
    required_sections = [
        'data',           # Data settings including file, splits, layout
        'paths',          # All file/directory paths
        'analysis',       # Analysis settings
        'features',       # Feature definitions and groups
        'model',          # Model settings
        'logging'         # Logging settings
    ]
    
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")
    
    # Validate data section
    required_data_settings = ['file', 'splits', 'layout']
    for setting in required_data_settings:
        if setting not in config['data']:
            raise ValueError(f"Missing required data setting: {setting}")
            
    # Validate splits settings
    if not all(key in config['data']['splits'] for key in ['generate', 'train_ratio']):
        raise ValueError("Missing required splits settings")
    
    # Validate layout settings
    if 'left_chars' not in config['data']['layout']:
        raise ValueError("Missing left_chars in layout settings")
    
    # Validate model settings if training enabled
    if config['model'].get('train', False):
        required_model_settings = ['inference_method', 'num_samples', 'chains']
        for setting in required_model_settings:
            if setting not in config['model']:
                raise ValueError(f"Missing required model setting: {setting}")

def setup_logging(config: Dict[str, Any]) -> None:
    """Setup logging configuration."""
    handlers = [
        logging.FileHandler(config['paths']['logs']),
        logging.StreamHandler()
    ]
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(config['logging']['level'])
    
    # Create and set formatter
    formatter = logging.Formatter(config['logging']['format'])
    
    # Add handlers with formatter
    for handler in handlers:
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        
    logger.info("Logging setup completed")

def load_config(config_path: str) -> Dict[str, Any]:
    """Load and validate configuration from YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    validate_config(config)
    return config

def create_output_directories(config: Dict[str, Any]) -> None:
    """
    Create all necessary output directories.
    
    Args:
        config: Configuration dictionary containing output paths
    """
    dirs_to_create = [
        Path(config['paths']['base']),
        Path(config['paths']['logs']),
        Path(config['paths']['feature_evaluation']),
        Path(config['paths']['feature_space']['dir']),
        Path(config['paths']['feature_space']['analysis']).parent,
        Path(config['paths']['feature_space']['recommendations']).parent,
        Path(config['paths']['feature_space']['pca']).parent,
        Path(config['paths']['feature_space']['bigram_graph']).parent,
        Path(config['paths']['feature_space']['underrepresented']).parent,
        Path(config['paths']['frequency_timing']['dir']),
        Path(config['paths']['frequency_timing']['analysis']).parent,
        Path(config['paths']['frequency_timing']['relationship']).parent,
        Path(config['paths']['model']['dir']),
        Path(config['paths']['model']['results']).parent,
        Path(config['paths']['model']['diagnostics']).parent,
        Path(config['paths']['model']['forest']).parent,
        Path(config['paths']['model']['posterior']).parent,
        Path(config['paths']['model']['participant_effects']).parent,
        Path(config['paths']['model']['sensitivity']).parent,
        Path(config['paths']['scores']).parent
    ]

    for directory in dirs_to_create:
        if not directory.exists():
            logger.info(f"Creating directory: {directory}")
            directory.mkdir(parents=True, exist_ok=True)

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Keyboard Layout Analysis Pipeline')
    parser.add_argument('--config', default='config.yaml', help='Path to configuration file')
    args = parser.parse_args()

    # Load and validate configuration
    config = load_config(args.config)
    
    # Create logs directory and setup logging
    Path(config['paths']['logs']).parent.mkdir(parents=True, exist_ok=True)
    setup_logging(config)
    logger = logging.getLogger(__name__)

    logger.info("Starting keyboard layout analysis pipeline")

    try:
        # Create all output directories
        create_output_directories(config)

        # Initialize preprocessor and load data
        logger.info("Loading and preprocessing data")
        preprocessor = DataPreprocessor(config['data']['file'])
        preprocessor.load_data()

        # Prepare features
        logger.info("Computing bigram features")
        all_bigrams, all_bigram_features, feature_names, samekey_bigrams, \
            samekey_bigram_features, samekey_feature_names = precompute_all_bigram_features(
                layout_chars=config['data']['layout']['left_chars'],
                column_map=column_map, 
                row_map=row_map, 
                finger_map=finger_map,
                engram_position_values=engram_position_values,
                row_position_values=row_position_values,
                bigrams=bigrams,
                bigram_frequencies_array=bigram_frequencies_array,
                config=config
            )

        # Compute feature differences
        all_feature_differences = precompute_bigram_feature_differences(all_bigram_features)

        # Process data
        logger.info("Processing data")
        preprocessor.prepare_bigram_pairs()
        preprocessor.extract_target_vector()
        preprocessor.process_participants()
        preprocessor.extract_typing_times()  # Add this line
        preprocessor.create_feature_matrix(
            all_feature_differences=all_feature_differences,
            feature_names=feature_names,
            config=config
        )

        # Get processed data BEFORE splitting
        processed_data = preprocessor.get_processed_data()

        # === FULL DATASET ANALYSES === #

        # Analyze bigram frequency/timing relationship if enabled
        if config['analysis']['frequency_timing']['enabled']:
            logger.info("Starting frequency/timing analysis")
            
            try:
                timing_results = plot_frequency_timing_relationship(
                    bigram_data=processed_data,
                    bigrams=bigrams,
                    bigram_frequencies_array=bigram_frequencies_array,
                    output_path=config['paths']['frequency_timing']['relationship']
                )
                
                if 'error' in timing_results:
                    logger.error(f"Frequency-timing analysis failed: {timing_results['error']}")
                else:
                    try:
                        save_timing_analysis(
                            timing_results, 
                            None,
                            config['paths']['frequency_timing']['analysis']
                        )
                        logger.info("Frequency/timing analysis completed and saved")
                        logger.info(f"Results:")
                        logger.info(f"  Raw correlation: {timing_results['raw_correlation']:.3f} (p = {timing_results['raw_p_value']:.3e})")
                        logger.info(f"  R-squared: {timing_results['r2']:.3f}")
                        logger.info(f"  Number of unique bigrams: {timing_results['n_unique_bigrams']}")
                    except Exception as e:
                        logger.error(f"Error saving timing analysis: {str(e)}")
            except Exception as e:
                logger.error(f"Error in frequency-timing analysis: {str(e)}")

        # Evaluate feature space
        if config['analysis']['feature_space']['enabled']:
            logger.info("Analyzing feature space")
            try:
                # Feature space analysis
                feature_space_results = analyze_feature_space(
                    feature_matrix=processed_data.feature_matrix,
                    output_paths=config['paths']['feature_space'],
                    all_feature_differences=all_feature_differences,
                    config=config,
                    recommend_bigrams=config['analysis']['feature_space']['recommend_bigrams'],
                    num_recommendations=config['analysis']['feature_space']['num_recommendations']
                )
                
                if feature_space_results is None:
                    logger.error("Feature space analysis returned no results")
                else:
                    # Save analysis results
                    save_feature_space_analysis_results(
                        feature_space_results, 
                        config['analysis']['feature_space']['analysis']
                    )

                    # Log recommendations and feature space metrics
                    logger.info(f"Feature space analysis completed:")
                    if 'feature_space_metrics' in feature_space_results:
                        logger.info(f"  Hull area: {feature_space_results['feature_space_metrics']['hull_area']:.3f}")
                        logger.info(f"  Point density: {feature_space_results['feature_space_metrics']['point_density']:.3f}")
                    if 'recommendations' in feature_space_results:
                        logger.info(f"  Generated {len(feature_space_results['recommendations'])} bigram pair recommendations")
            except Exception as e:
                logger.error(f"Error in feature space analysis: {str(e)}")
                if config['model']['train']:
                    logger.warning("Continuing with model training despite feature space analysis failure")

        # === SPLIT DATASET ANALYSES === #
        
        # Now create train/test splits for evaluation and modeling
        generate_train_test_splits(processed_data, config)
        train_data, test_data = manage_data_splits(processed_data, config)

        # Run feature evaluation on test data
        if config['analysis']['feature_evaluation']['enabled']:            
            logger.info("Starting feature evaluation on test data")
            feature_eval_results = evaluate_feature_sets(
                feature_matrix=test_data.feature_matrix,
                target_vector=test_data.target_vector,
                participants=test_data.participants,
                candidate_features=config['analysis']['feature_evaluation']['combinations'],
                feature_names=feature_names,
                output_dir=Path(config['paths']['feature_evaluation']),
                config=config,
                n_splits=config['analysis']['feature_evaluation']['n_splits'],
                n_samples=config['analysis']['feature_evaluation']['n_samples']
            )
            logger.info("Feature evaluation completed")

        # Train model on training data if requested
        if config['model']['train']:
            logger.info("Training Bayesian GLMM on training data")
            
            # Train model
            trace, model, priors = train_bayesian_glmm(
                feature_matrix=train_data.feature_matrix,
                target_vector=train_data.target_vector,
                participants=train_data.participants,
                design_features=config['features']['groups']['design'],
                control_features=config['features']['groups']['control'],
                inference_method=config['model']['inference_method'],
                num_samples=config['model']['num_samples'],
                chains=config['model']['chains']
            )

            # Save model results
            model_prefix = f"{config['paths']['model']['results']}_{config['model']['inference_method']}"
            save_model_results(trace, model, model_prefix)

            # Plot diagnostics
            if config['model'].get('visualization', {}).get('enabled', False):
                logger.info("Generating model diagnostics")
                plot_model_diagnostics(
                    trace=trace,
                    output_base_path=config['paths']['model']['diagnostics'],
                    inference_method=config['model']['inference_method']
                )

            # Calculate comfort scores using the trained model
            if config['model'].get('scoring', {}).get('enabled', False):
                logger.info("Calculating comfort scores")
                comfort_scores = calculate_bigram_comfort_scores(
                    trace,
                    train_data.feature_matrix,
                    features_for_design=config['features']['groups']['design'],
                    mirror_left_right_scores=config['model']['scoring'].get('mirror_left_right_scores', True)
                )

                # Validate scores against test data
                validate_comfort_scores(comfort_scores, test_data)

                # Save comfort scores
                output_path = Path(config['paths']['scores'])
                pd.DataFrame.from_dict(comfort_scores, orient='index',
                                     columns=['comfort_score']).to_csv(output_path)

            # Evaluate model on test data
            if config['model'].get('evaluate_test', True):
                logger.info("Evaluating model on test data")
                test_score = evaluate_model_performance(
                    trace=trace,
                    feature_matrix=test_data.feature_matrix,
                    target_vector=test_data.target_vector,
                    participants=test_data.participants,
                    design_features=config['features']['groups']['design'],
                    control_features=config['features']['groups']['control']
                )
                logger.info(f"Test set performance metrics:")
                for metric, value in test_score.items():
                    logger.info(f"  {metric}: {value:.3f}")

        logger.info("Pipeline completed successfully")

    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()