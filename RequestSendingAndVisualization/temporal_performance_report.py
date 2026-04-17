import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

# --- 1. 实验场景配置 ---
files = ["1.1", "1.2", "1.3", "2.2", "3.2"]
exp_meta = {
    "1.1": "Workload: Small-heavy (85% small)",
    "1.2": "Workload: Uniform (33% each)",
    "1.3": "Workload: Large-heavy (85% large)",
    "2.2": "Sensitivity: Constrained Cache (10MB)",
    "3.2": "Sensitivity: High Traffic (Batch 20)"
}
policy_colors = {"LRU": "#636EFA", "LFU": "#EF553B", "TTL": "#00CC96"}
policies = ["LRU", "LFU", "TTL"]

def create_temporal_fig(file_id):
    desc = exp_meta.get(file_id, "General Experiment")
    
    # 创建画布
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    try:
        with open(f"{file_id}.json", "r") as f:
            data = json.load(f)
        
        for policy in policies:
            if policy not in data: continue
            
            content = data[policy]
            reqs = content.get("requests", [])
            if not reqs: continue
            
            p_df = pd.DataFrame(reqs)
            p_df["RequestIdx"] = range(len(p_df))
            p_df["UsagePct"] = p_df["cache_usage_float"].astype(float) * 100
            p_df["ClientLatency"] = p_df["latency_ms"].astype(float)
            
            color = policy_colors.get(policy)
            
            # --- Cache Usage (左轴 - 实线) ---
            # 使用滑动平均平滑数据，window=20
            ma_usage = p_df["UsagePct"].rolling(window=20, min_periods=1).mean()
            fig.add_trace(go.Scatter(
                x=p_df["RequestIdx"], y=ma_usage, 
                name=f"{policy} Usage (%)", 
                mode='lines',
                line=dict(color=color, width=2),
                legendgroup=policy,
            ), secondary_y=False)
            
            # --- Latency (右轴 - 虚线) ---
            ma_latency = p_df["ClientLatency"].rolling(window=20, min_periods=1).mean()
            fig.add_trace(go.Scatter(
                x=p_df["RequestIdx"], y=ma_latency, 
                name=f"{policy} Latency (ms)", 
                mode='lines',
                line=dict(color=color, dash="dot", width=1.5),
                legendgroup=policy,
            ), secondary_y=True)

        # 布局美化
        fig.update_layout(
            title=dict(text=f"<b>Experiment {file_id}</b>: {desc}", x=0.5, font=dict(size=18)),
            height=500, width=1100,
            template="plotly_white",
            hovermode="x unified",
            legend=dict(
                orientation="v", yanchor="top", y=1, xanchor="left", x=1.02,
                bgcolor="rgba(255, 255, 255, 0.5)", font=dict(size=10)
            ),
            margin=dict(r=150, t=80, b=50)
        )

        fig.update_xaxes(title_text="Request Sequence")
        fig.update_yaxes(title_text="Cache Usage (%)", range=[0, 105], secondary_y=False)
        fig.update_yaxes(title_text="Avg Latency (ms)", secondary_y=True)

        return fig

    except FileNotFoundError:
        print(f"Warning: {file_id}.json not found.")
        return None

# --- 2. 批量渲染与合并 ---
output_file = "temporal_performance_report.html"

with open(output_file, "w", encoding="utf-8") as f:
    f.write("<html><head><meta charset='utf-8' /><title>Temporal Analysis Demo</title></head>")
    f.write("<body style='background-color:#f4f7f9; padding:20px; font-family:sans-serif;'>")
    f.write("<div style='max-width:1200px; margin:auto; background:white; padding:30px; box-shadow:0 4px 20px rgba(0,0,0,0.08);'>")
    f.write("<h1 style='text-align:center; color:#2c3e50;'>Temporal Performance Analysis</h1>")
    f.write("<p style='text-align:center; color:#7f8c8d;'>Solid Line: Cache Usage (%) | Dotted Line: Latency (ms)</p>")
    f.write("<hr style='border:0; height:1px; background:#eee; margin:30px 0;'>")

    for fid in files:
        fig = create_temporal_fig(fid)
        if fig:
            chart_html = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')
            f.write(f"<div style='margin-bottom:60px;'>{chart_html}</div>")
    
    f.write("</div></body></html>")

print(f"Successfully generated: {output_file}")