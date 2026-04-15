import json
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

# --- 1. 配置 ---
files = ["1.1", "1.2", "1.3", "2.2", "3.2"]
target_policies = ["LRU", "LFU", "TTL"]
colors = {"LRU": "#AB63FA", "LFU": "#EF553B", "TTL": "#00CC96"}

exp_meta = {
    "1.1": "Workload: Small-heavy (85% small)",
    "1.2": "Workload: Uniform (33% each)",
    "1.3": "Workload: Large-heavy (85% large)",
    "2.2": "Sensitivity: Constrained Cache (10MB)",
    "3.2": "Sensitivity: High Traffic (Batch 20)"
}

def create_latency_fig(file_id):
    desc = exp_meta.get(file_id, "General Experiment")
    fig = make_subplots(
        rows=3, cols=1, 
        subplot_titles=[f"<b>{p}</b> Latency Distribution" for p in target_policies],
        shared_xaxes=False, # 关闭共享，以便针对高延迟实验自动缩放
        vertical_spacing=0.1
    )

    max_p99_in_file = 0 # 用于动态调整 X 轴

    try:
        with open(f"{file_id}.json", "r") as f:
            data = json.load(f)
            
        for i, policy_name in enumerate(target_policies):
            if policy_name not in data: continue
            
            reqs = data[policy_name].get("requests", [])
            latencies = [float(r["latency_ms"]) for r in reqs if r.get("status_code") == 200]
            
            if latencies:
                p99 = np.percentile(latencies, 99)
                max_p99_in_file = max(max_p99_in_file, p99)
                
                # 添加直方图
                fig.add_trace(
                    go.Histogram(
                        x=latencies,
                        name=f"{policy_name} Dist",
                        nbinsx=100, 
                        marker_color=colors[policy_name],
                        opacity=0.6,
                        showlegend=False
                    ),
                    row=i+1, col=1
                )
                
                # 绘制 P99 虚线
                fig.add_vline(
                    x=p99, 
                    line_width=3, # 加粗
                    line_dash="dash", 
                    line_color="red",
                    annotation_text=f"P99: {int(p99)}ms", 
                    annotation_position="top right",
                    annotation_font=dict(size=14, color="red"),
                    row=i+1, col=1
                )

        # --- 动态 X 轴逻辑 ---
        # 如果是 3.2 且延迟很高，自动放宽坐标轴；否则默认 4000ms
        x_limit = max(4000, max_p99_in_file * 1.2)
        
        fig.update_layout(
            title=dict(text=f"Experiment {file_id}: {desc}", x=0.5, font=dict(size=22)),
            height=1000, 
            width=1000,
            template="plotly_white",
            margin=dict(t=150, b=80)
        )

        fig.update_xaxes(title_text="Latency (ms)", range=[0, x_limit])
        for r in range(1, 4):
            fig.update_yaxes(title_text="Frequency", row=r, col=1)

        return fig
    except FileNotFoundError:
        return None

# --- 2. 渲染合并 ---
output_file = "fixed_latency_p99_report.html"
with open(output_file, "w", encoding="utf-8") as f:
    f.write("<html><head><meta charset='utf-8' /></head><body style='background:#f4f7f9;'>")
    f.write("<div style='max-width:1100px; margin:auto; background:white; padding:20px;'>")
    f.write("<h1 style='text-align:center;'>Enhanced Latency Tail Analysis</h1>")
    f.write("<p style='text-align:center;'>Red dashed lines represent the 99th percentile (P99).</p>")
    
    for fid in files:
        fig = create_latency_fig(fid)
        if fig:
            f.write(pio.to_html(fig, full_html=False, include_plotlyjs='cdn'))
            f.write("<div style='height:100px;'></div>") # 间隔
            
    f.write("</div></body></html>")

