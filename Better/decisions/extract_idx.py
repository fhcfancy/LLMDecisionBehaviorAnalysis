import os
import pandas as pd
import glob

base_dir = "/Users/carina/Documents/MyResearch/Professional/DataAnalysis/Better/decisions"
target_idx = 24502

modes = ["EmotionalAnalytic", "EmotionalIntuitive", "Neutral", "Neutral-CoT"]
models = ["CN", "CT", "R1", "V3"]
runs = [1, 2, 3]

results = []

for mode in modes:
    mode_dir = os.path.join(base_dir, mode)
    if not os.path.exists(mode_dir):
        continue
    
    for model in models:
        for run in runs:
            # Construct file pattern
            # Files are named like EA_CN_1.csv, EI_CN_1.csv, Neutral_CN_1.csv, Neutral-CoT_CN_1.csv
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
                    df = pd.read_csv(filepath)
                    row = df[df['idx'] == target_idx]
                    if not row.empty:
                        choice_val = row.iloc[0]['choice_value']
                        decision = row.iloc[0]['decision']
                        
                        results.append({
                            "Mode": mode,
                            "Model": model,
                            "Run": run,
                            "Choice Value": choice_val,
                            "Decision": decision
                        })
                    else:
                        results.append({
                            "Mode": mode,
                            "Model": model,
                            "Run": run,
                            "Choice Value": "Not Found",
                            "Decision": "Not Found"
                        })
                except Exception as e:
                    print(f"Error reading {filepath}: {e}")

results_df = pd.DataFrame(results)
print(results_df.to_markdown(index=False))
