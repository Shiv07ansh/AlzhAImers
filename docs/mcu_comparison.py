import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# Original device table
device_data = [
    ["NodeMCU ESP8266", 170, "160 KB / 4 MB", 3, "No"],
    ["ESP32 (Original)", 240, "520 KB / 4 MB", 4.5, "Yes"],
    ["ESP32‑S3 Mini", 80, "512 KB / 8 MB", 5, "Yes"],
    ["Raspberry Pi Pico W", 100, "264 KB / 2 MB", 6, "No"],
    ["STM32H7 (Nucleo‑144)", 200, "1 MB / ext.", 20, "Yes"],
    ["Raspberry Pi 4 Model B", 650, "2–8 GB / SD", 55, "Yes"],
    ["NVIDIA Jetson Nano", 650, "4 GB / SD", 59, "Yes"],
    ["Google Coral Dev Board", 400, "1 GB / eMMC", 129, "Yes"],
    # Devices from papers
    ["Arduino Uno", 50, "2 KB / 32 KB", 3, "No"],
    ["ESP32 (Generic)", 240, "520 KB / 4 MB", 4.5, "Yes"],
    ["Raspberry Pi 3", 500, "1 GB / SD", 40, "Yes"],
    ["Arduino Nano", 30, "2 KB / 32 KB", 2.5, "No"],
    ["PIC Microcontroller", 20, "Variable", 5, "No"]
]

columns = ["Device", "Power_mA", "Memory_Flash", "Cost_USD", "Local_Inference"]
df = pd.DataFrame(device_data, columns=columns)

# Add normalized score columns: power (lower is better), cost (lower is better), inference (Yes=1, No=0)
df["Inference_Score"] = df["Local_Inference"].apply(lambda x: 1 if x == "Yes" else 0)
df["Norm_Power"] = 1 - (df["Power_mA"] - df["Power_mA"].min()) / (df["Power_mA"].max() - df["Power_mA"].min())
df["Norm_Cost"] = 1 - (df["Cost_USD"] - df["Cost_USD"].min()) / (df["Cost_USD"].max() - df["Cost_USD"].min())

# Combine into an overall score (equally weighted)
df["Total_Score"] = df[["Norm_Power", "Norm_Cost", "Inference_Score"]].mean(axis=1)

# Heatmap visualization
score_cols = ["Norm_Power", "Norm_Cost", "Inference_Score", "Total_Score"]
heatmap_data = df.set_index("Device")[score_cols]

plt.figure(figsize=(12, 8))
sns.heatmap(heatmap_data, annot=True, cmap="YlGnBu", cbar_kws={'label': 'Normalized Score'}, linewidths=0.5)
plt.title("Normalized Performance Comparison of Embedded AI Devices")
plt.tight_layout()
plt.show()

df_display = df[["Device", "Power_mA", "Memory_Flash", "Cost_USD", "Local_Inference", "Total_Score"]].sort_values(by="Total_Score", ascending=False)
df_display.reset_index(drop=True, inplace=True)
df_display.round(2)