
# bigram_typing_preferences_to_comfort_scores: 
Converting preferences of typing one bigram over another 
to individual bigram comfort scores via Bayesian Preference Learning
===================================================================

https://github.com/binarybottle/bigram_typing_preferences_to_comfort_scores.git

Author: Arno Klein (binarybottle.com)

## Workflow
1. Select important features
2. Collect targeted preference data
3. Train final preference model
4. Generate bigram comfort scores
5. Use scores for keyboard layout optimization

## Project Structure
bigram_typing_preferences_to_comfort_scores/                           
├── README                         # This file
├── config.yaml                    # Main configuration file
├── main.py                        # Pipeline implementation
├── memory-estimator.py            # Estimates memory requirements
└──    
    bigram_typing_preferences_to_comfort_scores/                       
    ├── features/                  
        ├── analyze_features.py    # Analyze feature metrics to determine optimal importance threshold
        ├── bigram_frequencies.py  # English language bigrams and bigram frequencies
        ├── feature_extraction.py  # Core feature computation
        ├── features.py            # Individual feature calculations
        ├── keymaps.py             # Keyboard layout definitions
    ├── models/                  
        ├── preference_model.stan  # Stan MCMC model file
    ├── utils/                     
        ├── config.py              # Configuration validation
        ├── logging.py             # Logging system
        └── visualization.py       # Visualization functions
    ├── data.py                    # Dataset management
    ├── model.py                   # Bayesian preference model
    └── recommendations.py         # Bigram pair recommendations

## Core Components
1. Data Processing (data.py)
   - Preference dataset management
   - Participant-aware splitting
   - Feature extraction and caching

2. Bayesian Model (model.py)
   - Hierarchical modeling with participant effects
   - Cross-validated feature selection
   - Uncertainty quantification

3. Recommendation Engine (recommendations.py)
   - PCA-based feature space analysis
   - Maximum-minimum distance selection
   - Feature space visualization

## Operation Modes
1. Feature Analysis
   ```bash
   python main.py --config config.yaml --mode analyze_features```

  - Determines feature importance thresholds
  - Evaluates feature interactions
  - Generates importance metrics

2. Feature Selection
   ```bash
   python main.py --config config.yaml --mode select_features```

  - Selects optimal feature combinations
  - Cross-validation with participant awareness
  - Metrics reporting

3. Model Training
   ```bash
   python main.py --config config.yaml --mode train_model```

  - Trains on selected features
  - Handles additional training data
  - Participant-aware validation

4. Bigram Recommendations
   ```bash
   python main.py --config config.yaml --mode recommend_bigram_pairs```

  - Generates diverse bigram pairs
  - Feature space coverage analysis
  - PCA-based visualization

5. Comfort Prediction
   ```bash
   python main.py --config config.yaml --mode predict_bigram_scores```

  - Predicts bigram comfort scores
  - Includes uncertainty estimates
  - Exports detailed results

## Configuration
config.yaml controls:
  - Dataset parameters and splits
  - Feature selection settings
  - Stan MCMC parameters
  - Recommendation criteria
  - Logging configuration

## License
MIT License. See LICENSE file for details.

## Requirements
  - Python packages: pyyaml, numpy, pandas, scikit-learn, matplotlib, cmdstanpy, adjustText, pydantic, tenacity
  - CmdStan v2.36.0 (special setup for M1/M2 Macs -- see below)

## Notes on Stan installation
Install Stan on Macos M1/M2 (or through Rosetta):
1. Create directory
   mkdir -p ~/.cmdstan
   cd ~/.cmdstan
2. Clone CmdStan
   git clone --depth 1 --branch v2.36.0 https://github.com/stan-dev/cmdstan.git cmdstan-2.36.0
   cd cmdstan-2.36.0
3. Initialize submodules
   git submodule update --init --recursive
4. Create make/local with very specific Apple Silicon settings
   cat > make/local << EOL
   STAN_OPENCL=false
   CC=/usr/bin/clang
   CXX=/usr/bin/clang++
   CFLAGS=-arch arm64 -target arm64-apple-darwin -isysroot $(xcrun --show-sdk-path)
   CXXFLAGS=-arch arm64 -target arm64-apple-darwin -isysroot $(xcrun --show-sdk-path)
   LDFLAGS=-arch arm64 -target arm64-apple-darwin
   STAN_FLAG_MARCH="-arch arm64"
   GTEST_CXXFLAGS="-arch arm64"
   O=3
   BUILD_ARCH=arm64
   OS=Darwin
   TBB_INTERFACE_NEW=TRUE
   EOL
5. Clean and build
   make clean-all
   STAN_CPU_ARCH=arm64 make build -j4

Note: Variations in Stan results are due to:
- MCMC sampling being inherently probabilistic
- Random initialization of Stan's MCMC chains
- Random train/test data splits using numpy's random seed
While the seed is set for reproducibility at each run, Stan chains operate independently 
and can explore the parameter space differently each time. This leads to slightly different 
posterior distributions and therefore different metrics.
These variations are expected and normal in Bayesian inference.
