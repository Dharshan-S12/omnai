import numpy as np
arr = np.array([1.2, 4.5, 3.8, 5.2])
rms = float(np.sqrt(np.mean(arr**2)))
print(f"COMPUTED_RMS:{rms:.2f}")
