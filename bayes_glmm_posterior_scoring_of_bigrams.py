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
import scipy.stats as stats
from itertools import product
import networkx as nx
import pymc as pm
import arviz as az
import ast
from ast import literal_eval
import json
import seaborn as sns
    
from bigram_features import *

#================================================#
# Set which features to use and functions to run # 
#================================================#
# NOTE: Set feature interactions (n_feature_interactions below)
left_layout_chars = list("qwertasdfgzxcvb")
selected_feature_names = ['freq', 'row_sum', 'engram_sum']  # freq is a control
features_for_design = ['row_sum', 'engram_sum']

# Analyze feature-timing relationship (see results in output/timing_vs_frequency/timing_frequency_relationship.txt)
run_analyze_timing_frequency_relationship = False 

# Analyze the feature space, and sensitivity and generalizability of priors
run_analyze_feature_space = True
if run_analyze_feature_space:
    run_recommend_bigram_pairs = True
    run_sensitivity_analysis = True
    run_cross_validation = True

# Run Bayesian GLMM and posterior scoring to estimate latent typing comfort for every bigram
run_glmm = False

# Score all bigrams based on the output of the GLMM
score_all_bigrams = False

# Incomplete
run_optimize_layout = False

#==============================#
# Functions to select features #
#==============================#
def extract_features(char1, char2, column_map, row_map, finger_map):
    features = {
        #--------------------------#
        # Qwerty frequency feature #
        #--------------------------#
        'freq': qwerty_bigram_frequency(char1, char2, bigrams, bigram_frequencies_array),
        #------------------------#
        # Same/adjacent features #
        #------------------------#
#        'same': same_finger(char1, char2, column_map, finger_map),
#        'adj': adjacent_finger(char1, char2, column_map, finger_map),
#        'adj_step': adj_finger_diff_row(char1, char2, column_map, row_map, finger_map),
#        'adj_skip': adj_finger_skip(char1, char2, column_map, row_map, finger_map),
        #---------------------#
        # Separation features #
        #---------------------#
#        'nrows': rows_apart(char1, char2, column_map, row_map),
#        'skip': skip_home(char1, char2, column_map, row_map),
#        'ncols': columns_apart(char1, char2, column_map),
#        'distance_apart': distance_apart(char1, char2, column_map, key_metrics),
#        'angle_apart': angle_apart(char1, char2, column_map, key_metrics),
        #--------------------#
        # Direction features #
        #--------------------#
#        'out': outward_roll(char1, char2, column_map, finger_map),
#        'out_same_row': outward_roll_same_row(char1, char2, column_map, row_map, finger_map),
#        'out_skip': outward_skip(char1, char2, column_map, finger_map),
        #-------------------#
        # Position features #
        #-------------------#
#        'middle': middle_column(char1, char2, column_map),
        'engram_sum': sum_engram_position_values(char1, char2, column_map, engram_position_values),
        'row_sum': sum_row_position_values(char1, char2, column_map, row_position_values)
        #'position_sum': sum_data_position_values(char1, char2, column_map, data_position_values)
        #-----------------#
        # Finger features #
        #-----------------#
        #'1skip2': finger1skip2(char1, char2, column_map, row_map, finger_map),
        #'2skip3': finger2skip3(char1, char2, column_map, row_map, finger_map),
        #'3skip4': finger3skip4(char1, char2, column_map, row_map, finger_map),
        #'f1': finger1(char1, char2, finger_map),
        #'f2': finger2(char1, char2, finger_map),
        #'f3': finger3(char1, char2, finger_map),
        #'f4': finger4(char1, char2, finger_map),
    #    '1above': finger1_above(char1, char2, column_map, row_map, finger_map),
        #'2above': finger2_above(char1, char2, column_map, row_map, finger_map),
        #'3above': finger3_above(char1, char2, column_map, row_map, finger_map),
    #    '4above': finger4_above(char1, char2, column_map, row_map, finger_map),
        #'1below': finger1_below(char1, char2, column_map, row_map, finger_map),
    #    '2below': finger2_below(char1, char2, column_map, row_map, finger_map),
    #    '3below': finger3_below(char1, char2, column_map, row_map, finger_map),
        #'4below': finger4_below(char1, char2, column_map, row_map, finger_map),
        #'1above2': finger1above2(char1, char2, column_map, row_map, finger_map),
        #'2above1': finger2above1(char1, char2, column_map, row_map, finger_map),
        #'2above3': finger2above3(char1, char2, column_map, row_map, finger_map),
        #'3above2': finger3above2(char1, char2, column_map, row_map, finger_map),
        #'3above4': finger3above4(char1, char2, column_map, row_map, finger_map),
        #'4above3': finger4above3(char1, char2, column_map, row_map, finger_map),
        #'2or3down': finger2or3down(char1, char2, column_map),
    #    '1or4_top_above': finger1or4_top_above(char1, char2, column_map, row_map),
    #    '2or3_bot_below': finger2or3_bottom_below(char1, char2, column_map, row_map)
        #'fpairs': finger_pairs(char1, char2, column_map, finger_map)
    }
    feature_names = list(features.keys())
    
    return features, feature_names

def extract_features_samekey(char, finger_map):
    features = {
        'finger1': int(finger_map[char] == 1),
        'finger2': int(finger_map[char] == 2),
        'finger3': int(finger_map[char] == 3),
        'finger4': int(finger_map[char] == 4)
    }
    feature_names = list(features.keys())
    
    return features, feature_names

#======================================================================================#
# Functions to compute features for all bigrams and their differences in feature space #
#======================================================================================#
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
    #plt.show()
    plt.savefig('output/bigram-connectivity-graph.png', dpi=300, bbox_inches='tight')
    plt.close()

#====================================================#
# Functions to analyze frequency-timing relationship #
#====================================================#
def analyze_timing_frequency_relationship(bigram_data, bigrams, bigram_frequencies_array):
    """
    Analyze relationship between normalized bigram frequency and typing time.
        
    - Works with individual bigrams rather than differences
    - Analyzes both raw and log-transformed frequencies (frequency distributions are often skewed)
    - Creates separate plots for raw and log frequencies
    - Provides statistics about the relationship

    To determine whether it makes sense to control for bigram frequency while focusing on ergonomic features,
    we want to first determine:
    - How strongly bigram frequency predicts typing time
    - Whether the relationship is linear or non-linear
    - How much variance in typing time is explained by frequency
    - Whether controlling for frequency in your GLMM was important

    Parameters:
    - bigram_data: DataFrame containing bigram pair data and timing
    - bigrams: List of bigrams ordered by frequency
    - bigram_frequencies_array: Array of corresponding frequency values
    """
    # Extract chosen bigrams and their timing
    frequencies = []
    timings = []
    bigram_list = []  # To track which bigrams we're analyzing
    
    # Process each row
    for _, row in bigram_data.iterrows():
        try:
            # Get chosen bigram (already a string)
            chosen_bigram = row['chosen_bigram'].lower().strip()
            
            if len(chosen_bigram) == 2:  # Ensure it's a valid bigram
                # Get normalized frequency for the bigram
                freq = qwerty_bigram_frequency(chosen_bigram[0], chosen_bigram[1], 
                                            bigrams, bigram_frequencies_array)
                frequencies.append(freq)
                timings.append(row['chosen_bigram_time'])
                bigram_list.append(chosen_bigram)
                
        except Exception as e:
            print(f"Error processing row - chosen_bigram: {row.get('chosen_bigram', 'N/A')}, "
                  f"error: {str(e)}")
            continue
    
    print(f"Number of bigrams analyzed: {len(frequencies)}")
    
    # Convert to numpy arrays
    frequencies = np.array(frequencies)
    timings = np.array(timings)
    
    # Remove any NaN values
    valid_mask = ~(np.isnan(frequencies) | np.isnan(timings))
    frequencies = frequencies[valid_mask]
    timings = timings[valid_mask]
    bigram_list = [b for i, b in enumerate(bigram_list) if valid_mask[i]]
    
    print(f"Number of bigrams after removing NaN: {len(frequencies)}")
    
    # Print some summary statistics
    print("\nFrequency Summary:")
    print(f"Mean frequency: {np.mean(frequencies):.6f}")
    print(f"Median frequency: {np.median(frequencies):.6f}")
    print(f"Min frequency: {np.min(frequencies):.6f}")
    print(f"Max frequency: {np.max(frequencies):.6f}")
    
    print("\nTiming Summary:")
    print(f"Mean timing: {np.mean(timings):.2f} ms")
    print(f"Median timing: {np.median(timings):.2f} ms")
    print(f"Min timing: {np.min(timings):.2f} ms")
    print(f"Max timing: {np.max(timings):.2f} ms")
    
    # Calculate correlations
    raw_correlation, raw_p_value = stats.pearsonr(frequencies, timings)
    log_frequencies = np.log10(frequencies + 1e-10)  # Add small constant to avoid log(0)
    log_correlation, log_p_value = stats.pearsonr(log_frequencies, timings)
    rank_correlation, rank_p_value = stats.spearmanr(frequencies, timings)
    
    # Linear regression using log frequencies
    from sklearn.linear_model import LinearRegression
    from sklearn.metrics import r2_score
    
    X = log_frequencies.reshape(-1, 1)
    y = timings
    reg = LinearRegression().fit(X, y)
    r2 = r2_score(y, reg.predict(X))
    
    # Print results
    print("\nCorrelation Results:")
    print(f"Raw Frequency Correlation: {raw_correlation:.3f} (p={raw_p_value:.3e})")
    print(f"Log Frequency Correlation: {log_correlation:.3f} (p={log_p_value:.3e})")
    print(f"Spearman Rank Correlation: {rank_correlation:.3f} (p={rank_p_value:.3e})")
    print(f"Log Frequency R²: {r2:.3f}")
    print(f"Regression coefficient: {reg.coef_[0]:.3f}")
    print(f"Intercept: {reg.intercept_:.3f}")
    
    # Create visualization
    plt.figure(figsize=(12, 5))
    
    # Raw frequency plot
    plt.subplot(1, 2, 1)
    plt.scatter(frequencies, timings, alpha=0.5, label='Data points')
    plt.xlabel('Normalized Bigram Frequency')
    plt.ylabel('Typing Time (ms)')
    plt.title('Raw Frequency vs Typing Time')
    
    # Add bigram labels for extreme points
    n_labels = 5  # Number of extreme points to label
    extreme_indices = np.argsort(frequencies)[-n_labels:]  # Highest frequencies
    for idx in extreme_indices:
        plt.annotate(bigram_list[idx], 
                    (frequencies[idx], timings[idx]),
                    xytext=(5, 5), textcoords='offset points')
    
    plt.text(0.05, 0.95, f'r: {raw_correlation:.3f}\np: {raw_p_value:.3e}', 
             transform=plt.gca().transAxes,
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    # Log frequency plot
    plt.subplot(1, 2, 2)
    plt.scatter(log_frequencies, timings, alpha=0.5, label='Data points')
    
    # Regression line
    x_range = np.linspace(log_frequencies.min(), log_frequencies.max(), 100)
    plt.plot(x_range, reg.predict(x_range.reshape(-1, 1)), 
             color='red', label='Regression line')
    
    plt.xlabel('Log10(Normalized Frequency)')
    plt.ylabel('Typing Time (ms)')
    plt.title('Log Frequency vs Typing Time')
    plt.legend()
    
    plt.text(0.05, 0.95, 
             f'r: {log_correlation:.3f}\nR²: {r2:.3f}\np: {log_p_value:.3e}', 
             transform=plt.gca().transAxes,
             verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig('output/timing_frequency_relationship.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    return {
        'raw_correlation': raw_correlation,
        'raw_p_value': raw_p_value,
        'log_correlation': log_correlation,
        'log_p_value': log_p_value,
        'rank_correlation': rank_correlation,
        'rank_p_value': rank_p_value,
        'r2': r2,
        'regression_coefficient': reg.coef_[0],
        'intercept': reg.intercept_,
        'n_samples': len(timings),
        'labeled_bigrams': [bigram_list[i] for i in extreme_indices]
    }                     

def compare_timing_by_frequency_groups(bigram_data, bigrams, bigram_frequencies_array, n_groups=4):
    """
    Compare typing times across different frequency groups.
    
    Parameters:
    - bigram_data: DataFrame containing timing data
    - bigrams: List of bigrams ordered by frequency
    - bigram_frequencies_array: Array of corresponding frequency values
    - n_groups: Number of frequency groups to create
    """
    import pandas as pd
    import numpy as np
    import scipy.stats as stats
    import matplotlib.pyplot as plt
    import seaborn as sns
    
    # First get frequencies for each chosen bigram
    freqs = []
    times = []
    bigram_texts = []
    
    for _, row in bigram_data.iterrows():
        chosen_bigram = row['chosen_bigram'].lower().strip()
        if len(chosen_bigram) == 2:
            freq = qwerty_bigram_frequency(chosen_bigram[0], chosen_bigram[1], 
                                         bigrams, bigram_frequencies_array)
            freqs.append(freq)
            times.append(row['chosen_bigram_time'])
            bigram_texts.append(chosen_bigram)
    
    # Create DataFrame with unique index
    analysis_df = pd.DataFrame({
        'bigram': bigram_texts,
        'frequency': freqs,
        'timing': times,
    })
    
    # Create frequency groups
    analysis_df['frequency_group'] = pd.qcut(analysis_df['frequency'], 
                                           n_groups, 
                                           labels=['Very Low', 'Low', 'High', 'Very High'])
    
    # Calculate summary statistics by group
    group_stats = analysis_df.groupby('frequency_group')['timing'].agg([
        'count', 'mean', 'std', 'median', 'min', 'max'
    ]).round(2)
    
    # Add frequency ranges for each group
    freq_ranges = analysis_df.groupby('frequency_group')['frequency'].agg(['min', 'max']).round(4)
    group_stats['freq_range'] = freq_ranges.apply(lambda x: f"{x['min']:.4f} - {x['max']:.4f}", axis=1)
    
    # Perform one-way ANOVA
    groups = [group['timing'].values for name, group in analysis_df.groupby('frequency_group')]
    f_stat, p_value = stats.f_oneway(*groups)
    
    # Print results
    print("\n---- Frequency Group Analysis ----\n")
    print("Group Statistics:")
    print(group_stats)
    print(f"\nOne-way ANOVA:")
    print(f"F-statistic: {f_stat:.3f}")
    print(f"p-value: {p_value:.3e}")
    
    # Create box plot
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=analysis_df, x='frequency_group', y='timing')
    plt.title('Typing Time Distribution by Frequency Group')
    plt.xlabel('Frequency Group')
    plt.ylabel('Typing Time (ms)')
    
    # Add sample sizes to x-axis labels
    sizes = analysis_df['frequency_group'].value_counts()
    plt.gca().set_xticklabels([f'{tick.get_text()}\n(n={sizes[tick.get_text()]})' 
                              for tick in plt.gca().get_xticklabels()])
    
    plt.savefig('output/timing_by_frequency_groups.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # Create violin plot
    plt.figure(figsize=(10, 6))
    sns.violinplot(data=analysis_df, x='frequency_group', y='timing')
    plt.title('Typing Time Distribution by Frequency Group (Violin Plot)')
    plt.xlabel('Frequency Group')
    plt.ylabel('Typing Time (ms)')
    
    # Add sample sizes to x-axis labels
    plt.gca().set_xticklabels([f'{tick.get_text()}\n(n={sizes[tick.get_text()]})' 
                              for tick in plt.gca().get_xticklabels()])
    
    plt.savefig('output/timing_by_frequency_groups_violin.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    return {
        'group_stats': group_stats,
        'anova_f_stat': f_stat,
        'anova_p_value': p_value
    }

#=========================================================================================================#
# Functions to evaluate feature space, feature matrix multicollinearity, priors sensitivity and stability #
#=========================================================================================================#
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
    #plt.show()
    plt.savefig('output/feature-space-pca-projection.png', dpi=300, bbox_inches='tight')
    plt.close()

    
    # Calculate the convex hull of the data points
    hull = ConvexHull(pca_result)
    hull_area = hull.area
    
    # Calculate the density of points
    point_density = len(pca_result) / hull_area
    
    print(f"Convex Hull Area: {hull_area}")
    print(f"Point Density: {point_density}")
    
    return pca, scaler, hull

#===============================================================#
# Functions to generate recommendations for new bigrams to test #
#===============================================================#
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
    #plt.show()
    plt.savefig('output/feature-space-underrepresented-areas.png', dpi=300, bbox_inches='tight')
    plt.close()
    
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
  
#============================================================================#
# Functions to train a Bayesian GLMM, and generate Bayesian posterior scores #
#============================================================================#
def train_bayesian_glmm(feature_matrix, target_vector, participants=None, 
                       selected_feature_names=None,
                       typing_times=None, inference_method="mcmc", 
                       num_samples=1000, chains=4):
    """
    Train a Bayesian GLMM with improved error handling and fallback options.
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

    # Define the model context block
    with pm.Model() as model:
        try:
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
            fixed_effects = pm.math.dot(selected_features_matrix, 
                                      pm.math.stack([feature_priors[name] for name in selected_feature_names]))
            if typing_times is not None:
                fixed_effects += typing_time_prior

            mu = (fixed_effects + participant_intercept[participants_contiguous]).reshape(target_vector.shape)

            # Likelihood: Observed target vector
            sigma = pm.HalfNormal('sigma', sigma=10)
            y_obs = pm.Normal('y_obs', mu=mu, sigma=sigma, observed=target_vector)

            # Choose the inference method with fallback options
            if inference_method == "mcmc":
                try:
                    # First attempt: Try with multiple chains
                    trace = pm.sample(num_samples, chains=chains, return_inferencedata=True)
                except Exception as e:
                    print(f"Warning: Multi-chain sampling failed ({str(e)}). Trying single chain...")
                    try:
                        # Second attempt: Try with a single chain
                        trace = pm.sample(num_samples, chains=1, return_inferencedata=True)
                    except Exception as e:
                        print(f"Warning: NUTS sampling failed ({str(e)}). Falling back to Metropolis...")
                        # Third attempt: Fall back to Metropolis
                        trace = pm.sample(num_samples, chains=1, step=pm.Metropolis(), 
                                        return_inferencedata=True)
            elif inference_method == "variational":
                try:
                    # Attempt variational inference
                    approx = pm.fit(method="advi", n=num_samples)
                    trace = approx.sample(num_samples)
                except Exception as e:
                    print(f"Warning: Variational inference failed ({str(e)}). Using MCMC...")
                    # Fall back to MCMC
                    trace = pm.sample(num_samples, chains=1, return_inferencedata=True)
            else:
                raise ValueError("Inference method must be 'mcmc' or 'variational'.")

        except Exception as e:
            print(f"Error in model training: {str(e)}")
            raise

    return trace, model, all_priors

    
def calculate_bayesian_comfort_scores(trace, bigram_pairs, feature_matrix, params=None, 
                                      features_for_design=None,
                                      output_filename="bigram_typing_comfort_scores.csv"):
    """
    Generate latent comfort scores using the full posterior distributions from a Bayesian GLMM.
    This version handles both feature-based and manual priors.

    We use Qwerty bigram frequency as a control variable to isolate ergonomic effects.
    This accounts for any frequency-based confounding effects in the data,
    gives cleaner estimates of the ergonomic features' true effects, and
    model coefficients for other features represent their effects while holding frequency constant.

    Parameters:
    - trace: The InferenceData object from the Bayesian GLMM
    - bigram_pairs: List of bigram pairs used in the comparisons
    - feature_matrix: The feature matrix used in the GLMM, indexed by bigram pairs
    - params: List of parameter names to use from the trace
    - features_for_design: List of features to use for scoring (excludes control variables)

    Returns:
    - bigram_comfort_scores
    """
    # Extract variable names from the trace
    all_vars = list(trace.posterior.data_vars)
    
    # If params is not provided, use all parameters except 'participant_intercept' and 'sigma'
    if params is None:
        params = [var for var in all_vars if var not in ['participant_intercept', 'sigma']]
    
    # If features_for_design not provided, use all params except known control variables
    if features_for_design is None:
        features_for_design = [p for p in params if p != 'freq']
    
    print(f"Design features used for scoring: {features_for_design}")
    
    # Extract posterior samples for design features only
    posterior_samples = {param: az.extract(trace, var_names=param).values 
                        for param in params if param in features_for_design}
    
    # Convert feature matrix to numpy array and extract relevant columns
    feature_array = feature_matrix[features_for_design].values

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

def calculate_all_bigram_comfort_scores(trace, all_bigram_features, params=None, 
                                        features_for_design=None, mirror_scores=True):
    """
    Calculate comfort scores for all possible bigrams.
    """
    # Extract variable names from the trace
    all_vars = list(trace.posterior.data_vars)
    
    # If params is not provided, use all parameters except 'participant_intercept' and 'sigma'
    if params is None:
        params = [var for var in all_vars if var not in ['participant_intercept', 'sigma']]
    
    # If features_for_design not provided, use all params except known control variables
    if features_for_design is None:
        features_for_design = [p for p in params if p != 'freq']
    
    print(f"Design features used for scoring: {features_for_design}")
    
    # Extract posterior samples for design features only
    posterior_samples = {param: az.extract(trace, var_names=param).values 
                        for param in params if param in features_for_design}
    
    # Calculate comfort scores for each bigram
    all_bigram_scores = {}
    for bigram, features in all_bigram_features.iterrows():
        # Calculate score using only design features
        scores = np.zeros(len(next(iter(posterior_samples.values()))))
        for param in features_for_design:
            if param in features.index:
                scores += posterior_samples[param] * features[param]
        
        # Use the mean score across all posterior samples
        all_bigram_scores[bigram] = np.mean(scores)
    
    # Normalize scores to 0-1 range, and subtract from 1
    min_score = min(all_bigram_scores.values())
    max_score = max(all_bigram_scores.values())
    normalized_scores = {bigram: 1 - (score - min_score) / (max_score - min_score) 
                         for bigram, score in all_bigram_scores.items()}
    #normalized_scores = {bigram: (score - min_score) / (max_score - min_score) 
    #                     for bigram, score in all_bigram_scores.items()}
    
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
#--------------------------------------------------------------------------------------------------#
#--------------------------------------------------------------------------------------------------#
####################################################################################################


if __name__ == "__main__":

    #############################################
    # Run feature analyses or GLMM on LEFT keys #
    #############################################
    run_samekey_analysis = False # compare repeat-key bigrams (data only for "aa", "ss", "dd", "ff")
    if run_analyze_timing_frequency_relationship or run_analyze_feature_space or run_glmm:

        #=======================================#
        # Load and prepare LEFT bigram features #
        #=======================================#
        print("\n ---- Load and prepare features ---- \n")

        # Precompute all bigram features and differences between the features of every pair of bigrams
        all_bigrams, all_bigram_features, feature_names, samekey_bigrams, samekey_bigram_features, \
            samekey_feature_names = precompute_all_bigram_features(left_layout_chars, column_map, row_map, finger_map)
        all_feature_differences = precompute_bigram_feature_differences(all_bigram_features)

        # Load the CSV file into a pandas DataFrame
        csv_file_path = "/Users/arno.klein/Documents/osf/output_all4studies_406participants/tables/filtered_bigram_data.csv"
        #csv_file_path = "/Users/arno.klein/Documents/osf/output_all4studies_406participants/tables/filtered_consistent_choices.csv"
        #csv_file_path = "/Users/arno.klein/Documents/osf/output_all4studies_303of406participants_0improbable/tables/filtered_bigram_data.csv"
        #csv_file_path = "/Users/arno.klein/Documents/osf/output_all4studies_303of406participants_0improbable/tables/filtered_consistent_choices.csv"
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
            n_feature_interactions = 0
            #feature_matrix['same_skip'] = feature_matrix['same'] * feature_matrix['skip']
            #feature_matrix['1_center'] = feature_matrix['same'] * feature_matrix['center']

        #=======================================#
        # Analyze frequency-timing relationship #
        #=======================================#
        if run_analyze_timing_frequency_relationship:

            print("\n ---- Analyze frequency-timing relationship ---- \n")

            correlation_results = analyze_timing_frequency_relationship(bigram_data, bigrams, bigram_frequencies_array)
            group_comparison_results = compare_timing_by_frequency_groups(bigram_data, bigrams, bigram_frequencies_array, n_groups=4)

        #=========================================================================================#
        # Check feature space, feature matrix multicollinearity, priors sensitivity and stability #
        #=========================================================================================#
        if run_analyze_feature_space:

            print("\n ---- Analyze feature space ---- \n")

            # Plot a graph of all bigram pairs to see how well they are connected
            plot_bigram_pair_graph = False
            if plot_bigram_pair_graph:
                plot_bigram_graph(bigram_pairs)

            if run_recommend_bigram_pairs:

                pca, scaler, hull = analyze_feature_space(feature_matrix)
                grid_points, distances = identify_underrepresented_areas(pca.transform(scaler.transform(feature_matrix)))
                new_feature_differences = generate_new_features(grid_points, distances, pca, scaler)

                # Remove feature interactions 
                # (timing should be in the last column (prior appended to all_priors in train_bayesian_glmm))
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
                                                                selected_feature_names,
                                                                typing_times=typing_times, 
                                                                prior_means=[0, 50, 100], 
                                                                prior_stds=[1, 10, 100])
            if run_cross_validation:
                cv_scores = bayesian_cv_pipeline(train_bayesian_glmm, calculate_bayesian_comfort_scores, 
                                feature_matrix, target_vector, participants, bigram_pairs, n_splits=5)
        
    #############################################################
    # Train a Bayesian GLMM and score using Bayesian posteriors #
    #############################################################
    if run_glmm:

        trace, model, priors = train_bayesian_glmm(feature_matrix, target_vector, participants, 
            selected_feature_names, 
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
                                                                  features_for_design=features_for_design,
                                                                  output_filename = "output/bigram_typing_comfort_scores.csv")
        # Print the comfort score for a specific bigram
        #print(bigram_comfort_scores)
        #print(bigram_comfort_scores['df'])

    ###########################################################################
    # Score all LEFT bigrams based on the output of the GLMM, mirror on RIGHT #
    # NOTE: Subtract score from 1
    ###########################################################################
    if score_all_bigrams:

        # Load the precomputed bigram features for all bigrams
        all_bigrams, all_bigram_features, feature_names, _, _, _ = precompute_all_bigram_features(left_layout_chars, 
                                                                        column_map, row_map, finger_map)

        # Load the left bigram comfort scores from the CSV file
        comfort_scores = pd.read_csv("output/bigram_typing_comfort_scores.csv", index_col='bigram')

        # Load the GLMM results
        loaded_trace, loaded_point_estimates, loaded_model_info = load_glmm_results("output/glmm_results")

        # Calculate comfort scores for all (left and mirrored right) bigrams
        all_bigram_comfort_scores = calculate_all_bigram_comfort_scores(loaded_trace, all_bigram_features, params=None, 
                                                                        features_for_design=features_for_design, mirror_scores=True)

        # Convert to DataFrame and save to CSV
        all_scores_df = pd.DataFrame.from_dict(all_bigram_comfort_scores, orient='index', columns=['comfort_score'])
        all_scores_df.index = all_scores_df.index.map(lambda x: ''.join(x) if isinstance(x, tuple) else x)  # Convert tuple index to string
        all_scores_df.index.name = 'bigram'
        output_filename_all_scores = "output/all_bigram_comfort_scores.csv"
        all_scores_df.to_csv(f"{output_filename_all_scores}")

        print(f"Comfort scores for all bigrams (including right-hand mirrors) saved to {output_filename_all_scores}")

