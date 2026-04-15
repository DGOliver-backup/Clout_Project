import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio

# --- 1. 基础配置：锁定 1.1 ---
file_id = "1.1"
policies = ["LRU", "LFU", "TTL"]
policy_colors = {"LRU": "#636EFA", "LFU": "#EF553B", "TTL": "#00CC96"}
exp_title = "Experiment 1.1-Comprehensive Report"

def generate_report_1_1():
    try:
        with open(f"{file_id}.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: {file_id}.json not found.")
        return

    # --- 模块 A: 总体统计 (Hit Rate & Avg Latency) ---
    summary_list = []
    for p in policies:
        if p in data:
            stats = data[p].get("stats", {})
            reqs = data[p].get("requests", [])
            lats = [float(r["latency_ms"]) for r in reqs if r.get("status_code") == 200]
            summary_list.append({
                "Policy": p,
                "Hit Rate": round(stats.get("hit_rate", 0) * 100, 2),
                "Avg Latency": round(np.mean(lats), 2) if lats else 0
            })
    df_sum = pd.DataFrame(summary_list)
    fig_sum = make_subplots(specs=[[{"secondary_y": True}]])
    fig_sum.add_trace(go.Bar(x=df_sum["Policy"], y=df_sum["Hit Rate"], text=df_sum["Hit Rate"], 
                             textposition="inside", name="Hit Rate (%)", marker_color='indianred'), secondary_y=False)
    fig_sum.add_trace(go.Scatter(x=df_sum["Policy"], y=df_sum["Avg Latency"], text=df_sum["Avg Latency"], 
                                 mode='lines+markers+text', textposition="top center", name="Avg Latency (ms)"), secondary_y=True)
    fig_sum.update_layout(title="<b>Section 1: Overall Performance Metrics</b>", template="plotly_white", height=600)

    # --- 模块 B: 缓存占用 vs. 延迟 (你新加的图) ---
    fig_policy = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.08,
        subplot_titles=[f"<b>Policy: {p}</b> (Usage vs. Latency Distribution)" for p in policies],
        specs=[[{"secondary_y": True}], [{"secondary_y": True}], [{"secondary_y": True}]]
    )
    for i, p in enumerate(policies):
        if p not in data: continue
        df = pd.DataFrame(data[p].get("requests", []))
        df["UsagePct"] = df["cache_usage_float"].astype(float) * 100
        df["Latency"] = df["latency_ms"].astype(float)
        
        # 直方图
        fig_policy.add_trace(go.Histogram(
            x=df["UsagePct"], name=f"{p} Usage Dist", xbins=dict(start=0, end=100, size=5),
            marker_color=policy_colors[p], opacity=0.3, legendgroup=p, showlegend=False
        ), row=i+1, col=1, secondary_y=False)
        
        # 延迟均值线
        bins = np.arange(0, 105, 5)
        df['bin'] = pd.cut(df['UsagePct'], bins=bins, labels=bins[:-1] + 2.5)
        bin_means = df.groupby('bin', observed=True)['Latency'].mean().reset_index()
        fig_policy.add_trace(go.Scatter(
            x=bin_means['bin'], y=bin_means['Latency'], name=f"{p} Latency Trend",
            mode='lines+markers', line=dict(color=policy_colors[p], width=2.5),
            legendgroup=p, showlegend=True if i == 0 else False
        ), row=i+1, col=1, secondary_y=True)
    fig_policy.update_layout(title="<b>Section 2: Latency Sensitivity to Cache Usage</b>", height=800, template="plotly_white")

    # --- 模块 C: 时序动态演变 ---
    fig_temp = make_subplots(specs=[[{"secondary_y": True}]])
    for p in policies:
        if p in data:
            df_p = pd.DataFrame(data[p].get("requests", []))
            fig_temp.add_trace(go.Scatter(y=df_p["cache_usage_float"].astype(float)*100, name=f"{p} Usage",
                                          line=dict(color=policy_colors[p], width=1), opacity=0.4, legendgroup=p), secondary_y=False)
            fig_temp.add_trace(go.Scatter(y=df_p["latency_ms"].rolling(20).mean(), name=f"{p} Latency (MA20)",
                                          line=dict(color=policy_colors[p], width=2), legendgroup=p), secondary_y=True)
    fig_temp.update_layout(title="<b>Section 3: Temporal Performance Flow</b>", template="plotly_white", height=500, hovermode="x unified")

    # --- 模块 D: 延迟直方图 (P99) ---
    fig_dist = make_subplots(rows=3, cols=1, subplot_titles=[f"<b>{p}</b> Latency Tail" for p in policies], vertical_spacing=0.1)
    for i, p in enumerate(policies):
        if p in data:
            lats = [float(r["latency_ms"]) for r in data[p].get("requests", []) if r.get("status_code") == 200]
            p99 = np.percentile(lats, 99)
            fig_dist.add_trace(go.Histogram(x=lats, nbinsx=100, marker_color=policy_colors[p], opacity=0.6, showlegend=False), row=i+1, col=1)
            fig_dist.add_vline(x=p99, line_dash="dash", line_color="red", annotation_text=f"P99:{int(p99)}ms", row=i+1, col=1)
    fig_dist.update_layout(title="<b>Section 4: Tail Latency Analysis (P99)</b>", height=800, template="plotly_white")

    # --- 导出 HTML ---
    with open("integrated_report_1.1.html", "w", encoding="utf-8") as f:
        f.write(f"<html><head><meta charset='utf-8'/><title>1.1 Report</title></head>")
        f.write("<body style='background:#f0f2f5; font-family:sans-serif; padding:20px;'>")
        f.write("<div style='max-width:1100px; margin:auto; background:white; padding:40px; border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.08);'>")
        f.write(f"<h1 style='text-align:center; color:#1a1a1a;'>{exp_title}</h1>")
        
        for fig in [fig_sum, fig_policy, fig_temp, fig_dist]:
            f.write(pio.to_html(fig, full_html=False, include_plotlyjs='cdn'))
            f.write("<hr style='border:0; height:1px; background:#eee; margin:50px 0;'>")
        
        f.write("</div></body></html>")
    print("✓ Integrated report for 1.1 generated: integrated_report_1.1.html")

if __name__ == "__main__":
    generate_report_1_1()