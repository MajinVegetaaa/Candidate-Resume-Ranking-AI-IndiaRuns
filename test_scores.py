import json
import yaml
import numpy as np

with open('config/ranking_config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Mock some scores
ce_scores = np.array([-5.0, -2.0, 0.0, 2.0, 5.0])
min_ce = np.min(ce_scores)
max_ce = np.max(ce_scores)
if max_ce > min_ce:
    norm_ce = (ce_scores - min_ce) / (max_ce - min_ce)
else:
    norm_ce = np.zeros_like(ce_scores)
print("Norm CE:", norm_ce)
