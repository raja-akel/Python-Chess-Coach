"""
Chess statistics dashboard built with Streamlit.

Run from the project directory:
    streamlit run chess_dashboard.py
"""

from pathlib import Path
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from my_functions import import_games, add_opening_group


# ----------------------------- Configuration -----------------------------
st.set_page_config(
    page_title="Chess Statistics",
    page_icon="♟️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / "parameters.env")
USERNAME = os.getenv("USERTAG", "").strip()
DEFAULT_START_DATE = pd.Timestamp("2025-02-28")


# ------------------------------- Data layer ------------------------------
@st.cache_data(show_spinner="Loading and processing your games…")
def load_game_data(username: str, pgn_path: str, file_mtime: float):
    """Load PGN games and derive the data used by all dashboard tabs."""
    games = import_games(pgn_path)
    if not games:
        raise ValueError("No games were found in the PGN file.")

    opening_names = {}
    for game_id, game in games.items():
        eco = game.get("ECO")
        eco_url = game.get("ECOUrl", "")
        if not eco:
            continue
        if eco not in opening_names:
            opening_names[eco] = (
                eco_url.rstrip("/").split("/")[-1].replace("-", " ")
                if eco_url
                else str(eco)
            )
        game["Opening"] = opening_names[eco]

    games_df = pd.DataFrame.from_dict(games, orient="index")
    if "Variant" in games_df.columns:
        games_df = games_df[games_df["Variant"].isna()].copy()

    if "EndDate" not in games_df.columns:
        raise ValueError("The PGN data does not contain an EndDate field.")

    games_df["EndDate"] = pd.to_datetime(games_df["EndDate"], errors="coerce")
    games_df = games_df.dropna(subset=["EndDate"])
    games_df = games_df[games_df["EndDate"] > DEFAULT_START_DATE].copy()

    if "TimeControl" in games_df.columns:
        games_df = games_df[
            ~games_df["TimeControl"].fillna("").astype(str).str.startswith("1/")
        ].copy()

    for col in ("WhiteElo", "BlackElo"):
        games_df[col] = pd.to_numeric(games_df[col], errors="coerce")
    games_df = games_df.dropna(subset=["WhiteElo", "BlackElo"])

    games_df["isWhite"] = games_df["White"].eq(username)
    games_df["isBlack"] = games_df["Black"].eq(username)
    games_df["UserColor"] = games_df["isWhite"].map({True: "White", False: "Black"})

    result = games_df["Result"].astype(str)
    games_df["RelativeResult"] = "Other"
    games_df.loc[
        result.eq("1-0") & games_df["isWhite"]
        | result.eq("0-1") & games_df["isBlack"],
        "RelativeResult",
    ] = "Win"
    games_df.loc[
        result.eq("1-0") & games_df["isBlack"]
        | result.eq("0-1") & games_df["isWhite"],
        "RelativeResult",
    ] = "Loss"
    games_df.loc[result.eq("1/2-1/2"), "RelativeResult"] = "Tie"
    games_df["RelativeEloDiff"] = (
        (games_df["WhiteElo"] - games_df["BlackElo"])
        * games_df["isBlack"].astype(int)
        + (games_df["BlackElo"] - games_df["WhiteElo"])
        * games_df["isWhite"].astype(int)
    )
    games_df["Opponent"] = games_df.apply(
        lambda row: row["Black"] if row["isWhite"] else row["White"], axis=1
    )

    games_df = add_opening_group(games_df)
    games_df = games_df.loc[:, ~games_df.columns.duplicated()]
    drop_cols = [
        "Site", "Event", "Round", "Link", "Termination", "ECOUrl", "SetUp",
        "StartTime", "EndTime", "UTCTime", "UTCDate", "Timezone", "ECO",
        "FEN", "Variant", "CurrentPosition", "game_pgn",
    ]
    games_df = games_df.drop(columns=drop_cols, errors="ignore")
    games_df = games_df.drop_duplicates().sort_values("EndDate")
    games_df = games_df.set_index("EndDate")
    return games_df


def result_counts(df: pd.DataFrame) -> dict:
    counts = df["RelativeResult"].value_counts()
    return {name: int(counts.get(name, 0)) for name in ["Win", "Loss", "Tie"]}


def monthly_results(df: pd.DataFrame, color: str | None = None) -> pd.DataFrame:
    subset = df if color is None else df[df["UserColor"] == color]
    out = (
        subset.assign(Month=subset.index.to_period("M").astype(str))
        .groupby(["Month", "RelativeResult"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=["Win", "Loss", "Tie"], fill_value=0)
        .sort_index()
    )
    out["Winrate"] = out["Win"] / (out["Win"] + out["Loss"]).replace(0, pd.NA)
    return out.reset_index()


def monthly_openings(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.assign(Month=df.index.to_period("M").astype(str))
        .groupby(["Month", "Opening_Group"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )


def make_opening_winrate(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    temp = df.reset_index().copy()
    temp["Quarter"] = temp["EndDate"].dt.to_period("Q").astype(str)
    top_openings = temp["Opening_Group"].value_counts().head(top_n).index
    temp = temp[temp["Opening_Group"].isin(top_openings)]
    counts = (
        temp.groupby(["Opening_Group", "Quarter", "RelativeResult"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=["Win", "Loss", "Tie"], fill_value=0)
        .reset_index()
    )
    counts["Winrate"] = counts["Win"] / (counts["Win"] + counts["Loss"]).replace(0, pd.NA)
    return counts


# --------------------------------- App ------------------------------------
st.title("♟️ Chess Statistics")
st.caption("A personal performance dashboard built from your PGN game archive.")

if not USERNAME:
    st.error("No chess username configured. Add USER=<your_username> to parameters.env.")
    st.stop()

pgn_file = BASE_DIR / f"{USERNAME}_all_games.pgn"
if not pgn_file.exists():
    st.error(f"Could not find the PGN file: {pgn_file.name}")
    st.info("Place your exported PGN file next to this script, or update the path in the script.")
    st.stop()

with st.sidebar:
    st.header("Dashboard settings")
    st.write(f"**Player:** {USERNAME}")
    start_date = st.date_input(
        "Games from",
        value=DEFAULT_START_DATE.date(),
        help="The notebook originally excluded games on or before 28 February 2025.",
    )
    min_games_opponent = st.slider("Minimum games vs. opponent", 1, 30, 10)
    top_n_openings = st.slider("Opening groups to compare", 3, 15, 10)
    if st.button("Reload data", use_container_width=True):
        load_game_data.clear()

try:
    games_df = load_game_data(USERNAME, str(pgn_file), pgn_file.stat().st_mtime)
except Exception as exc:
    st.error("The games could not be processed.")
    st.exception(exc)
    st.stop()

games_df = games_df.loc[games_df.index >= pd.Timestamp(start_date)].copy()
if games_df.empty:
    st.warning("No games match the selected date range.")
    st.stop()

counts = result_counts(games_df)
decisive = counts["Win"] + counts["Loss"]
winrate = counts["Win"] / decisive if decisive else 0.0
total_games = len(games_df)
average_elo_diff = games_df["RelativeEloDiff"].mean()

tab_overview, tab_results, tab_openings, tab_opponents, tab_data = st.tabs(
    ["Overview", "Results over time", "Opening analysis", "Opponents", "Game data"]
)

# Overview
with tab_overview:
    st.subheader("Performance at a glance")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Games", f"{total_games:,}")
    c2.metric("Wins", f"{counts['Win']:,}")
    c3.metric("Losses", f"{counts['Loss']:,}")
    c4.metric("Draws", f"{counts['Tie']:,}")
    c5.metric("Win rate", f"{winrate:.1%}", help="Wins divided by decisive games; draws excluded.")

    left, right = st.columns([1, 1])
    with left:
        result_df = pd.DataFrame({"Result": ["Wins", "Losses", "Draws"],
                                  "Games": [counts["Win"], counts["Loss"], counts["Tie"]]})
        fig = px.pie(result_df, names="Result", values="Games", hole=0.58,
                     title="Result distribution")
        fig.update_layout(legend_title_text="")
        st.plotly_chart(fig, use_container_width=True)
    with right:
        trend = monthly_results(games_df)
        fig = go.Figure()
        for col, label in [("Win", "Wins"), ("Loss", "Losses"), ("Tie", "Draws")]:
            fig.add_trace(go.Bar(x=trend["Month"], y=trend[col], name=label))
        fig.update_layout(title="Games played per month", barmode="stack",
                          xaxis_title="", yaxis_title="Games")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Recent games")
    display_cols = [c for c in ["White", "Black", "Result", "RelativeResult", "Opening",
                                "Opening_Group", "WhiteElo", "BlackElo", "Opponent"]
                    if c in games_df.columns]
    st.dataframe(games_df[display_cols].sort_index(ascending=False).head(15),
                 use_container_width=True)

# Results over time
with tab_results:
    st.subheader("Win rate over time")
    result_by_month = monthly_results(games_df)
    fig = px.line(result_by_month, x="Month", y="Winrate", markers=True,
                  title="Monthly win rate (draws excluded)")
    fig.add_hline(y=0.5, line_dash="dash", line_color="gray",
                  annotation_text="50% reference")
    fig.update_yaxes(tickformat=".0%", range=[0, 1])
    fig.update_layout(xaxis_title="", yaxis_title="Win rate")
    st.plotly_chart(fig, use_container_width=True)

    color_col1, color_col2 = st.columns(2)
    for color, container in [("White", color_col1), ("Black", color_col2)]:
        with container:
            color_monthly = monthly_results(games_df, color=color)
            fig = px.line(color_monthly, x="Month", y="Winrate", markers=True,
                          title=f"Win rate playing {color.lower()}")
            fig.add_hline(y=0.5, line_dash="dash", line_color="gray")
            fig.update_yaxes(tickformat=".0%", range=[0, 1])
            fig.update_layout(xaxis_title="", yaxis_title="Win rate")
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("Games by result per month")
    result_long = result_by_month.melt(
        id_vars="Month", value_vars=["Win", "Loss", "Tie"],
        var_name="Result", value_name="Games"
    )
    fig = px.bar(result_long, x="Month", y="Games", color="Result", barmode="stack")
    fig.update_layout(xaxis_title="", yaxis_title="Games")
    st.plotly_chart(fig, use_container_width=True)

# Opening analysis
with tab_openings:
    st.subheader("Most-played opening groups")
    if "Opening_Group" not in games_df.columns:
        st.warning("The opening-group field was not produced by add_opening_group().")
    else:
        opening_counts = games_df["Opening_Group"].value_counts().head(15).rename_axis(
            "Opening group"
        ).reset_index(name="Games")
        fig = px.bar(opening_counts.sort_values("Games"), x="Games", y="Opening group",
                     orientation="h", title="Top opening groups")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Opening win rates by quarter")
        opening_rates = make_opening_winrate(games_df, top_n=top_n_openings)
        if not opening_rates.empty:
            fig = px.line(opening_rates, x="Quarter", y="Winrate", color="Opening_Group",
                          markers=True, title=f"Win rate across the top {top_n_openings} openings")
            fig.add_hline(y=0.5, line_dash="dash", line_color="gray")
            fig.update_yaxes(tickformat=".0%", range=[0, 1])
            fig.update_layout(xaxis_title="", yaxis_title="Win rate",
                              legend_title_text="Opening group")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Opening usage over time")
        usage = monthly_openings(games_df)
        top_usage = usage.sum().nlargest(top_n_openings).index
        usage = usage.loc[:, usage.columns.isin(top_usage)]
        if not usage.empty:
            fig = px.line(usage, x=usage.index, y=usage.columns,
                          title="Monthly games by opening group")
            fig.update_layout(xaxis_title="Month", yaxis_title="Games",
                              legend_title_text="Opening group")
            st.plotly_chart(fig, use_container_width=True)

        white, black = st.columns(2)
        for color, container in [("White", white), ("Black", black)]:
            with container:
                subset = games_df[games_df["UserColor"] == color]
                counts_by_opening = subset["Opening_Group"].value_counts().head(5)
                fig = px.bar(counts_by_opening.sort_values(), orientation="h",
                             title=f"Top openings playing {color.lower()}",
                             labels={"value": "Games", "index": "Opening group"})
                st.plotly_chart(fig, use_container_width=True)

# Opponents
with tab_opponents:
    st.subheader("Results against frequent opponents")
    opponent_summary = (
        games_df.groupby(["Opponent", "RelativeResult"]).size()
        .unstack(fill_value=0)
        .reindex(columns=["Win", "Loss", "Tie"], fill_value=0)
    )
    opponent_summary["Total games"] = opponent_summary[["Win", "Loss", "Tie"]].sum(axis=1)
    opponent_summary = opponent_summary[opponent_summary["Total games"] >= min_games_opponent]
    opponent_summary = opponent_summary.sort_values("Total games", ascending=False)
    if opponent_summary.empty:
        st.info("No opponents meet the selected minimum-games threshold.")
    else:
        opponent_summary["Win rate"] = (
            opponent_summary["Win"] /
            (opponent_summary["Win"] + opponent_summary["Loss"]).replace(0, pd.NA)
        )
        top_opponents = opponent_summary.head(25).reset_index()
        fig = px.bar(top_opponents, x="Opponent", y=["Win", "Loss", "Tie"],
                     title=f"Results against top opponents (minimum {min_games_opponent} games)",
                     barmode="group")
        fig.update_layout(xaxis_title="Opponent", yaxis_title="Games")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(opponent_summary, use_container_width=True)

# Data and downloads
with tab_data:
    st.subheader("Processed game data")
    st.caption("Use the filters and downloads below to inspect or export the processed dataset.")
    result_filter = st.multiselect(
        "Filter by result", options=["Win", "Loss", "Tie", "Other"],
        default=["Win", "Loss", "Tie"]
    )
    filtered_df = games_df[games_df["RelativeResult"].isin(result_filter)]
    st.dataframe(filtered_df.sort_index(ascending=False), use_container_width=True,
                 height=450)
    st.download_button(
        "Download processed games (CSV)",
        data=filtered_df.to_csv(index=True).encode("utf-8"),
        file_name="mygames_dataframe.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.download_button(
        "Download opponent summary (CSV)",
        data=opponent_summary.to_csv(index=True).encode("utf-8"),
        file_name="opponent_summary.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.download_button(
        "Download opening usage (CSV)",
        data=monthly_openings(games_df).to_csv(index=True).encode("utf-8"),
        file_name="monthly_openings.csv",
        mime="text/csv",
        use_container_width=True,
    )
