import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Config
files = ["3.2"]
summary_list = []

# Load data
for file_name in files:
    try:
        with open(f"{file_name}.json", "r") as f:
            data = json.load(f)
            
        for policy, content in data.items():
            s = content.get("stats", {})
            reqs = content.get("requests", [])
            
            # Average Latency 
            latencies = [float(r["latency_ms"]) for r in reqs if r.get("status_code") == 200]
            avg_latency = round(np.mean(latencies), 2) if latencies else 0
            
            summary_list.append({
                "Workload": file_name, 
                "Policy": policy,
                "Hit Rate": round(s.get("hit_rate", 0) * 100, 2),
                "Avg Latency": avg_latency
            })
    except FileNotFoundError:
        print(f"Warning: {file_name}.json not found.")

df_sum = pd.DataFrame(summary_list)

fig = make_subplots(specs=[[{"secondary_y": True}]])

x_labels = [f"{row['Workload']} ({row['Policy']})" for _, row in df_sum.iterrows()]

fig.add_trace(go.Bar(
    x=x_labels, 
    y=df_sum["Hit Rate"], 
    text=df_sum["Hit Rate"], 
    textposition="auto",
    name="Hit Rate (%)", 
    marker_color='indianred',
    opacity=0.8
), secondary_y=False)

fig.add_trace(go.Scatter(
    x=x_labels, 
    y=df_sum["Avg Latency"], 
    text=df_sum["Avg Latency"], 
    textposition="top center",
    mode='lines+markers+text', 
    name="Average Latency (ms)",
    line=dict(color='royalblue', width=3),
    marker=dict(size=10)
), secondary_y=True)

fig.update_layout(
        template="plotly_white",
    hovermode="x unified",
    legend=dict(x=1.1, y=1) 
)

fig.update_yaxes(title_text="<b>Hit Rate (%)</b>", secondary_y=False, range=[0, 100])
fig.update_yaxes(title_text="<b>Average Latency (ms)</b>", secondary_y=True)

fig.show()
fig.write_html("workload_performance_summary.html")
