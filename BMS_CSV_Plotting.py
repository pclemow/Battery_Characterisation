import pandas as pd
import matplotlib.pyplot as plt

# File path
csv_path = "./Data/bms_discharge_05.csv"
out_png = "./Data/bms_cells_plot.png"

# Read CSV
try:
    df = pd.read_csv(csv_path, engine="python")
except Exception as e:
    raise SystemExit(f"Failed to read CSV: {e}")

# Parse time column if possible
time_col = "time"
if time_col in df.columns:
    try:
        df[time_col] = pd.to_datetime(df[time_col])
        x = df[time_col]
    except Exception:
        x = df[time_col]
else:
    raise SystemExit(f"Expected time column '{time_col}' not found in CSV columns: {list(df.columns)}")

# Prepare voltage columns
voltage_cols = [f"mV{i}" for i in range(1, 13)]
missing = [c for c in voltage_cols if c not in df.columns]
if missing:
    raise SystemExit(f"Missing expected voltage columns: {missing}")

# Plot
plt.style.use("seaborn-darkgrid")
fig, ax = plt.subplots(figsize=(14, 7))

for col in voltage_cols:
    ax.plot(x, df[col], label=col, linewidth=1)

ax.set_title("12-cell BMS voltages (mV1–mV12)")
ax.set_xlabel("Time")
ax.set_ylabel("Voltage (mV)")
ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), ncol=1)
plt.tight_layout()

# Save and show
plt.savefig(out_png, dpi=300, bbox_inches="tight")
plt.show()
