import pandas as pd
import matplotlib.pyplot as plt

# 1. Provide your actual file name
filename = 'Battery_Full_Charge_170926.csv'
df = pd.read_csv(filename)

# 2. Convert 'time' column to datetime
df['time'] = pd.to_datetime(df['time'])

# 3. Calculate time gap (in hours) between rows
dt_hours = df['time'].diff().dt.total_seconds() / 3600.0
dt_hours = dt_hours.fillna(0)

# 4. Calculate average current between rows (Trapezoidal Rule)
mA_avg = df['mA'].rolling(window=2).mean().fillna(df['mA'])

# 5. Calculate mAh step and zero it out for "Rest Battery" modes
capacity_step = mA_avg * dt_hours
#capacity_step.loc[df['mode'] == 'Rest Battery'] = 0.0

# 6. Create the new column with the running total and save back to CSV
df['integrated_capacity_mAh'] = capacity_step.cumsum()
df.to_csv(filename, index=False)
print(f"Success! Saved new column to {filename}")

# --- 7. PLOT CELL VOLTAGES VS CUMULATIVE TOTAL ---
plt.figure(figsize=(12, 6))

# Dynamically loop and plot mV1 through mV12
for i in range(1, 13):
    col_name = f'mV{i}'
    if col_name in df.columns:
        plt.plot(df['integrated_capacity_mAh'], df[col_name], label=col_name, alpha=0.8)

# Configure chart details
plt.title('Cell Voltages (mV1-mV12) vs. Accumulated Capacity')
plt.xlabel('Integrated Capacity (mAh)')
plt.ylabel('Cell Voltage (mV)')
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')  # Moves legend outside the plot area
plt.tight_layout()

# Display the plot window
plt.show()
