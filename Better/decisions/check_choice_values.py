import os
import pandas as pd

base_dir = "/Users/carina/Documents/MyResearch/Professional/DataAnalysis/Better/decisions"
modes = ["EmotionalAnalytic", "EmotionalIntuitive", "Neutral", "Neutral-CoT"]
models = ["CN", "CT", "R1", "V3"]
runs = [1, 2, 3]

# We will check if there's any refusal (choice_value == 0) across all modes/models
# Just to be absolutely sure, let's also check if there are any other choices that might be considered "refusal" 
# like choice_value == -1 or something similar.

all_data = []

for mode in modes:
    mode_dir = os.path.join(base_dir, mode)
    if not os.path.exists(mode_dir):
        continue
    
    for model in models:
        for run in runs:
            if mode == "EmotionalAnalytic":
                prefix = "EA"
            elif mode == "EmotionalIntuitive":
                prefix = "EI"
            else:
                prefix = mode
                
            filename = f"{prefix}_{model}_{run}.csv"
            filepath = os.path.join(mode_dir, filename)
            
            if os.path.exists(filepath):
                try:
                    df = pd.read_csv(filepath, usecols=['idx', 'choice_value'])
                    all_data.append(df)
                except Exception as e:
                    pass

if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)
    print("Unique choice values present in the dataset:")
    print(combined_df['choice_value'].value_counts())
