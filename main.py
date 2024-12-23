# main.py
"""
Command-line interface and pipeline orchestration for the Engram3 keyboard layout optimization system.

Provides four main operational modes:

1. Feature Selection ('select_features'):
   - Loads and splits typing preference dataset
   - Evaluates base features and their interactions
   - Performs feature selection with stability analysis
   - Saves comprehensive feature metrics and selection results
   - Generates feature importance visualizations

2. Feature Space Visualization ('visualize_feature_space'):
   - Projects bigrams into reduced feature space
   - Visualizes feature relationships and impacts
   - Generates multiple analysis plots:
     * PCA feature space projection
     * Feature weight impact analysis
     * Selected vs. non-selected feature comparisons

3. Model Training ('train_model'):
   - Creates participant-aware train/test splits
   - Trains Bayesian preference model on selected features
   - Evaluates model performance on holdout data
   - Saves trained model and performance metrics

4. Bigram Recommendations ('recommend_bigram_pairs'):
   - Generates candidate bigram pairs
   - Scores pairs using multiple criteria
   - Visualizes recommendations in feature space
   - Exports recommended pairs for data collection

Core functionality:
- Configuration management via YAML
- Comprehensive logging system
- Reproducible train/test splitting
- Feature precomputation and caching
- Error handling and validation
- Results visualization and export

Usage:
    python main.py --config config.yaml --mode [select_features|visualize_feature_space|train_model|recommend_bigram_pairs]
"""
import argparse
import yaml
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from pathlib import Path
import matplotlib.pyplot as plt
from itertools import combinations

from engram3.utils.config import Config
from engram3.data import PreferenceDataset
from engram3.model import PreferenceModel
from engram3.recommendations import BigramRecommender
from engram3.utils.visualization import plot_feature_space
from engram3.features.feature_extraction import FeatureExtractor, FeatureConfig
from engram3.features.features import angles
from engram3.features.keymaps import (
    column_map, row_map, finger_map,
    engram_position_values, row_position_values
)
from engram3.features.bigram_frequencies import bigrams, bigram_frequencies_array
from engram3.utils.logging import LoggingManager
logger = LoggingManager.getLogger(__name__)

def load_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def load_or_create_split(dataset: PreferenceDataset, config: Dict) -> Tuple[PreferenceDataset, PreferenceDataset]:
    """
    Load existing train/test split or create and save a new one.
    """
    split_file = Path(config.data.splits['split_data_file'])
    
    # If split file exists, delete it to force new split creation
    if split_file.exists():
        logger.info("Removing existing split file to create new split...")
        split_file.unlink()
    
    try:
        logger.info("Creating new train/test split...")
        
        # Get test size from config
        test_ratio = config.data.splits['test_ratio']
        
        # Set random seed for reproducibility
        np.random.seed(config.data.splits['random_seed'])
        
        # Get unique participant IDs and their corresponding preference indices
        participant_to_indices = {}
        for i, pref in enumerate(dataset.preferences):
            if pref.participant_id not in participant_to_indices:
                participant_to_indices[pref.participant_id] = []
            participant_to_indices[pref.participant_id].append(i)
        
        # Randomly select participants for test set
        all_participants = list(participant_to_indices.keys())
        n_test = int(len(all_participants) * test_ratio)
        test_participants = set(np.random.choice(all_participants, n_test, replace=False))
        train_participants = set(all_participants) - test_participants
        
        logger.info(f"Split participants: {len(train_participants)} train, {len(test_participants)} test")
        
        # Split indices based on participants
        train_indices = []
        test_indices = []
        for participant, indices in participant_to_indices.items():
            if participant in test_participants:
                test_indices.extend(indices)
            else:
                train_indices.extend(indices)
        
        train_indices = np.array(train_indices)
        test_indices = np.array(test_indices)
        
        logger.info(f"Split preferences: {len(train_indices)} train, {len(test_indices)} test")
        
        # Save split
        split_file.parent.mkdir(parents=True, exist_ok=True)
        np.savez(split_file, train_indices=train_indices, test_indices=test_indices)
        
        # Create datasets
        train_data = dataset._create_subset_dataset(train_indices)
        test_data = dataset._create_subset_dataset(test_indices)
        
        # Verify no overlap in participants
        train_participants_actual = set(p.participant_id for p in train_data.preferences)
        test_participants_actual = set(p.participant_id for p in test_data.preferences)
        
        if train_participants_actual & test_participants_actual:
            overlap = train_participants_actual & test_participants_actual
            logger.error(f"Train participants: {len(train_participants_actual)}")
            logger.error(f"Test participants: {len(test_participants_actual)}")
            logger.error(f"Overlap: {len(overlap)}")
            logger.error(f"Sample overlapping IDs: {list(overlap)[:5]}")
            raise ValueError("Train and test sets contain overlapping participants")
            
        return train_data, test_data
        
    except Exception as e:
        logger.error(f"Error in split creation: {str(e)}")
        logger.error(f"Dataset preferences: {len(dataset.preferences)}")
        logger.error(f"Total participants: {len(participant_to_indices)}")
        raise

def main():
    parser = argparse.ArgumentParser(description='Preference Learning Pipeline')
    parser.add_argument('--config', default='config.yaml', help='Path to configuration file')
    parser.add_argument('--mode', choices=['select_features', 'visualize_feature_space', 
                                       'train_model', 'recommend_bigram_pairs'], 
                       required=True,
                       help='Pipeline mode: feature selection, model training, or bigram recommendations')
    args = parser.parse_args()
    
    print("\n=== DEBUG: Program Start ===")
    print(f"Mode argument: {args.mode}")
    print(f"Mode type: {type(args.mode)}")
    print(f"Mode comparison: {'select_features' == args.mode}")

    try:
        # Load configuration and convert to Pydantic model
        config_dict = load_config(args.config)
        print(f"Loaded config: {config_dict}")
        config = Config(**config_dict)
        print(f"Config features: {config.features}")

        if args.mode == 'select_features':
            print("=== DEBUG: select_features mode triggered ===")
        else:
            print(f"=== DEBUG: different mode triggered: {args.mode} ===")
                    
        # Setup logging using LoggingManager
        LoggingManager(config).setup_logging()        
        
        # Set random seed for all operations
        np.random.seed(config.data.splits['random_seed'])
        
        # Initialize feature extraction
        logger.info("Initializing feature extraction...")
        # Debug to check the values are imported
        logger.debug(f"Loaded bigrams: {len(bigrams)} items")
        logger.debug(f"Loaded bigram frequencies: {bigram_frequencies_array.shape}")
        feature_config = FeatureConfig(
            column_map=column_map,
            row_map=row_map,
            finger_map=finger_map,
            engram_position_values=engram_position_values,
            row_position_values=row_position_values,
            angles=angles,
            bigrams=bigrams,
            bigram_frequencies_array=bigram_frequencies_array
        )
        feature_extractor = FeatureExtractor(feature_config)
        
        # Precompute features for all possible bigrams
        logger.info("Precomputing bigram features...")
        all_bigrams, all_bigram_features = feature_extractor.precompute_all_features(
            config.data.layout['chars']
        )
        # Debug:
        logger.debug("First bigram features:")
        first_bigram = next(iter(all_bigram_features))
        logger.debug(f"  bigram: {first_bigram}")
        logger.debug(f"  features: {all_bigram_features[first_bigram]}")

        # Get feature names from first computed features
        feature_names = list(next(iter(all_bigram_features.values())).keys())
        
        # Load dataset with precomputed features
        logger.info("Loading dataset...")
        dataset = PreferenceDataset(
            Path(config.data.input_file),
            feature_extractor=feature_extractor,  # Make sure this is passed
            config=config,
            precomputed_features={
                'all_bigrams': all_bigrams,
                'all_bigram_features': all_bigram_features,
                'feature_names': feature_names
            }
        )

        #---------------------------------
        # Select features
        #---------------------------------
        if args.mode == 'select_features':
            print("\n=== MAIN: FEATURE SELECTION MODE STARTING ===")
            print(f"Config base features: {config.features.base_features}")
            print(f"Config interactions: {config.features.interactions}")
            print(f"Config control features: {config.features.control_features}")

            # Get train/test split
            train_data, holdout_data = load_or_create_split(dataset, config)
            print(f"Split complete: {len(train_data.preferences)} train, {len(holdout_data.preferences)} test")

            # Get all features including interactions and control features
            base_features = config.features.base_features
            interaction_features = [f"{f1}_x_{f2}" for f1, f2 in config.features.interactions]
            control_features = config.features.control_features
            all_features = base_features + interaction_features + control_features
            
            print("\nFeatures prepared:")
            print(f"Base features: {base_features}")
            print(f"Interaction features: {interaction_features}")
            print(f"Control features: {control_features}")
            print(f"All features: {all_features}")

            # Initialize model
            model = PreferenceModel(config=config)
            
            print("\nAbout to call model.select_features with:")
            print(f"all_features: {all_features}")
            selected_features = model.select_features(train_data, all_features)
            print(f"select_features returned: {selected_features}")
                                    
            # Select features using round-robin tournament
            logger.info("Calling model.select_features()...")
            selected_features = model.select_features(train_data, all_features)
            logger.info(f"Feature selection completed. Selected features: {selected_features}")
            
            # Final fit with selected features
            logger.info("Fitting final model with selected features...")
            model.fit(train_data, selected_features)
            
            # Save the trained model
            model_save_path = Path(config.feature_selection.model_file)
            logger.info(f"Saving model to {model_save_path}")
            model.save(model_save_path)
            
            # Get final weights and metrics
            feature_weights = model.get_feature_weights(include_control=True)  # Add include_control=True

            # Create comprehensive results DataFrame
            logger.info("\n=== Starting feature evaluation loop ===")
            logger.info(f"All features: {all_features}")

            # Define selectable features BEFORE trying to log it
            selectable_features = [f for f in all_features if f not in config.features.control_features]
            logger.info(f"Selectable features: {selectable_features}")

            results = []
            for feature_name in selectable_features:  # Only evaluate non-control features
                metrics = model.importance_calculator.evaluate_feature(
                    feature=feature_name,
                    dataset=train_data,
                    model=model,
                    all_features=all_features,
                    current_selected_features=selected_features
                )
                
                weight, std = feature_weights.get(feature_name, (0.0, 0.0))
                components = feature_name.split('_x_')
                
                results.append({
                    'feature_name': feature_name,
                    'n_components': len(components),
                    'selected': 1 if feature_name in selected_features else 0,
                    'model_effect': metrics.get('model_effect', 0.0),
                    'effect_consistency': metrics.get('effect_consistency', 0.0),
                    'predictive_power': metrics.get('predictive_power', 0.0),
                    'weight': weight,
                    'weight_std': std
                })

            # Log final results
            logger.info("\n=== Feature evaluation complete ===")
            logger.info(f"Final model state:")
            logger.info(f"  Feature names: {model.feature_names}")
            logger.info(f"  Selected features: {model.selected_features}")
            logger.info(f"Results dataframe:")
            for result in results:
                logger.info(f"  {result}")
            
            # Save comprehensive metrics
            metrics_file = Path(config.feature_selection.metrics_file)
            pd.DataFrame(results).to_csv(metrics_file, index=False)
            
            # Print summary
            logger.info("\nFeature selection summary:")
            logger.info(f"Total features evaluated: {len(all_features)}")
            logger.info(f"Base features: {len(base_features)}")
            logger.info(f"Interaction features: {len(interaction_features)}")
            logger.info(f"Features selected: {len(selected_features)}")

            logger.info("\nSelected features:")
            # Change this part
            feature_weights = model.get_feature_weights(include_control=True)  # Add include_control=True
            for feature in selected_features:
                weight, std = feature_weights.get(feature, (0.0, 0.0))  # Use .get() with default
                metrics = model.importance_calculator.evaluate_feature(
                    feature=feature,
                    dataset=train_data,
                    model=model,
                    all_features=all_features,  # We have this from earlier
                    current_selected_features=selected_features
                )
                logger.info(f"\n{feature}:")
                logger.info(f"  Weight: {weight:.3f} ± {std:.3f}")
                logger.info(f"  Effect magnitude: {metrics.get('model_effect', 0.0):.3f}")
                logger.info(f"  Effect consistency: {metrics.get('effect_consistency', 0.0):.3f}")
                logger.info(f"  Predictive power: {metrics.get('predictive_power', 0.0):.3f}")

        #---------------------------------
        # Visualize feature space
        #---------------------------------
        if args.mode == 'visualize_feature_space':
            logger.info("Generating feature analysis visualizations...")
            
            # Load feature selection model
            selection_model_save_path = Path(config.feature_selection.model_file)
            feature_selection_model = PreferenceModel.load(selection_model_save_path)
            
            # Initialize feature extraction
            logger.info("Initializing feature extraction...")
            # Debug to check the values are imported
            logger.debug(f"Loaded bigrams: {len(bigrams)} items")
            logger.debug(f"Loaded bigram frequencies: {bigram_frequencies_array.shape}")
            feature_config = FeatureConfig(
                column_map=column_map,
                row_map=row_map,
                finger_map=finger_map,
                engram_position_values=engram_position_values,
                row_position_values=row_position_values,
                angles=angles,
                bigrams=bigrams,
                bigram_frequencies_array=bigram_frequencies_array
            )
            feature_extractor = FeatureExtractor(feature_config)
            
            # Precompute features for all possible bigrams
            logger.info("Precomputing bigram features...")
            all_bigrams, all_bigram_features = feature_extractor.precompute_all_features(
                config.data.layout['chars']
            )
            
            # Get feature names from first computed features
            feature_names = list(next(iter(all_bigram_features.values())).keys())
            
            # Load dataset with precomputed features
            logger.info("Loading dataset...")
            dataset = PreferenceDataset(
                Path(config.data.input_file),
                feature_extractor=feature_extractor,
                config=config,
                precomputed_features={
                    'all_bigrams': all_bigrams,
                    'all_bigram_features': all_bigram_features,
                    'feature_names': feature_names
                }
            )
            
            # Load saved feature metrics
            metrics_file = Path(config.feature_selection.metrics_file)
            if not metrics_file.exists():
                raise FileNotFoundError(f"Feature metrics file not found: {metrics_file}")
                    
            # Load metrics and check available columns
            metrics_df = pd.read_csv(metrics_file)
            logger.info(f"Available columns in metrics file: {list(metrics_df.columns)}")
            
            available_plots = []
            
            try:
                # 1. PCA Feature Space Plot
                fig_pca = plot_feature_space(
                    model=feature_selection_model,
                    dataset=dataset,
                    title="Feature Space",
                    figure_size=(12, 8),
                    alpha=0.6
                )
                fig_pca.savefig(Path(config.paths.plots_dir) / 'feature_space_pca.png')
                plt.close()
                available_plots.append('feature_space_pca.png')
                
                # 2. Feature Impacts Plot from metrics
                metrics_df = pd.read_csv(metrics_file)
                # Get all features including control features
                sorted_metrics = pd.concat([
                    metrics_df[~metrics_df['feature_name'].isin(control_features)],
                    metrics_df[metrics_df['feature_name'].isin(control_features)]
                ]).sort_values('weight', key=abs, ascending=False)

                fig_impacts = plt.figure(figsize=(12, 6))
                ax = fig_impacts.add_subplot(111)

                # Separate main and control features
                control_features = config.features.control_features
                main_metrics = sorted_metrics[~sorted_metrics['feature_name'].isin(control_features)]
                control_metrics = sorted_metrics[sorted_metrics['feature_name'].isin(control_features)]

                # Plot main features
                y_pos = np.arange(len(main_metrics))
                ax.barh(y_pos,
                        main_metrics['weight'],
                        xerr=main_metrics['weight_std'],
                        alpha=0.6,
                        capsize=5,
                        color=['blue' if s else 'lightgray' for s in main_metrics['selected']],
                        label='Main Features')

                # Plot control features differently
                if len(control_metrics) > 0:
                    control_y_pos = np.arange(len(main_metrics), len(sorted_metrics))
                    ax.barh(control_y_pos,
                            control_metrics['weight'],
                            xerr=control_metrics['weight_std'],
                            alpha=0.4,
                            capsize=5,
                            color='gray',
                            label='Control Features')

                # Customize plot
                all_y_pos = np.arange(len(sorted_metrics))
                ax.set_yticks(all_y_pos)
                ax.set_yticklabels(sorted_metrics['feature_name'])
                ax.set_xlabel('Feature Weight\n(Effects shown after controlling for bigram frequency)')
                ax.set_title('Feature Impact Analysis\n(blue = selected features, gray = control features)')
                ax.grid(True, alpha=0.3)
                ax.axvline(x=0, color='black', linestyle='-', alpha=0.2)
                ax.legend()

                # Similarly update the model weights plot
                feature_weights = feature_selection_model.get_feature_weights(include_control=True)
                if feature_weights:
                    fig_weights = plt.figure(figsize=(12, 6))
                    ax = fig_weights.add_subplot(111)
                    
                    # Separate main and control features
                    main_features = {k: v for k, v in feature_weights.items() 
                                    if k not in control_features}
                    control_features_weights = {k: v for k, v in feature_weights.items() 
                                            if k in control_features}
                    
                    # Sort and plot main features
                    sorted_main = sorted(main_features.items(), key=lambda x: abs(x[1][0]), reverse=True)
                    main_y_pos = np.arange(len(sorted_main))
                    
                    features = [f for f, _ in sorted_main]
                    means = [w[0] for _, w in sorted_main]
                    stds = [w[1] for _, w in sorted_main]
                    
                    ax.barh(main_y_pos, means, xerr=stds,
                            alpha=0.6, capsize=5,
                            color=['blue' if m > 0 else 'red' for m in means],
                            label='Main Features')
                    
                    # Plot control features
                    if control_features_weights:
                        sorted_control = sorted(control_features_weights.items(), 
                                            key=lambda x: abs(x[1][0]), reverse=True)
                        control_y_pos = np.arange(len(main_y_pos), 
                                                len(main_y_pos) + len(sorted_control))
                        
                        control_features = [f for f, _ in sorted_control]
                        control_means = [w[0] for _, w in sorted_control]
                        control_stds = [w[1] for _, w in sorted_control]
                        
                        ax.barh(control_y_pos, control_means, xerr=control_stds,
                                alpha=0.4, capsize=5, color='gray',
                                label='Control Features')
                        
                        features.extend(control_features)
                        
                    # Customize plot
                    ax.set_yticks(np.arange(len(features)))
                    ax.set_yticklabels(features)
                    ax.set_xlabel('Feature Weight\n(Effects shown after controlling for bigram frequency)')
                    ax.set_title('Feature Weights from Model')
                    ax.grid(True, alpha=0.3)
                    ax.axvline(x=0, color='black', linestyle='-', alpha=0.2)
                    ax.legend()
                
                logger.info(f"Generated the following plots: {', '.join(available_plots)}")
                
            except Exception as e:
                logger.error(f"Error generating visualizations: {str(e)}")
                raise
                        
        #---------------------------------
        # Recommend bigram pairs
        #---------------------------------
        elif args.mode == 'recommend_bigram_pairs':
            logger.info("Starting recommendation of bigram pairs...")
            # Load feature selection trained model
            logger.info("Loading feature selection trained model...")
            selection_model_save_path = Path(config.feature_selection.model_file)
            feature_selection_model = PreferenceModel.load(selection_model_save_path)
            
            # Initialize recommender with include_control=True
            logger.info("Generating bigram pair recommendations...")
            recommender = BigramRecommender(dataset, feature_selection_model, config)
            logger.debug(f"Using features (including control): {feature_selection_model.get_feature_weights(include_control=True).keys()}")
            recommended_pairs = recommender.get_recommended_pairs()
            
            # Visualize recommendations
            logger.info("Visualizing recommendations...")
            recommender.visualize_recommendations(recommended_pairs)
            
            # Save recommendations
            recommendations_file = Path(config.recommendations.recommendations_file)
            pd.DataFrame(recommended_pairs, columns=['bigram1', 'bigram2']).to_csv(
                         recommendations_file, index=False)
            logger.info(f"Saved recommendations to {recommendations_file}")
            
            # Print recommendations
            logger.info("\nRecommended bigram pairs:")
            for b1, b2 in recommended_pairs:
                logger.info(f"{b1} - {b2}")

        #---------------------------------
        # Train model
        #---------------------------------
        elif args.mode == 'train_model':
            logger.info("Starting model training...")
            # Load train/test split
            train_data, test_data = load_or_create_split(dataset, config)
            
            # Load selected features including control features
            feature_metrics_file = Path(config.feature_selection.metrics_file)
            if not feature_metrics_file.exists():
                raise FileNotFoundError("Feature metrics file not found. Run feature selection first.")      
            feature_metrics_df = pd.read_csv(feature_metrics_file)
            selected_features = (feature_metrics_df[feature_metrics_df['selected'] == 1]['feature_name'].tolist() + 
                                list(config.features.control_features))  # Add control features
            if not selected_features:
                raise ValueError("No features were selected in feature selection phase")
            
            # Train prediction model
            logger.info(f"Training model on training data using {len(selected_features)} selected features...")
            model = PreferenceModel(config=config)
            model.fit(train_data, features=selected_features)

            # Save the trained model
            model_save_path = Path(config.model.model_file)
            model.save(model_save_path)  # Save the model we just trained

            # Evaluate on test data (model.evaluate will use all features including control)
            logger.info("Evaluating model on test data...")
            test_metrics = model.evaluate(test_data)
            
            logger.info("\nTest data metrics:")
            for metric, value in test_metrics.items():
                logger.info(f"{metric}: {value:.3f}")

        #---------------------------------
        # Predict bigram scores
        #---------------------------------
        elif args.mode == 'predict_bigram_scores':
            logger.info("Starting bigram score prediction...")

            # Load selected features
            feature_metrics_file = Path(config.feature_selection.metrics_file)
            if not feature_metrics_file.exists():
                raise FileNotFoundError("Feature metrics file not found. Run feature selection first.")      
            feature_metrics_df = pd.read_csv(feature_metrics_file)
            # Change to handle control features
            selected_features = (feature_metrics_df[feature_metrics_df['selected'] == 1]['feature_name'].tolist() + 
                                list(config.features.control_features))  # Add control features
            if not selected_features:
                raise ValueError("No features were selected in feature selection phase")

            # Load trained model
            logger.info("Loading trained model...")
            model_save_path = Path(config.model.model_file)
            trained_model = PreferenceModel.load(model_save_path)

            # Generate all possible bigrams
            layout_chars = config.data.layout['chars']
            all_bigrams = []
            for char1 in layout_chars:
                for char2 in layout_chars:
                    all_bigrams.append(char1 + char2)

            # Calculate comfort scores for all bigrams
            results = []
            for bigram in all_bigrams:
                comfort_mean, comfort_std = trained_model.get_bigram_comfort_scores(bigram)
                results.append({
                    'bigram': bigram,
                    'comfort_score': comfort_mean,
                    'uncertainty': comfort_std,
                    'first_char': bigram[0],
                    'second_char': bigram[1]
                })

            # Save results
            bigram_scores_file = Path(config.model.predictions_file)
            pd.DataFrame(results).to_csv(bigram_scores_file, index=False)
            logger.info(f"Saved comfort scores for {len(all_bigrams)} bigrams to {bigram_scores_file}")

            # Generate summary statistics and visualizations
            df = pd.DataFrame(results)
            logger.info("\nComfort Score Summary:")
            logger.info(f"Mean comfort score: {df['comfort_score'].mean():.3f}")
            logger.info(f"Score range: {df['comfort_score'].min():.3f} to {df['comfort_score'].max():.3f}")
            logger.info(f"Mean uncertainty: {df['uncertainty'].mean():.3f}")

        logger.info("Pipeline completed successfully")
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main()
