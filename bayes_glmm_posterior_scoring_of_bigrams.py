import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.model_selection import GroupKFold
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from scipy.optimize import differential_evolution, minimize
from scipy.spatial import ConvexHull
from scipy.spatial.distance import cdist
from itertools import product
import networkx as nx
import pymc as pm
import arviz as az
import ast
import json

from bayes_glmm_features import *

def extract_features_samekey(char, finger_map):
    features = {
        'finger1': int(finger_map[char] == 1),
        'finger2': int(finger_map[char] == 2),
        'finger3': int(finger_map[char] == 3),
        'finger4': int(finger_map[char] == 4)
    }
    feature_names = list(features.keys())
    
    return features, feature_names

def extract_features(char1, char2, column_map, row_map, finger_map):
    features = {
        'ncols': columns_apart(char1, char2, column_map),
        'nrows': rows_apart(char1, char2, column_map, row_map),
        'out': outward_roll(char1, char2, column_map, finger_map),
        'skip': skip_home(char1, char2, column_map, row_map),
        '1or4_top_above': finger1or4_top_above(char1, char2, column_map, row_map),
        '2or3_bot_below': finger2or3_bottom_below(char1, char2, column_map, row_map),
        '1above': finger1_above(char1, char2, column_map, row_map, finger_map),
        '4above': finger4_above(char1, char2, column_map, row_map, finger_map),
        '2below': finger2_below(char1, char2, column_map, row_map, finger_map),
        '3below': finger3_below(char1, char2, column_map, row_map, finger_map),
        'center': middle_column(char1, char2, column_map),
        'same': same_finger(char1, char2, column_map, finger_map),
        'adj_skip': adj_finger_skip(char1, char2, column_map, row_map, finger_map)
    }
    feature_names = list(features.keys())
    
    return features, feature_names

#=================================================================#
# Features for all bigrams and their differences in feature space #
#=================================================================#
def precompute_all_bigram_features(layout_chars, column_map, row_map, finger_map):
    """
    Precompute features for all possible bigrams based on the given layout characters.
    
    Parameters:
    - layout_chars: List of all possible characters in the keyboard layout.
    
    Returns:
    - all_bigrams: All possible bigrams.
    - all_bigram_features: DataFrame mapping all bigrams to their feature vectors (with named columns).
    - feature_names: List of feature names.   
    - samekey_bigrams: All possible same-key bigrams.
    - samekey_bigram_features: DataFrame mapping all same-key bigrams to their feature vectors (with named columns).
    - samekey_feature_names: List of same-key feature names.   
    """
    # Generate all possible bigrams (permutations of 2 characters, with repeats)
    #all_bigrams = list(product(layout_chars, repeat=2))
    # Generate all possible 2-key bigrams (permutations of 2 unique characters)
    all_bigrams = [(x, y) for x, y in product(layout_chars, repeat=2) if x != y]
    # Generate all possible same-key bigrams
    samekey_bigrams = [(char, char) for char in layout_chars]

    # Extract features for each bigram (non-repeating, and same-key bigrams)
    feature_vectors = []
    feature_names = None
    samekey_feature_vectors = []
    samekey_feature_names = None

    # Extract features for the bigram, and convert features to a list
    for char1, char2 in all_bigrams:
        features, feature_names = extract_features(char1, char2, column_map, row_map, finger_map)
        feature_vectors.append(list(features.values()))

    for char1, char2 in samekey_bigrams:
        samekey_features, samekey_feature_names = extract_features_samekey(char1, finger_map)
        samekey_feature_vectors.append(list(samekey_features.values()))

    # Convert to DataFrame with feature names
    features_df = pd.DataFrame(feature_vectors, columns=feature_names, index=all_bigrams)
    features_df.index = pd.MultiIndex.from_tuples(features_df.index)
    samekey_features_df = pd.DataFrame(samekey_feature_vectors, columns=samekey_feature_names, index=samekey_bigrams)
    samekey_features_df.index = pd.MultiIndex.from_tuples(samekey_features_df.index)

    print(f"Extracted {len(features_df.columns)} features from each of {len(all_bigrams)} possible 2-key bigrams.")
    print(f"Extracted {len(samekey_features_df.columns)} features from each of {len(samekey_bigrams)} possible same-key bigrams.")

    return all_bigrams, features_df, feature_names, \
           samekey_bigrams, samekey_features_df, samekey_feature_names

def precompute_bigram_feature_differences(bigram_features):
    """
    Precompute and store feature differences between bigram pairs.
    
    Parameters:
    - bigram_features: Dictionary of precomputed features for each bigram.
    
    Returns:
    - bigram_feature_differences: A dictionary where each key is a tuple of bigrams (bigram1, bigram2),
                                  and the value is the precomputed feature differences.
    """
    bigram_feature_differences = {}
    bigrams_list = list(bigram_features.index)

    # Loop over all pairs of bigrams
    for i, bigram1 in enumerate(bigrams_list):
        for j, bigram2 in enumerate(bigrams_list):
            if i <= j:  # Only compute differences for unique pairs (skip symmetric pairs)
                # Calculate the feature differences
                abs_feature_diff = np.abs(bigram_features.loc[bigram1].values - bigram_features.loc[bigram2].values)
                bigram_feature_differences[(bigram1, bigram2)] = abs_feature_diff
                bigram_feature_differences[(bigram2, bigram1)] = abs_feature_diff  # Symmetric pair

    print(f"Calculated all {len(bigram_feature_differences)} bigram-bigram feature differences.")
      
    return bigram_feature_differences

def plot_bigram_graph(bigram_pairs):
    """
    Plot a graph of all bigrams as nodes with edges connecting bigrams that are in pairs.
    
    Parameters:
    - bigram_pairs: List of bigram pairs (e.g., [(('a', 'r'), ('s', 't')), ...])
    """
    # Create a graph
    G = nx.Graph()

    # Create a mapping of tuple bigrams to string representations
    for bigram1, bigram2 in bigram_pairs:
        bigram1_str = ''.join(bigram1)  # Convert tuple ('a', 'r') to string "ar"
        bigram2_str = ''.join(bigram2)  # Convert tuple ('s', 't') to string "st"
        
        # Add edges between bigram string representations
        G.add_edge(bigram1_str, bigram2_str)

    # Get all connected components (subgraphs)
    components = [G.subgraph(c).copy() for c in nx.connected_components(G)]
    
    # Initialize figure
    plt.figure(figsize=(14, 14))

    # Layout positioning of all components
    pos = {}
    grid_size = int(np.ceil(np.sqrt(len(components))))  # Arrange components in a grid
    spacing = 5.0  # Adjust this value for more space between clusters

    # Iterate over each component and apply a layout
    for i, component in enumerate(components):
        # Apply spring layout to the current component
        component_pos = nx.spring_layout(component, k=1.0, seed=i)  # Use different seed for each component
        
        # Determine the grid position for this component
        x_offset = (i % grid_size) * spacing  # X-axis grid position
        y_offset = (i // grid_size) * spacing  # Y-axis grid position

        # Shift the component positions to avoid overlap
        for node in component_pos:
            component_pos[node][0] += x_offset
            component_pos[node][1] += y_offset

        # Update the global position dictionary
        pos.update(component_pos)
    
    # Draw the entire graph with the adjusted positions
    nx.draw(G, pos, with_labels=True, node_color='lightblue', font_weight='bold', 
            node_size=500, font_size=14, edge_color='gray', linewidths=1.5, width=2.0)

    # Display the graph
    plt.title("Bigram Connectivity Graph", fontsize=20)
    plt.show()

#===========================================================================================#
# Feature space, feature matrix multicollinearity, priors sensitivity, and cross-validation #
#===========================================================================================#
def check_multicollinearity(feature_matrix):
    """
    Check for multicollinearity.
    Multicollinearity occurs when two or more predictor variables are highly correlated, 
    which can inflate standard errors and lead to unreliable p-values. 
    You can check for multicollinearity using the Variance Inflation Factor (VIF), 
    a common metric that quantifies how much the variance of a regression coefficient 
    is inflated due to collinearity with other predictors.

    VIF ≈ 1: No correlation between a feature and the other features.
        •	1 < VIF < 5: Moderate correlation, but acceptable.
        •	VIF > 5: High correlation; consider removing or transforming the feature.
        •	VIF > 10: Serious multicollinearity issue.

    Parameters:
    - feature_matrix: DataFrame containing the features
    """
    print("\n ---- Check feature matrix multicollinearity ---- \n")
    
    debug = True
    if debug:

        # Compute the correlation matrix
        print("Correlation matrix:")
        corr_matrix = feature_matrix.corr().abs()
        print(corr_matrix)

        # Identify features with high correlation (e.g., > 0.95)
        high_corr_features = np.where(corr_matrix > 0.95)

        # Display pairs of highly correlated features
        for i in range(len(high_corr_features[0])):
            if high_corr_features[0][i] != high_corr_features[1][i]:  # Avoid self-correlation
                print(f"High correlation: {feature_matrix.columns[high_corr_features[0][i]]} "
                    f"and {feature_matrix.columns[high_corr_features[1][i]]}")
        print("")

    print("Variance Inflation Factor\n1: perfect correlation, 1 < VIF < 5: moderate correlation")

    X = sm.add_constant(feature_matrix)

    vif_data = pd.DataFrame()
    vif_data["Feature"] = X.columns

    # Handle infinite VIF gracefully
    def safe_vif(i):
        try:
            return variance_inflation_factor(X.values, i)
        except (ZeroDivisionError, np.linalg.LinAlgError):
            return np.inf

    vif_data["VIF"] = [safe_vif(i) for i in range(X.shape[1])]

    # Display the VIF for each feature
    print(vif_data)

def perform_sensitivity_analysis(feature_matrix, target_vector, participants, selected_feature_names=None,
                                 typing_times=None, prior_means=[0, 50, 100], prior_stds=[1, 10, 100]):
    """
    Perform sensitivity analysis by varying the prior on typing_time.
    
    Args:
    feature_matrix, target_vector, participants: As in the original model
    selected_feature_names: names of features to include as priors (if None, use all)
    typing_times: Typing time data
    prior_means, prior_stds: Lists of means and standard deviations to try for the typing_time prior
    
    Returns:
    A dictionary of results for each prior configuration
    """
    print("\n ---- Analyze sensitivity of the GLMM results on each prior ---- \n")
    
    results = {}
    
    for mean in prior_means:
        for std in prior_stds:
            print(f"Running model with typing_time prior: N({mean}, {std})")
            
            trace, model, priors = train_bayesian_glmm(
                feature_matrix=feature_matrix,
                target_vector=target_vector,
                participants=participants,
                selected_feature_names=selected_feature_names,
                typing_times=typing_times,
                inference_method="mcmc",
                num_samples=1000,
                chains=4
            )

            # Generate summary
            summary = az.summary(trace)
            results[f"prior_N({mean},{std})"] = summary

            # Print the first X rows
            print_nrows = np.shape(feature_matrix)[1] + 5
            print(print_nrows)
            print(summary.head(print_nrows))
            print("\n" + "="*50 + "\n")
    
    return results

def bayesian_pairwise_scoring(y_true, y_pred):
    """
    Calculate a score for Bayesian pairwise comparison predictions.
    
    Parameters:
    - y_true: True pairwise preferences (positive for first bigram preferred, negative for second)
    - y_pred: Predicted differences in comfort scores
    
    Returns:
    - score: A score between 0 and 1, where 1 is perfect prediction
    """
    # Convert inputs to numpy arrays
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    
    # Convert predictions and true values to binary outcomes
    y_true_binary = (y_true > 0).astype(int)
    y_pred_binary = (y_pred > 0).astype(int)
    
    # Calculate accuracy
    accuracy = np.mean(y_true_binary == y_pred_binary)
    
    # Calculate log-likelihood
    epsilon = 1e-15  # Small value to avoid log(0)
    probs = 1 / (1 + np.exp(-np.abs(y_pred)))
    log_likelihood = np.mean(y_true_binary * np.log(probs + epsilon) + 
                             (1 - y_true_binary) * np.log(1 - probs + epsilon))
    
    # Combine accuracy and log-likelihood
    score = (accuracy + (log_likelihood + 1) / 2) / 2
    
    return score

def bayesian_cv_pipeline(bayesian_glmm_func, bayesian_scoring_func, feature_matrix, 
                         target_vector, participants, bigram_pairs, n_splits=5):
    """
    Perform cross-validation for Bayesian GLMM and posterior scoring.
    
    Parameters:
    - bayesian_glmm_func: Function to fit the Bayesian GLMM.
    - bayesian_scoring_func: Function to calculate Bayesian comfort scores.
    - feature_matrix: Feature matrix (X).
    - target_vector: Target vector (y).
    - participants: Grouping variable for random effects or None if already preprocessed.
    - bigram_pairs: List of bigram pairs used in the comparisons.
    - n_splits: Number of cross-validation splits.
    
    Returns:
    - cv_scores: Scores from cross-validation for the full pipeline.
    """
    print("\n ---- Run Bayesian cross-validation ---- \n")

    cv = GroupKFold(n_splits=n_splits)
    
    cv_scores = []
    
    # Check if participants need preprocessing
    if participants is not None and not isinstance(participants[0], (int, np.integer)):
        #print("Preprocessing participants...")
        unique_participants = np.unique(participants)
        participant_map = {p: i for i, p in enumerate(unique_participants)}
        participants_index = np.array([participant_map[p] for p in participants])
    else:
        #print("Using provided participant indices...")
        participants_index = participants

    if participants_index is None:
        print("Warning: participants_index is None. Using range(len(target_vector)) as default.")
        participants_index = np.arange(len(target_vector))

    for train_idx, test_idx in cv.split(feature_matrix, target_vector, groups=participants_index):
        X_train, X_test = feature_matrix.iloc[train_idx], feature_matrix.iloc[test_idx]
        y_train, y_test = target_vector[train_idx], target_vector[test_idx]
        groups_train = participants_index[train_idx]
        bigram_pairs_train = [bigram_pairs[i] for i in train_idx]
        bigram_pairs_test = [bigram_pairs[i] for i in test_idx]
        
        #print(f"Train set size: {len(X_train)}, Test set size: {len(X_test)}")
        
        # Step 1: Fit the Bayesian GLMM on the training set
        glmm_result = bayesian_glmm_func(X_train, y_train, groups_train)
        
        # Unpack the result, assuming it returns (trace, model, all_priors)
        if isinstance(glmm_result, tuple) and len(glmm_result) >= 1:
            trace = glmm_result[0]
        else:
            trace = glmm_result  # In case it only returns the trace
        
        # Step 2: Calculate Bayesian comfort scores for test set
        comfort_scores_test = bayesian_scoring_func(trace, bigram_pairs_test, X_test)
        
        # Step 3: Prepare test scores for evaluation
        test_scores = []
        for (bigram1, bigram2) in bigram_pairs_test:
            score_diff = comfort_scores_test.get(bigram1, 0) - comfort_scores_test.get(bigram2, 0)
            test_scores.append(score_diff)
        
        # Convert test_scores to a numpy array
        test_scores = np.array(test_scores)

        # Step 4: Evaluate performance
        score = bayesian_pairwise_scoring(y_test, test_scores)
        cv_scores.append(score)
        
        print(f"Cross-validation fold score: {score}")

    print(f"Mean CV Score: {np.mean(cv_scores)}")
    return cv_scores

def analyze_feature_space(feature_matrix):
    # Standardize the features
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(feature_matrix)
    
    # Perform PCA to reduce to 2D for visualization
    from sklearn.decomposition import PCA
    pca = PCA(n_components=2)
    pca_result = pca.fit_transform(scaled_features)
    
    # Plot the 2D projection
    plt.figure(figsize=(10, 8))
    plt.scatter(pca_result[:, 0], pca_result[:, 1], alpha=0.6)
    plt.title('2D PCA projection of feature space')
    plt.xlabel('First Principal Component')
    plt.ylabel('Second Principal Component')
    plt.show()
    
    # Calculate the convex hull of the data points
    hull = ConvexHull(pca_result)
    hull_area = hull.area
    
    # Calculate the density of points
    point_density = len(pca_result) / hull_area
    
    print(f"Convex Hull Area: {hull_area}")
    print(f"Point Density: {point_density}")
    
    return pca, scaler, hull

def identify_underrepresented_areas(pca_result, num_grid=20):
    x_min, x_max = pca_result[:, 0].min() - 1, pca_result[:, 0].max() + 1
    y_min, y_max = pca_result[:, 1].min() - 1, pca_result[:, 1].max() + 1
    
    xx, yy = np.meshgrid(np.linspace(x_min, x_max, num_grid),
                         np.linspace(y_min, y_max, num_grid))
    
    grid_points = np.c_[xx.ravel(), yy.ravel()]
    
    # Calculate distances to nearest data point for each grid point
    from scipy.spatial.distance import cdist
    distances = cdist(grid_points, pca_result).min(axis=1)
    
    # Reshape distances to match the grid
    distances = distances.reshape(xx.shape)
    
    # Plot the distance heatmap
    plt.figure(figsize=(10, 8))
    plt.imshow(distances, extent=[x_min, x_max, y_min, y_max], origin='lower', cmap='viridis')
    plt.colorbar(label='Distance to nearest data point')
    plt.scatter(pca_result[:, 0], pca_result[:, 1], c='red', s=20, alpha=0.5)
    plt.title('Underrepresented Areas in Feature Space')
    plt.xlabel('First Principal Component')
    plt.ylabel('Second Principal Component')
    plt.show()
    
    return grid_points, distances

def generate_new_features(grid_points, distances, pca, scaler, num_new=100):
    # Sort grid points by distance (descending)
    sorted_indices = np.argsort(distances.ravel())[::-1]
    
    # Select the grid points with the largest distances
    selected_points = grid_points[sorted_indices[:num_new]]
    
    # Transform these points back to the original feature space
    original_space_points = scaler.inverse_transform(pca.inverse_transform(selected_points))
    
    # Round the feature values to the nearest valid value (e.g., 0 or 1 for binary features)
    rounded_points = np.round(original_space_points)
    
    return np.abs(rounded_points)

def features_to_bigram_pairs(new_feature_differences, all_feature_differences):
    """
    Convert new feature differences to bigram pairs by finding the closest matching known bigram pair.
    
    Parameters:
    - new_feature_differences: numpy array of new feature differences to convert
    - all_feature_differences: numpy array of all known feature differences corresponding to all_bigram_pairs
    
    Returns:
    - features_to_bigram_pairs: List of bigram pairs corresponding to the new feature differences
    """
    all_pairs = list(all_feature_differences.keys())  # Extract all pairs (keys)
    all_values = np.array(list(all_feature_differences.values()))  # Extract all values

    # Compute distances between new feature differences and all known feature differences
    distances = cdist(new_feature_differences, all_values)
    
    # Find the index of the closest match for each new feature difference
    closest_indices = np.argmin(distances, axis=1)
    
    # Map these indices to the corresponding known bigram pairs
    suggested_bigram_pairs = list(set([all_pairs[i] for i in closest_indices]))
    
    return suggested_bigram_pairs

def generate_extended_recommendations(new_feature_differences, all_feature_differences, suggested_bigram_pairs, n_total=30):
    """
    Generate bigram pair recommendations, including initial suggestions and additional ones.
    
    Parameters:
    - new_feature_differences: numpy array of new feature differences
    - all_feature_differences: dictionary of all known feature differences
    - suggested_bigram_pairs: output from features_to_bigram_pairs
    - n_total: total number of recommendations to generate
    
    Returns:
    - List of suggested bigram pairs
    """
    all_pairs = list(all_feature_differences.keys())
    all_values = np.array(list(all_feature_differences.values()))

    # Ensure new_feature_differences is a numpy array
    new_feature_differences = np.array(new_feature_differences)

    # Step 1: Generate more diverse points in the feature space
    mean = np.mean(all_values, axis=0)
    cov = np.cov(all_values, rowvar=False)
    additional_points = np.random.multivariate_normal(mean, cov, size=n_total*2)
    
    # Step 2: Combine with the original new points and cluster
    combined_points = np.vstack([new_feature_differences, additional_points])
    kmeans = KMeans(n_clusters=n_total, n_init=10)
    kmeans.fit(combined_points)
    
    # Step 3: Select diverse points (cluster centers)
    diverse_points = kmeans.cluster_centers_
    
    # Step 4: Find the closest known bigram pairs for these diverse points
    distances = cdist(diverse_points, all_values)
    closest_indices = np.argmin(distances, axis=1)
    
    # Step 5: Map these indices to the corresponding known bigram pairs
    suggested_bigram_pairs = [all_pairs[i] for i in closest_indices if all_pairs[i] not in suggested_bigram_pairs]
    
    # Step 6: Remove duplicates while preserving order
    seen = set()
    unique_suggestions = []
    for pair in suggested_bigram_pairs:
        pair_tuple = tuple(sorted([tuple(pair[0]), tuple(pair[1])]))  # Sort to ensure consistent ordering
        if pair_tuple not in seen:
            seen.add(pair_tuple)
            unique_suggestions.append(pair)
    
    return unique_suggestions[:n_total]
  
#====================================================#
# Bayesian GLMM training, Bayesian posterior scoring #
#====================================================#
def train_bayesian_glmm(feature_matrix, target_vector, participants=None, 
                        selected_feature_names=None,
                        typing_times=None, inference_method="mcmc", 
                        num_samples=1000, chains=4):
    """
    Train a Bayesian GLMM with hierarchical modeling using custom and feature-based priors.
    """
    print("\n ---- Train Bayesian GLMM ---- \n")

    # Ensure that selected features are provided, or default to all features
    if selected_feature_names is None:
        selected_feature_names = feature_matrix.columns.tolist()

    # Handle the case where participants is None
    if participants is None:
        print("Warning: participants is None. Using range(len(target_vector)) as default.")
        participants = np.arange(len(target_vector))

    # Get the unique participants in this subset of data
    unique_participants = np.unique(participants)
    num_participants = len(unique_participants)
    
    # Create a mapping from original indices to contiguous indices
    participant_map = {p: i for i, p in enumerate(unique_participants)}
    participants_contiguous = np.array([participant_map[p] for p in participants])

    selected_features_matrix = feature_matrix[selected_feature_names]

    # Define the model context block to avoid the context stack error
    with pm.Model() as model:
        # Create feature-based priors dynamically
        feature_priors = {}
        for feature_name in selected_feature_names:
            feature_priors[feature_name] = pm.Normal(
                feature_name, 
                mu=np.mean(selected_features_matrix[feature_name]), 
                sigma=np.std(selected_features_matrix[feature_name])
            )

        # Define custom priors
        if typing_times is not None:
            typing_time_prior = pm.Normal('typing_time', 
                                          mu=np.mean(typing_times), 
                                          sigma=np.std(typing_times))

        # Combine all priors (feature-based + custom)
        all_priors = list(feature_priors.values())
        if typing_times is not None:
            all_priors.append(typing_time_prior)

        # Random effects: Participant-specific intercepts
        participant_intercept = pm.Normal('participant_intercept', mu=0, sigma=1, 
                                          shape=num_participants)

        # Define the linear predictor (fixed + random effects)
        fixed_effects = pm.math.dot(selected_features_matrix, pm.math.stack([feature_priors[name] for name in selected_feature_names]))
        if typing_times is not None:
            fixed_effects += typing_time_prior

        mu = (fixed_effects + participant_intercept[participants_contiguous]).reshape(target_vector.shape)

        # Likelihood: Observed target vector
        sigma = pm.HalfNormal('sigma', sigma=10)
        y_obs = pm.Normal('y_obs', mu=mu, sigma=sigma, observed=target_vector)

        # Choose the inference method
        if inference_method == "mcmc":
            trace = pm.sample(num_samples, chains=chains, return_inferencedata=True)
        elif inference_method == "variational":
            approx = pm.fit(method="advi", n=num_samples)
            trace = approx.sample(num_samples)
        else:
            raise ValueError("Inference method must be 'mcmc' or 'variational'.")

    return trace, model, all_priors

def calculate_bayesian_comfort_scores(trace, bigram_pairs, feature_matrix, params=None, 
                                      output_filename="bigram_typing_comfort_scores.csv"):
    """
    Generate latent comfort scores using the full posterior distributions from a Bayesian GLMM.
    This version handles both feature-based and manual priors.
    
    Parameters:
    - trace: The InferenceData object from the Bayesian GLMM (contains posterior samples).
    - bigram_pairs: List of bigram pairs used in the comparisons.
    - feature_matrix: The feature matrix used in the GLMM, indexed by bigram pairs.
    - params: List of parameter names to use from the trace. If None, all suitable parameters will be used.
   
    Returns:
    - bigram_comfort_scores: Dictionary mapping each bigram to its latent comfort score.
    """
    # Extract variable names from the trace
    all_vars = list(trace.posterior.data_vars)
    
    # If params is not provided, use all parameters except 'participant_intercept' and 'sigma'
    if params is None:
        params = [var for var in all_vars if var not in ['participant_intercept', 'sigma']]
    
    print(f"All parameters: {params}")
    
    # Separate parameters into those in the feature matrix and those that aren't
    feature_params = [param for param in params if param in feature_matrix.columns]
    manual_params = [param for param in params if param not in feature_matrix.columns]
    
    print(f"Feature-based parameters: {feature_params}")
    print(f"Manual parameters: {manual_params}")
    
    # Extract posterior samples for all parameters
    posterior_samples = {param: az.extract(trace, var_names=param).values for param in params}
    
    # Convert feature matrix to numpy array and extract relevant columns
    feature_array = feature_matrix[feature_params].values
    
    # Create a dictionary to map bigram pairs to their index in the feature array
    bigram_to_index = {tuple(map(tuple, pair)): i for i, pair in enumerate(feature_matrix.index)}
    
    # Calculate comfort scores for each bigram pair
    bigram_pair_scores = {}
    mismatches = []
    for bigram_pair in bigram_pairs:
        bigram_pair_tuple = tuple(map(tuple, bigram_pair))
        if bigram_pair_tuple in bigram_to_index:
            row_index = bigram_to_index[bigram_pair_tuple]
            bigram_features = feature_array[row_index]
            
            # Calculate score using feature-based parameters
            scores = np.zeros(len(next(iter(posterior_samples.values()))))
            for i, param in enumerate(feature_params):
                scores += posterior_samples[param] * bigram_features[i]
            
            # Add contribution from manual parameters
            for param in manual_params:
                scores += posterior_samples[param]
            
            # Use the mean score across all posterior samples
            bigram_pair_scores[bigram_pair] = np.mean(scores)
        else:
            mismatches.append(bigram_pair)
    
    if not bigram_pair_scores:
        raise ValueError("No valid bigram pair scores could be calculated.")
    
    # Normalize scores to 0-1 range
    min_score = min(bigram_pair_scores.values())
    max_score = max(bigram_pair_scores.values())
    normalized_scores = {bigram_pair: (score - min_score) / (max_score - min_score) 
                         for bigram_pair, score in bigram_pair_scores.items()}
    
    # Calculate comfort scores for individual bigrams
    bigram_comfort_scores = {}
    for bigram_pair, score in normalized_scores.items():
        bigram1, bigram2 = bigram_pair
        bigram1 = ''.join(bigram1)
        bigram2 = ''.join(bigram2)
        
        if bigram1 not in bigram_comfort_scores:
            bigram_comfort_scores[bigram1] = []
        if bigram2 not in bigram_comfort_scores:
            bigram_comfort_scores[bigram2] = []
        bigram_comfort_scores[bigram1].append(score)
        bigram_comfort_scores[bigram2].append(1 - score)  # Invert score for the second bigram
    
    # Average the scores for each bigram
    bigram_comfort_scores = {bigram: np.mean(scores) for bigram, scores in bigram_comfort_scores.items()}
    
    # Convert dictionary to DataFrame and store as csv file
    df = pd.DataFrame.from_dict(bigram_comfort_scores, orient='index', columns=['bigram_comfort_score'])
    df.index.name = 'bigram'
    df.to_csv(f"{output_filename}")
    print(f"Bigram typing comfort scores saved to {output_filename}")

    return bigram_comfort_scores

def save_glmm_results(trace, model, base_filename):
    # Save trace
    az.to_netcdf(trace, filename=f"{base_filename}_trace.nc")
    
    # Save point estimates
    point_estimates = az.summary(trace)
    point_estimates.to_csv(f"{base_filename}_point_estimates.csv")
    
    # Save model configuration
    model_config = {
        'input_vars': [var.name for var in model.named_vars.values() if hasattr(var, 'distribution')],
        'observed_vars': [var.name for var in model.observed_RVs],
        'free_vars': [var.name for var in model.free_RVs],
    }
    
    # Save prior information
    prior_info = {}
    for var in model.named_vars.values():
        if hasattr(var, 'distribution'):
            prior_info[var.name] = {
                'distribution': var.distribution.__class__.__name__,
                'parameters': {k: str(v) for k, v in var.distribution.parameters.items() if k != 'name'}
            }
    
    # Combine model config and prior info
    model_info = {
        'config': model_config,
        'priors': prior_info
    }
    
    with open(f"{base_filename}_model_info.json", "w") as f:
        json.dump(model_info, f, indent=2)

def load_glmm_results(base_filename):
    # Load trace
    trace = az.from_netcdf(f"{base_filename}_trace.nc")
    
    # Load point estimates
    point_estimates = pd.read_csv(f"{base_filename}_point_estimates.csv", index_col=0)
    
    # Load model info (including priors)
    with open(f"{base_filename}_model_info.json", "r") as f:
        model_info = json.load(f)
    
    return trace, point_estimates, model_info

def calculate_all_bigram_comfort_scores(trace, all_bigram_features, params=None, mirror_scores=True):
    # Extract variable names from the trace
    all_vars = list(trace.posterior.data_vars)
    
    # If params is not provided, use all parameters except 'participant_intercept' and 'sigma'
    if params is None:
        params = [var for var in all_vars if var not in ['participant_intercept', 'sigma']]
    
    # Extract posterior samples for all parameters
    posterior_samples = {param: az.extract(trace, var_names=param).values for param in params}
    
    # Calculate comfort scores for each bigram
    all_bigram_scores = {}
    for bigram, features in all_bigram_features.iterrows():
        # Calculate score using feature-based parameters
        scores = np.zeros(len(next(iter(posterior_samples.values()))))
        for param in params:
            if param in features.index:
                scores += posterior_samples[param] * features[param]
        
        # Use the mean score across all posterior samples
        all_bigram_scores[bigram] = np.mean(scores)
    
    # Normalize scores to 0-1 range
    min_score = min(all_bigram_scores.values())
    max_score = max(all_bigram_scores.values())
    normalized_scores = {bigram: (score - min_score) / (max_score - min_score) 
                         for bigram, score in all_bigram_scores.items()}
    
    # Create a mapping for the right-hand keys
    if mirror_scores:
        left_keys = "qwertasdfgzxcvb"
        right_keys = "poiuy;lkjh/.,mn"
        key_mapping = dict(zip(left_keys, right_keys))
        
        # Add scores for right-hand bigrams
        right_scores = {}
        for bigram, score in normalized_scores.items():
            if isinstance(bigram, tuple) and len(bigram) == 2:
                right_bigram = (key_mapping.get(bigram[0], bigram[0]), 
                                key_mapping.get(bigram[1], bigram[1]))
                right_scores[right_bigram] = score
        
        # Combine left and right scores
        all_scores = {**normalized_scores, **right_scores}
    else:
        all_scores = normalized_scores
    
    return all_scores


####################################################################################################

#==============#
# Run the code #
#==============#
if __name__ == "__main__":

    # Run analyses on the feature space, and sensitivity and generalizability of priors
    run_analyze_feature_space = False
    # The following can only run if run_analyze_feature_space = True
    run_sensitivity_analysis = False
    run_cross_validation = False
    # Run the above on comparisons of repeat-key bigrams (only collected data on 4: "aa", "ss", "dd", "ff")
    run_samekey_analysis = False

    # Run Bayesian GLMM and posterior scoring to estimate latent typing comfort for every bigram
    run_glmm = False

    # Score all bigrams based on the output of the GLMM
    score_all_bigrams = True

    # Incomplete
    run_optimize_layout = False

    #===========================================#
    # Run feature analyses or GLMM on LEFT keys #
    #===========================================#
    left_layout_chars = list("qwertasdfgzxcvb")

    if run_analyze_feature_space or run_glmm:

        #=================================================#
        # Load, prepare, and analyze LEFT bigram features #
        #=================================================#
        print("\n ---- Load, prepare, and analyze features ---- \n")

        # Precompute all bigram features and differences between the features of every pair of bigrams
        all_bigrams, all_bigram_features, feature_names, samekey_bigrams, samekey_bigram_features, \
            samekey_feature_names = precompute_all_bigram_features(left_layout_chars, column_map, row_map, finger_map)
        all_feature_differences = precompute_bigram_feature_differences(all_bigram_features)

        # Load the CSV file into a pandas DataFrame
        csv_file_path = "/Users/arno.klein/Downloads/osf/output_all4studies_406participants/tables/filtered_bigram_data.csv"
        #csv_file_path = "/Users/arno.klein/Downloads/osf/output_all4studies_406participants/tables/filtered_consistent_choices.csv"
        #csv_file_path = "/Users/arno.klein/Downloads/osf/output_all4studies_303of406participants_0improbable/tables/filtered_bigram_data.csv"
        #csv_file_path = "/Users/arno.klein/Downloads/osf/output_all4studies_303of406participants_0improbable/tables/filtered_consistent_choices.csv"
        bigram_data = pd.read_csv(csv_file_path)  # print(bigram_data.columns)

        # Prepare bigram data (format, including strings to actual tuples, conversion to numeric codes)
        bigram_pairs = [ast.literal_eval(bigram_pair) for bigram_pair in bigram_data['bigram_pair']]
        bigram_pairs = [((bigram1[0], bigram1[1]), (bigram2[0], bigram2[1])) for bigram1, bigram2 in bigram_pairs]     # Split each bigram in the pair into its individual characters
        slider_values = bigram_data['abs_sliderValue']
        typing_times = bigram_data['chosen_bigram_time']
        # Extract participant IDs as codes and ensure a 1D numpy array of integers
        participants = pd.Categorical(bigram_data['user_id']).codes
        participants = participants.astype(int)  # Already flattened, so no need for .flatten()

        if run_samekey_analysis:
            all_samekey_feature_differences = precompute_bigram_feature_differences(samekey_bigram_features)
            # Filter out bigram pairs where either bigram is not in the precomputed features
            bigram_pairs = [bigram for bigram in bigram_pairs if bigram in all_samekey_feature_differences]
            target_vector = np.array([slider_values.iloc[idx] for idx, bigram in enumerate(bigram_pairs)])
            participants = np.array([participants[idx] for idx, bigram in enumerate(bigram_pairs)])

            # Create a DataFrame for the feature matrix, using precomputed features for the bigram pairs
            feature_matrix_data = [all_samekey_feature_differences[(bigram1, bigram2)] for (bigram1, bigram2) in bigram_pairs] 
            feature_matrix = pd.DataFrame(feature_matrix_data, columns=samekey_feature_names, index=bigram_pairs)
        else:
            # Filter out bigram pairs where either bigram is not in the precomputed differences
            bigram_pairs = [bigram for bigram in bigram_pairs if bigram in all_feature_differences]
            target_vector = np.array([slider_values.iloc[idx] for idx, bigram in enumerate(bigram_pairs)])
            participants = np.array([participants[idx] for idx, bigram in enumerate(bigram_pairs)])

            # Create a DataFrame for the feature matrix, using precomputed feature differences for the bigram pairs
            feature_matrix_data = [all_feature_differences[(bigram1, bigram2)] for (bigram1, bigram2) in bigram_pairs] 
            feature_matrix = pd.DataFrame(feature_matrix_data, columns=feature_names, index=bigram_pairs)

            #-------------------------
            # Add feature interactions
            #-------------------------
            n_feature_interactions = 2
            feature_matrix['same_skip'] = feature_matrix['same'] * feature_matrix['skip']
            feature_matrix['1_center'] = feature_matrix['same'] * feature_matrix['center']

        #=====================================================================================================#
        # Check feature space, feature matrix multicollinearity, priors sensitivity, and run cross-validation #
        #=====================================================================================================#
        if run_analyze_feature_space:

            # Plot a graph of all bigram pairs to make sure they are all connected for Bradley-Terry training
            plot_bigram_pair_graph = False
            if plot_bigram_pair_graph:
                plot_bigram_graph(bigram_pairs)

            pca, scaler, hull = analyze_feature_space(feature_matrix)
            grid_points, distances = identify_underrepresented_areas(pca.transform(scaler.transform(feature_matrix)))
            new_feature_differences = generate_new_features(grid_points, distances, pca, scaler)

            # Timing data should be in the last column (prior appended to all_priors in train_bayesian_glmm)
            if n_feature_interactions > 0:
                new_feature_differences = new_feature_differences[:, :-n_feature_interactions]  # Removes the last n columns
            suggested_bigram_pairs = features_to_bigram_pairs(new_feature_differences, all_feature_differences)

            print("Suggested new bigram pairs to collect data for:")
            for pair in suggested_bigram_pairs:
                print(f"{pair[0][0] + pair[0][1]}, {pair[1][0] + pair[1][1]}")

            n_recommendations = 30
            extended_suggestions = generate_extended_recommendations(new_feature_differences, all_feature_differences, 
                                                                     suggested_bigram_pairs, n_recommendations)

            print("Extended list of suggested bigram pairs to collect data for:")
            for i, pair in enumerate(extended_suggestions):
                print(f"{pair[0][0] + pair[0][1]}, {pair[1][0] + pair[1][1]}")

            # Check multicollinearity: Run VIF on the feature matrix to identify highly correlated features
            check_multicollinearity(feature_matrix)

            # Sensitivity analysis to determine how much each prior influences the results
            if run_sensitivity_analysis:
                sensitivity_results = perform_sensitivity_analysis(feature_matrix, target_vector, participants, 
                                                                selected_feature_names=None,
                                                                typing_times=typing_times, 
                                                                prior_means=[0, 50, 100], 
                                                                prior_stds=[1, 10, 100])
            if run_cross_validation:
                cv_scores = bayesian_cv_pipeline(train_bayesian_glmm, calculate_bayesian_comfort_scores, 
                                feature_matrix, target_vector, participants, bigram_pairs, n_splits=5)
        
    #===========================================================#
    # Train a Bayesian GLMM and score using Bayesian posteriors #
    #===========================================================#
    if run_glmm:
        if run_samekey_analysis:
            selected_feature_names = None
        else:
            selected_feature_names = None  #['same', 'skip']

        trace, model, priors = train_bayesian_glmm(feature_matrix, target_vector, participants, 
            selected_feature_names=selected_feature_names, 
            typing_times=typing_times,
            inference_method="mcmc", 
            num_samples=2000, 
            chains=8)

        # Generate the summary of the posterior trace
        summary = az.summary(trace)

        # Define the number of rows to print
        print_nrows = 15

        # Print the first `print_nrows` rows of the summary
        print(summary.head(print_nrows))
        print("\n" + "=" * 50 + "\n")

        # Plot the trace for visual inspection
        az.plot_trace(trace)

        # Save trace, point estimates, model configuration, and prior information
        save_glmm_results(trace, model, "output/glmm_results")

        print("\n ---- Score comfort using Bayesian posteriors ---- \n")
        # Generate bigram typing comfort scores using the Bayesian posteriors
        bigram_comfort_scores = calculate_bayesian_comfort_scores(trace, bigram_pairs, feature_matrix, params=None,
                                                                  output_filename = "output/bigram_typing_comfort_scores.csv")
        # Print the comfort score for a specific bigram
        #print(bigram_comfort_scores)
        #print(bigram_comfort_scores['df'])

    #=========================================================================#
    # Score all LEFT bigrams based on the output of the GLMM, mirror on RIGHT #
    #=========================================================================#
    if score_all_bigrams:

        # Load the precomputed bigram features for all bigrams
        all_bigrams, all_bigram_features, feature_names, _, _, _ = precompute_all_bigram_features(left_layout_chars, 
                                                                        column_map, row_map, finger_map)

        # Load the left bigram comfort scores from the CSV file
        comfort_scores = pd.read_csv("output/bigram_typing_comfort_scores.csv", index_col='bigram')

        # Load the GLMM results
        loaded_trace, loaded_point_estimates, loaded_model_info = load_glmm_results("output/glmm_results")

        # Calculate comfort scores for all (left and mirrored right) bigrams
        all_bigram_comfort_scores = calculate_all_bigram_comfort_scores(loaded_trace, all_bigram_features,
                                                                        params=None, mirror_scores=True)

        # Convert to DataFrame and save to CSV
        all_scores_df = pd.DataFrame.from_dict(all_bigram_comfort_scores, orient='index', columns=['comfort_score'])
        all_scores_df.index = all_scores_df.index.map(lambda x: ''.join(x) if isinstance(x, tuple) else x)  # Convert tuple index to string
        all_scores_df.index.name = 'bigram'
        output_filename_all_scores = "output/all_bigram_comfort_scores.csv"
        all_scores_df.to_csv(f"{output_filename_all_scores}")

        print(f"Comfort scores for all bigrams (including right-hand mirrors) saved to {output_filename_all_scores}")

