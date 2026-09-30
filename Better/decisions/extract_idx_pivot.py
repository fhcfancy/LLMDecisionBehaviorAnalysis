import os
import pandas as pd
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

base_dir = f"{REPO_ROOT}/Better/decisions"
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
                        decision = str(row.iloc[0]['decision']).replace('\n', ' ').strip()
                        # Truncate decision if it's too long
                        if len(decision) > 100:
                            decision = decision[:97] + "..."
                            
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
                    pass

results_df = pd.DataFrame(results)

# Create a pivot table to show choice values more compactly
pivot_df = results_df.pivot_table(
    index=['Mode', 'Model'], 
    columns='Run', 
    values='Choice Value',
    aggfunc='first'
).reset_index()

print("### Choice Values by Mode and Model (Runs 1-3)")
print(pivot_df.to_markdown(index=False))
print("\n### Detailed Decisions")
print(results_df.to_markdown(index=False))
