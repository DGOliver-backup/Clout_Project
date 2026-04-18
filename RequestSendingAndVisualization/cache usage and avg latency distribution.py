import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

# Config
task_configs = {
    "1.1": {"main": "Workload: Small-heavy", "desc": "85% Small Files | Cache: 40MB | Batch: 5"},
    "1.2": {"main": "Workload: Uniform", "desc": "33% Small/Med/Large | Cache: 40MB | Batch: 5"},
    "1.3": {"main": "Workload: Large-heavy", "desc": "85% Large Files | Cache: 40MB | Batch: 5"},
    "2.2": {"main": "Sensitivity: Constrained Cache", "desc": "Size: 10MB | Workload: Standard | Batch: 5"},
    "3.2": {"main": "Sensitivity: High Traffic", "desc": "Batch Size: 20 | Workload: Standard | Cache: 40MB"}
}

policy_colors = {"LRU": "#636EFA", "LFU": "#EF553B", "TTL": "#00CC96"}
policies = ["LRU", "LFU", "TTL"]

def create_policy_figure(file_id):
    config = task_configs.get(file_id, {"main": f"Experiment {file_id}", "desc": ""})
    
    try:
        with open(f"{file_id}.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Skipping {file_id}: File not found.")
        return None

    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=[f"<b>Policy: {p}</b>" for p in policies],
        shared_xaxes=True,
        vertical_spacing=0.08,
        specs=[[{"secondary_y": True}], [{"secondary_y": True}], [{"secondary_y": True}]]
    )

    for i, policy in enumerate(policies):
        if policy not in data: continue
        
        df = pd.DataFrame(data[policy].get("requests", []))
        if df.empty: continue
        
        df["UsagePct"] = df["cache_usage_float"].astype(float) * 100
        df["Latency"] = df["latency_ms"].astype(float)
        
        fig.add_trace(go.Histogram(
            x=df["UsagePct"],
            name=f"{policy} Distribution",
            xbins=dict(start=0, end=100, size=5),
            marker_color=policy_colors[policy],
            opacity=0.3,
            legendgroup=policy, 
            showlegend=True if i == 0 else False 
        ), row=i+1, col=1, secondary_y=False)
        
        bins = np.arange(0, 105, 5)
        df['bin'] = pd.cut(df['UsagePct'], bins=bins, labels=bins[:-1] + 2.5) 
        bin_means = df.groupby('bin', observed=True)['Latency'].mean().reset_index()
        
        fig.add_trace(go.Scatter(
            x=bin_means['bin'],
            y=bin_means['Latency'],
            name=f"{policy} Avg Latency",
            mode='lines+markers',
            line=dict(color=policy_colors[policy], width=2.5),
            marker=dict(size=6, symbol='diamond'),
            connectgaps=True,
            legendgroup=policy,
            showlegend=True if i == 0 else False
        ), row=i+1, col=1, secondary_y=True)

    full_title = f"<span style='font-size:24px;'>{config['main']}</span><br><span style='font-size:14px; color:gray;'>{config['desc']}</span>"
    
    fig.update_layout(
        title=dict(text=full_title, x=0.5, y=0.96, xanchor='center'),
        height=1000,
        width=1100,
        template="plotly_white",
        margin=dict(t=150, b=80, l=80, r=80),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    fig.update_xaxes(title_text="Cache Usage (%)", range=[0, 100], row=3, col=1)
    for row in range(1, 4):
        fig.update_yaxes(title_text="Request Count", secondary_y=False, row=row, col=1)
        fig.update_yaxes(title_text="Latency (ms)", secondary_y=True, row=row, col=1)

    return fig

output_file = "cache usage and avg latency distribution.html"
file_ids = ["1.1", "1.2", "1.3", "2.2", "3.2"]

with open(output_file, "w", encoding="utf-8") as f:
    f.write("<html><head><title>Cache Strategy Analysis</title></head><body style='background-color:#f8f9fa;'>")
    f.write("<div style='max-width:1200px; margin:auto; background:white; padding:20px; box-shadow:0 0 10px rgba(0,0,0,0.1);'>")
    f.write("<h1 style='text-align:center; font-family:sans-serif;'>System Performance Demo: Edge Caching Policies</h1>")
    
    for fid in file_ids:
        fig = create_policy_figure(fid)
        if fig:
            chart_div = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
            f.write(f"<div style='margin-top:50px; border-bottom:2px solid #eee; padding-bottom:50px;'>{chart_div}</div>")
            
    f.write("</div></body></html>")

print(f"Report generated: {output_file}")
