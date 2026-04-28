from __future__ import annotations

from importlib import import_module
from typing import Any

import pandas as pd

                          
px: Any = import_module("plotly.express")

def chart_html(fig: Any) -> str:
    fig.update_layout(
        margin=dict(l=24, r=24, t=36, b=24),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        config={"displayModeBar": False, "responsive": True},
    )

def timeline_chart(appointments: list[dict[str, Any]]) -> str | None:
    if not appointments:
        return None
    
    frame = pd.DataFrame(appointments)
    frame["slot_start"] = pd.to_datetime(frame["slot_start"])
    frame["slot_end"] = pd.to_datetime(frame["slot_end"])
    frame["Task"] = frame["pet_name"] + " | " + frame["service_name"]
    
    fig = px.timeline(
        frame,
        x_start="slot_start",
        x_end="slot_end",
        y="Task",
        color="status",
        color_discrete_map={
            "confirmed": "#1f7a6b",
            "completed": "#0f9d58",
            "cancelled": "#c2410c",
            "pending": "#c18b00",
            "rescheduled": "#005f73",
            "no_show": "#8b1e3f",
        },
    )
    fig.update_layout(height=360)
    return chart_html(fig)

def bar_chart(
    data: list[dict[str, Any]],
    x: str,
    y: str,
    color_scale: str = "Teal",
    orientation: str = "v",
) -> str | None:
    if not data:
        return None
    
    frame = pd.DataFrame(data)
    fig = px.bar(
        frame,
        x=x,
        y=y,
        color=x if orientation == "h" else y,
        orientation=orientation,
        color_continuous_scale=color_scale,
        text_auto=True,
    )
    fig.update_layout(height=340, coloraxis_showscale=False, showlegend=False)
    return chart_html(fig)

def line_chart(data: list[dict[str, Any]], x: str, y: str) -> str | None:
    if not data:
        return None
    
    frame = pd.DataFrame(data)
    fig = px.line(frame, x=x, y=y, markers=True, color_discrete_sequence=["#1f7a6b"])
    fig.update_layout(height=320, showlegend=False)
    return chart_html(fig)
