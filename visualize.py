import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. 加载数据
with open("experiment_results.json", "r") as f:
    data = json.load(f)

summary_list = []
all_reqs = []

# 数据预处理
for policy, content in data.items():
    s = content.get("stats", {})
    origin_bytes = s.get("bytes_fetched_from_origin", 0)
    efficiency = s.get("bytes_served_from_cache", 0) / origin_bytes if origin_bytes > 0 else 0
    
    summary_list.append({
        "Policy": policy,
        "Hit Rate": round(s.get("hit_rate", 0) * 100, 2),
        "Origin Fetches": s.get("origin_fetches", 0),
        "Efficiency": round(efficiency, 2)
    })
    
    # 提取请求明细，增加时序索引
    for idx, req in enumerate(content.get("requests", [])):
        is_success = req.get("status_code") == 200
        all_reqs.append({
            "Policy": policy,
            "RequestIdx": idx,
            "ClientLatency": float(req.get("latency_ms", 0)),
            "ProxyLatency": float(req.get("response_time_ms", 0)),
            "OriginLatency": float(req.get("origin_latency_ms", 0)),
            "Status": "SUCCESS" if is_success else "FAILURE",
            "Cache": req.get("cache", "ERROR"),
            "Reason": req.get("cache_reason", "unknown"),
            "File": req.get("file", "unknown"),
            "UsagePct": float(req.get("cache_usage_float", 0)) * 100
        })

df_sum = pd.DataFrame(summary_list)
df_req = pd.DataFrame(all_reqs)

# --- 2. 创建画布 (扩展至 6 行) ---
fig = make_subplots(
    rows=6, cols=3,
    row_heights=[0.15, 0.15, 0.15, 0.15, 0.2, 0.2], 
    subplot_titles=(
        "Core Metrics: Hit Rate & Origin Fetches", "Cache Efficiency Ratio", "Request Success Rate", 
        "Latency CDF (Client Perspective)", "Proxy Internal Latency (Box)", "AWS Origin Latency (Box)",
        "Miss Distribution by File Type", "", "",
        "LRU Miss Reasons", "LFU Miss Reasons", "TTL Miss Reasons",
        "Temporal Comparison: Cache Usage Evolution (%)", "", "",
        "Temporal Comparison: Latency Trend (ms) - Moving Average", "", ""
    ),
    specs=[
        [{"secondary_y": True}, {"type": "xy"}, {"type": "xy"}], 
        [{"type": "xy"}, {"type": "xy"}, {"type": "xy"}],        
        [{"colspan": 3}, None, None],                           
        [{"type": "domain"}, {"type": "domain"}, {"type": "domain"}],
        [{"colspan": 3}, None, None], # Usage 演进图
        [{"colspan": 3}, None, None]  # Latency 演进图
    ],
    vertical_spacing=0.05,
    horizontal_spacing=0.06
)

# --- 颜色定义 ---
policy_colors = {"LRU": "#636EFA", "LFU": "#EF553B", "TTL": "#00CC96"}

# --- [Row 1-4] 原有统计图表 ---
fig.add_trace(go.Bar(x=df_sum["Policy"], y=df_sum["Hit Rate"], name="Hit Rate (%)", marker_color='indianred'), row=1, col=1)
fig.add_trace(go.Scatter(x=df_sum["Policy"], y=df_sum["Origin Fetches"], name="Origin Fetches", mode='lines+markers'), row=1, col=1, secondary_y=True)
fig.add_trace(go.Bar(x=df_sum["Policy"], y=df_sum["Efficiency"], name="Byte Efficiency", marker_color='mediumpurple'), row=1, col=2)

for status, color in zip(["SUCCESS", "FAILURE"], ['green', 'red']):
    status_df = df_req[df_req["Status"] == status].groupby("Policy").size().reset_index(name="count")
    fig.add_trace(go.Bar(x=status_df["Policy"], y=status_df["count"], name=status, marker_color=color, showlegend=False), row=1, col=3)

success_reqs = df_req[df_req["Status"] == "SUCCESS"]
for policy in df_sum["Policy"]:
    p_lat = success_reqs[success_reqs["Policy"] == policy]["ClientLatency"]
    if not p_lat.empty:
        sorted_val = np.sort(p_lat)
        y_vals = np.arange(len(sorted_val)) / float(len(sorted_val))
        fig.add_trace(go.Scatter(x=sorted_val, y=y_vals, name=f"CDF: {policy}", line=dict(color=policy_colors.get(policy))), row=2, col=1)
    fig.add_trace(go.Box(y=success_reqs[success_reqs["Policy"] == policy]["ProxyLatency"], name=f"Proxy:{policy}", marker_color=policy_colors.get(policy)), row=2, col=2)

origin_data = success_reqs[success_reqs["OriginLatency"] > 0]
for policy in df_sum["Policy"]:
    fig.add_trace(go.Box(y=origin_data[origin_data["Policy"] == policy]["OriginLatency"], name=f"AWS:{policy}", marker_color=policy_colors.get(policy)), row=2, col=3)

def get_file_type(filename):
    for t in ['small', 'medium', 'large']: 
        if t in filename.lower(): return t.capitalize()
    return 'Other'

df_req['FileType'] = df_req['File'].apply(get_file_type)
type_miss = df_req[df_req["Cache"] == "MISS"].groupby(["Policy", "FileType"]).size().reset_index(name="counts")
for f_type in ['Small', 'Medium', 'Large']:
    subset = type_miss[type_miss["FileType"] == f_type]
    fig.add_trace(go.Bar(x=subset["Policy"], y=subset["counts"], name=f_type), row=3, col=1)

for i, policy in enumerate(["LRU", "LFU", "TTL"]):
    p_miss = df_req[(df_req["Policy"] == policy) & (df_req["Cache"] == "MISS")]
    if not p_miss.empty:
        reasons = p_miss["Reason"].value_counts()
        fig.add_trace(go.Pie(labels=reasons.index, values=reasons.values, hole=.3, title=policy), row=4, col=i+1)

# --- [Row 5-6] 新增：时序对比演进图 ---
for policy in df_sum["Policy"]:
    p_df = df_req[df_req["Policy"] == policy].sort_values("RequestIdx")
    color = policy_colors.get(policy)
    
    # Usage 演进 (Row 5)
    fig.add_trace(go.Scatter(x=p_df["RequestIdx"], y=p_df["UsagePct"], name=f"{policy} Usage Evolution",
                             mode='lines', line=dict(color=color, width=2), legendgroup=policy), row=5, col=1)
    
    # Latency 趋势 (Row 6) - 20点移动平均
    ma_latency = p_df["ClientLatency"].rolling(window=20, min_periods=1).mean()
    fig.add_trace(go.Scatter(x=p_df["RequestIdx"], y=ma_latency, name=f"{policy} Latency Trend",
                             mode='lines', line=dict(color=color, width=3), legendgroup=policy), row=6, col=1)

# --- 布局优化 ---
fig.update_layout(
    height=2400, width=1300, 
    title_text="<b>Edge Cache Proxy: Comprehensive Experimental Report</b>",
    title_x=0.5,
    template="plotly_white",
    barmode='stack',
    hovermode="x unified"
)

fig.update_xaxes(title_text="Request Sequence", row=5, col=1)
fig.update_xaxes(title_text="Request Sequence", row=6, col=1)
fig.update_yaxes(title_text="Usage %", row=5, col=1)
fig.update_yaxes(title_text="Latency (ms)", row=6, col=1)

fig.show()
fig.write_html("full_cache_analysis.html")