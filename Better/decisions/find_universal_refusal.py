import os
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

base_dir = f"{REPO_ROOT}/Better/decisions"
modes = ["EmotionalAnalytic", "EmotionalIntuitive", "Neutral", "Neutral-CoT"]
models = ["CN", "CT", "R1", "V3"]
runs = [1, 2, 3]

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
                    # Only read necessary columns to save memory and time
                    df = pd.read_csv(filepath, usecols=['idx', 'choice_value'])
                    df['Mode'] = mode
                    df['Model'] = model
                    df['Run'] = run
                    all_data.append(df)
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")

if all_data:
    combined_df = pd.concat(all_data, ignore_index=True)
    
    # Group by idx to calculate refusal stats
    stats = combined_df.groupby('idx').agg(
        total_evals=('choice_value', 'count'),
        refusal_count=('choice_value', lambda x: (x == 0).sum())
    ).reset_index()
    
    stats['refusal_rate'] = stats['refusal_count'] / stats['total_evals']
    
    # Sort by refusal rate descending
    stats = stats.sort_values(by=['refusal_rate', 'refusal_count'], ascending=[False, False])
    
    print("### Top 10 Most Refused Dilemmas")
    print(stats.head(10).to_markdown(index=False))
    
    universal = stats[(stats['refusal_rate'] == 1.0) & (stats['total_evals'] == 48)]
    if not universal.empty:
        print(f"\nFound {len(universal)} universally refused dilemma(s) (100% refusal across all 48 evaluations):")
        print(universal['idx'].tolist())
    else:
        print("\nNo dilemma was universally refused (100% refusal rate across all 48 evaluations).")
else:
    print("No data found.")
