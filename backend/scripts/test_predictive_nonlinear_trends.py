import sys
import os
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.graph.trends import fit_models

def test_nonlinear_predictive_trends():
    print("=" * 70)
    print("   TEST: Non-Linear Regression & Conservative Trend Forecasting       ")
    print("=" * 70)

    # Accelerating vibration time series (Day 0: 2.1, Day 30: 3.5, Day 60: 6.8 mm/s)
    x = np.array([0.0, 30.0, 60.0])
    y = np.array([2.1, 3.5, 6.8])

    fit_res = fit_models(x, y)
    lin = fit_res["linear"]
    poly2 = fit_res["polynomial_deg2"]

    print(f" -> Linear Fit: Slope={lin['slope']:.4f} mm/s/day, R²={lin['r_squared']}")
    print(f" -> Non-Linear Fit (Deg 2): a={poly2['a']:.5f}, b={poly2['b']:.4f}, R²={poly2['r_squared']}, Accelerating={poly2['is_accelerating']}")

    # Non-linear fit should have equal or higher R² on convex curve
    assert poly2["r_squared"] >= lin["r_squared"], "Polynomial fit R² must be >= linear fit on accelerating degradation curve"
    assert poly2["is_accelerating"] is True, "Positive acceleration (a > 0) must be detected"

    # Days to reach 7.1 mm/s threshold:
    # Linear: (7.1 - 6.8) / slope
    lin_slope = lin["slope"]
    lin_days = (7.1 - 6.8) / lin_slope
    print(f" -> Linear projection to 7.1 mm/s: {lin_days:.1f} days")

    # In accelerating condition, failure occurs sooner than linear extrapolation suggests
    assert lin_days > 0.0, "Linear days to threshold must be positive"
    print("\n[PASS] Non-linear regression and acceleration detection verified successfully!")
    print("=" * 70)

if __name__ == "__main__":
    test_nonlinear_predictive_trends()
