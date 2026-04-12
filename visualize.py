import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

with open("experiment_results.json", "r") as f:
    data = json.load(f)

summary_list = []
all_reqs = []

for policy, content in data.items():
    s = content["stats"]
    origin_bytes = s["bytes_fetched_from_origin"]
    efficiency = s["bytes_served_from_cache"] / origin_bytes if origin_bytes > 0 else 0
    
    summary_list.append({
        "Policy": policy,
        "Hit Rate": round(s["hit_rate"] * 100, 2),
        "Origin Fetches": s["origin_fetches"],
        "Efficiency": round(efficiency, 2)
    })
    
    for req in content["requests"]:
        all_reqs.append({
            "Policy": policy,
            "Latency": float(req["latency_ms"]),
            "Cache": req["cache"],
            "Reason": req["reason"],
            "File": req["file"]
        })

df_sum = pd.DataFrame(summary_list)
df_req = pd.DataFrame(all_reqs)

fig = make_subplots(
    rows=3, cols=3,
    row_heights=[0.30, 0.40, 0.3], 
    subplot_titles=(
        "Core Metrics: Hit Rate (%) & Origin Fetches", 
        "Cache Efficiency Ratio ", 
        "Miss Count Distribution per File",
        "Latency CDF ", 
        "Latency Box Plot ", 
        "LRU Miss Reason Breakdown", 
        "LFU Miss Reason Breakdown", 
        "TTL Miss Reason Breakdown"
    ),
    specs=[
        [{"secondary_y": True}, {"type": "xy"}, {"type": "xy"}],
        [{"colspan": 2}, None, {"type": "xy"}], 
        [{"type": "domain"}, {"type": "domain"}, {"type": "domain"}]
    ],
    vertical_spacing=0.1,
    horizontal_spacing=0.06
)

fig.add_trace(go.Bar(
    x=df_sum["Policy"], 
    y=df_sum["Hit Rate"], 
    name="Hit Rate (%)",
    text=df_sum["Hit Rate"], 
    textposition='outside'
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=df_sum["Policy"], 
    y=df_sum["Origin Fetches"], 
    name="Origin Fetches",
    mode='lines+markers+text', 
    text=df_sum["Origin Fetches"], 
    textposition='top center'
), row=1, col=1, secondary_y=True)

fig.add_trace(go.Bar(
    x=df_sum["Policy"], 
    y=df_sum["Efficiency"], 
    name="Efficiency",
    text=df_sum["Efficiency"], 
    textposition='outside', 
    marker_color='mediumpurple'
), row=1, col=2)

for filename in df_req["File"].unique():
    f_miss = df_req[(df_req["Cache"]=="MISS") & (df_req["File"]==filename)].groupby("Policy").size().reset_index(name="counts")
    fig.add_trace(go.Bar(
        x=f_miss["Policy"], 
        y=f_miss["counts"], 
        name=f"Miss: {filename}",
        text=f_miss["counts"], 
        textposition='inside'
    ), row=1, col=3)

for policy in df_sum["Policy"]:
    sorted_latency = np.sort(df_req[df_req["Policy"]==policy]["Latency"])
    y_vals = np.arange(len(sorted_latency)) / float(len(sorted_latency) - 1)
    fig.add_trace(go.Scatter(
        x=sorted_latency, 
        y=y_vals, 
        name=f"CDF: {policy}", 
        mode='lines'
    ), row=2, col=1)

for policy in df_sum["Policy"]:
    fig.add_trace(go.Box(
        y=df_req[df_req["Policy"]==policy]["Latency"], 
        name=policy, 
        boxmean='sd'
    ), row=2, col=3)

for i, policy in enumerate(["LRU", "LFU", "TTL"]):
    p_reasons = df_req[(df_req["Policy"] == policy) & (df_req["Cache"] == "MISS")]["Reason"].value_counts()
    fig.add_trace(go.Pie(
        labels=p_reasons.index, 
        values=p_reasons.values, 
        hole=.3, 
        title=f"<b>{policy}</b>", 
        textinfo='label+percent',
        textposition='inside',
        showlegend=False
    ), row=3, col=i+1)

fig.update_layout(
    height=2100, width=1950, 
    title_text="<b>Edge Cache Proxy Experimental Analysis Report</b>",
    title_font_size=24,
    showlegend=True, 
    barmode='stack',
    template="plotly_white"
)

fig.update_xaxes(title_text="Latency (ms)", row=2, col=1, gridcolor='lightgrey')
fig.update_yaxes(title_text="Cumulative Probability", row=2, col=1, gridcolor='lightgrey')
fig.update_yaxes(title_text="Latency (ms)", row=2, col=3, gridcolor='lightgrey')

fig.show()
fig.write_html("cache_report.html")