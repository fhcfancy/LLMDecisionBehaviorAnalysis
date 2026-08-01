import pandas as pd

filepath = "/Users/carina/Documents/MyResearch/Professional/DataAnalysis/Better/decisions/Neutral/Neutral_CN_1.csv"
target_idxs = [24502, 31266, 11101, 29454]

df = pd.read_csv(filepath)
dilemmas = df[df['idx'].isin(target_idxs)][['idx', 'dilemma_situation', 'action1', 'action2']]

for _, row in dilemmas.iterrows():
    print(f"--- IDX: {row['idx']} ---")
    print(f"Situation: {row['dilemma_situation']}")
    print(f"Action 1: {row['action1']}")
    print(f"Action 2: {row['action2']}\n")
