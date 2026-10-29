"""
Chess statistics dashboard built with Streamlit.

Run from the project directory:
    streamlit run chess_statistics_dashboard.py
"""

from pathlib import Path
import math
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from dotenv import load_dotenv

from my_functions import (
    import_games,
    add_opening_group,
    load_opponent_countries,
    add_opponent_countries,
)


# ----------------------------- Configuration -----------------------------
st.set_page_config(
    page_title="Chess Statistics",
    page_icon="♟️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
load_dotenv(BASE_DIR / "parameters.env")
USERNAME = os.getenv("USERTAG", "").strip()
DEFAULT_START_DATE = pd.Timestamp("2025-02-28")

# Opponent profiles live in data/; the project root is the old location.
PROFILES_PATHS = [DATA_DIR / "opponent_countries.json", BASE_DIR / "opponent_countries.json"]
ISO_PATH = DATA_DIR / "ISO_countries.csv"

RESULTS = ["Win", "Loss", "Tie"]
RESULT_COLORS = {"Win": "#2e7d32", "Loss": "#c62828", "Tie": "#9e9e9e"}
# Readable on both Streamlit's light and dark themes (a literal black line disappears on dark).
SIDE_COLORS = {"Overall": "#1e88e5", "White": "#d4a72c", "Black": "#8e6bd8"}
TIME_CLASSES = ["Bullet", "Blitz", "Rapid"]
UNKNOWN_REGION = "Unknown"


# ------------------------------- Data layer ------------------------------
def time_class(time_control: str) -> str:
    """Classify a chess.com TimeControl string ("180", "180+2") the way chess.com does."""
    try:
        base, _, increment = str(time_control).partition("+")
        estimated = int(base) + 40 * int(increment or 0)
    except ValueError:
        return "Other"
    if estimated < 180:
        return "Bullet"
    if estimated < 600:
        return "Blitz"
    return "Rapid"


@st.cache_data(show_spinner="Loading and processing your games…")
def load_game_data(username: str, pgn_path: str, file_mtime: float,
                   profiles_path: str | None, profiles_mtime: float | None):
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
        games_df["TimeClass"] = games_df["TimeControl"].map(time_class)

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

    # Usernames are case-insensitive on chess.com; the profile cache is keyed in lowercase.
    for col in ("Opponent", "White", "Black"):
        games_df[col] = games_df[col].str.lower()

    if profiles_path and ISO_PATH.exists():
        countries = load_opponent_countries(profiles_path, ISO_PATH)
        games_df = add_opponent_countries(games_df, countries)
    else:
        for col in ("Country", "Region", "Subregion", "CountryISO3"):
            games_df[col] = pd.NA
    games_df["Region"] = games_df["Region"].fillna(UNKNOWN_REGION)
    return games_df


def result_counts(df: pd.DataFrame) -> dict:
    counts = df["RelativeResult"].value_counts()
    return {name: int(counts.get(name, 0)) for name in RESULTS}


def add_winrate(df: pd.DataFrame) -> pd.DataFrame:
    """Win rate = wins / decisive games (draws excluded), as in the notebook."""
    df["Total"] = df[RESULTS].sum(axis=1)
    decisive = (df["Win"] + df["Loss"]).astype(float)
    df["Winrate"] = df["Win"] / decisive.where(decisive > 0)
    return df


def results_by(df: pd.DataFrame, keys) -> pd.DataFrame:
    out = (
        df.groupby(keys)["RelativeResult"].value_counts()
        .unstack(fill_value=0)
        .reindex(columns=RESULTS, fill_value=0)
    )
    out.columns.name = None
    return add_winrate(out).reset_index()


def monthly_results(df: pd.DataFrame, color: str | None = None) -> pd.DataFrame:
    subset = df if color is None else df[df["UserColor"] == color]
    return results_by(subset.assign(Month=subset.index.to_period("M").astype(str)), "Month")


def monthly_openings(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.assign(Month=df.index.to_period("M").astype(str))
        .groupby(["Month", "Opening_Group"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )


def top_openings(df: pd.DataFrame, top_n: int) -> pd.Index:
    return df["Opening_Group"].value_counts().head(top_n).index


def make_opening_winrate(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    temp = df[df["Opening_Group"].isin(top_openings(df, top_n))]
    temp = temp.assign(Quarter=temp.index.to_period("Q").astype(str))
    return results_by(temp, ["Opening_Group", "Quarter"])


def opening_color_map(groups) -> dict:
    """Give every opening group a fixed color so it reads the same in every chart."""
    palette = px.colors.qualitative.Alphabet + px.colors.qualitative.Dark24
    named = sorted(g for g in groups if g not in ("Other", "Unknown"))
    colors = {group: palette[i % len(palette)] for i, group in enumerate(named)}
    colors.update({"Other": "#7f7f7f", "Unknown": "#c7c7c7"})
    return colors


def opening_lines(usage: pd.DataFrame, title: str) -> go.Figure:
    fig = px.line(usage, x=usage.index, y=usage.columns, title=title,
                  color_discrete_map=OPENING_COLORS)
    fig.update_layout(xaxis_title="Month", yaxis_title="Games",
                      legend_title_text="Opening group")
    return fig


# --------------------------------- App ------------------------------------
st.title("♟️ Chess Statistics")
st.caption("A personal performance dashboard built from your PGN game archive.")

if not USERNAME:
    st.error("No chess username configured. Add USERTAG=<your_username> to parameters.env.")
    st.stop()

pgn_file = BASE_DIR / f"{USERNAME}_all_games.pgn"
if not pgn_file.exists():
    st.error(f"Could not find the PGN file: {pgn_file.name}")
    st.info("Place your exported PGN file next to this script, or update the path in the script.")
    st.stop()

profiles_file = next((p for p in PROFILES_PATHS if p.exists()), None)

try:
    all_games_df = load_game_data(
        USERNAME, str(pgn_file), pgn_file.stat().st_mtime,
        str(profiles_file) if profiles_file else None,
        profiles_file.stat().st_mtime if profiles_file else None,
    )
except Exception as exc:
    st.error("The games could not be processed.")
    st.exception(exc)
    st.stop()

OPENING_COLORS = opening_color_map(all_games_df["Opening_Group"].unique())
has_countries = all_games_df["Country"].notna().any()

with st.sidebar:
    st.header("Filters")
    st.write(f"**Player:** {USERNAME}")

    first_day = all_games_df.index.min().date()
    last_day = all_games_df.index.max().date()
    date_range = st.slider("Date range", min_value=first_day, max_value=last_day,
                           value=(first_day, last_day), format="MMM YYYY")

    side = st.radio("Playing as", ["Both", "White", "Black"], horizontal=True)

    available_classes = [c for c in TIME_CLASSES if c in set(all_games_df.get("TimeClass", []))]
    time_classes = st.multiselect("Time control", available_classes, default=available_classes)

    regions = sorted(all_games_df["Region"].unique(), key=lambda r: (r == UNKNOWN_REGION, r))
    selected_regions = st.multiselect("Opponent region", regions, default=regions,
                                      disabled=not has_countries)

    st.header("Settings")
    min_games_opponent = st.slider("Minimum games vs. opponent", 1, 30, 10)
    min_games_country = st.slider("Minimum games per country", 1, 50, 10)
    top_n_openings = st.slider("Opening groups to compare", 3, 15, 10)
    if st.button("Reload data", width="stretch"):
        load_game_data.clear()

games_df = all_games_df.loc[
    (all_games_df.index >= pd.Timestamp(date_range[0]))
    & (all_games_df.index < pd.Timestamp(date_range[1]) + pd.Timedelta(days=1))
]
if side != "Both":
    games_df = games_df[games_df["UserColor"] == side]
if "TimeClass" in games_df.columns:
    games_df = games_df[games_df["TimeClass"].isin(time_classes)]
games_df = games_df[games_df["Region"].isin(selected_regions)].copy()

if games_df.empty:
    st.warning("No games match the selected filters.")
    st.stop()

counts = result_counts(games_df)
decisive = counts["Win"] + counts["Loss"]
winrate = counts["Win"] / decisive if decisive else 0.0
total_games = len(games_df)

country_winrates = results_by(games_df.dropna(subset=["Country"]),
                              ["Country", "CountryISO3"]).sort_values("Winrate")

tab_overview, tab_results, tab_openings, tab_opponents, tab_countries, tab_data = st.tabs(
    ["Overview", "Results over time", "Opening analysis", "Opponents", "Opponent countries",
     "Game data"]
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
        result_df = pd.DataFrame({"Result": RESULTS, "Games": [counts[r] for r in RESULTS]})
        fig = px.pie(result_df, names="Result", values="Games", hole=0.58,
                     title="Result distribution", color="Result",
                     color_discrete_map=RESULT_COLORS)
        fig.update_layout(legend_title_text="")
        st.plotly_chart(fig, width="stretch")
    with right:
        trend = monthly_results(games_df)
        fig = go.Figure()
        for col in RESULTS:
            fig.add_trace(go.Bar(x=trend["Month"], y=trend[col], name=col,
                                 marker_color=RESULT_COLORS[col]))
        fig.update_layout(title="Games played per month", barmode="stack",
                          xaxis_title="", yaxis_title="Games")
        st.plotly_chart(fig, width="stretch")

    st.subheader("Recent games")
    display_cols = [c for c in ["White", "Black", "Result", "RelativeResult", "Opening",
                                "Opening_Group", "TimeClass", "WhiteElo", "BlackElo",
                                "Opponent", "Country"]
                    if c in games_df.columns]
    st.dataframe(games_df[display_cols].sort_index(ascending=False).head(15),
                 width="stretch")

# Results over time
with tab_results:
    st.subheader("Win rate over time")
    fig = go.Figure()
    sides = ["Overall"] + ([side] if side != "Both" else ["White", "Black"])
    for line in dict.fromkeys(sides):
        monthly = monthly_results(games_df, color=None if line == "Overall" else line)
        fig.add_trace(go.Scatter(
            x=monthly["Month"], y=monthly["Winrate"], name=line, mode="lines+markers",
            line=dict(color=SIDE_COLORS[line], width=3 if line == "Overall" else 2),
        ))
    overall = monthly_results(games_df)
    fig.add_hline(y=0.5, line_color="gray", annotation_text="50%",
                  annotation_position="top left")
    fig.add_hline(y=overall["Winrate"].mean(), line_dash="dot", line_color=SIDE_COLORS["Overall"],
                  annotation_text="Average winrate", annotation_position="bottom right")
    fig.update_layout(title="Monthly win rate by color (draws excluded)",
                      xaxis_title="", yaxis_title="Win rate", legend_title_text="")
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, width="stretch")

    st.subheader("Games by result per month")
    result_long = overall.melt(
        id_vars="Month", value_vars=RESULTS, var_name="Result", value_name="Games"
    )
    fig = px.bar(result_long, x="Month", y="Games", color="Result", barmode="stack",
                 color_discrete_map=RESULT_COLORS)
    fig.update_layout(xaxis_title="", yaxis_title="Games")
    st.plotly_chart(fig, width="stretch")

# Opening analysis
with tab_openings:
    st.subheader(f"Win rate in your top {top_n_openings} openings")
    opening_totals = results_by(games_df, "Opening_Group").set_index("Opening_Group")
    opening_totals = opening_totals.loc[top_openings(games_df, top_n_openings)]
    per_row = 5
    for start in range(0, len(opening_totals), per_row):
        columns = st.columns(per_row)
        for container, (opening, row) in zip(columns, opening_totals.iloc[start:start + per_row].iterrows()):
            rate = row["Winrate"]
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=0 if pd.isna(rate) else rate * 100,
                number={"suffix": "%", "valueformat": ".0f"},
                title={"text": f"{opening}<br><span style='font-size:0.8em;color:gray'>"
                               f"{int(row['Total'])} games</span>",
                       "font": {"size": 13}},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": OPENING_COLORS.get(opening)},
                    "steps": [{"range": [0, 50], "color": "#fdecea"},
                              {"range": [50, 100], "color": "#e8f5e9"}],
                    "threshold": {"line": {"color": "gray", "width": 2}, "value": 50},
                },
            ))
            fig.update_layout(height=230, margin=dict(l=20, r=20, t=70, b=10))
            container.plotly_chart(fig, width="stretch")

    st.subheader("Most-played opening groups")
    opening_counts = games_df["Opening_Group"].value_counts().head(15).rename_axis(
        "Opening group"
    ).reset_index(name="Games")
    fig = px.bar(opening_counts.sort_values("Games"), x="Games", y="Opening group",
                 orientation="h", title="Top opening groups", color="Opening group",
                 color_discrete_map=OPENING_COLORS)
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width="stretch")

    st.subheader("Opening win rates by quarter")
    opening_rates = make_opening_winrate(games_df, top_n=top_n_openings)
    if not opening_rates.empty:
        fig = px.line(opening_rates, x="Quarter", y="Winrate", color="Opening_Group",
                      facet_col="Opening_Group", facet_col_wrap=5, markers=True,
                      color_discrete_map=OPENING_COLORS,
                      hover_data={"Total": True, "Opening_Group": False},
                      category_orders={"Opening_Group": list(top_openings(games_df, top_n_openings))})
        fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
        fig.add_hline(y=0.5, line_color="black", line_width=1)
        fig.update_xaxes(title_text="")
        fig.update_yaxes(title_text="", tickformat=".0%", range=[0, 1])
        rows = math.ceil(opening_rates["Opening_Group"].nunique() / 5)
        fig.update_layout(showlegend=False, height=280 * rows)
        st.plotly_chart(fig, width="stretch")

    st.subheader("Opening usage over time")
    usage = monthly_openings(games_df)
    usage = usage.loc[:, usage.columns.isin(usage.sum().nlargest(top_n_openings).index)]
    if not usage.empty:
        st.plotly_chart(opening_lines(usage, "Monthly games by opening group"),
                        width="stretch")

    white, black = st.columns(2)
    for color, container in [("White", white), ("Black", black)]:
        with container:
            subset = games_df[games_df["UserColor"] == color]
            if subset.empty:
                st.info(f"No games as {color.lower()} with the current filters.")
                continue
            usage = monthly_openings(subset)
            usage = usage.loc[:, usage.columns.isin(usage.sum().nlargest(5).index)]
            st.plotly_chart(opening_lines(usage, f"({color}) Openings played over time"),
                            width="stretch")

# Opponents
with tab_opponents:
    st.subheader("Results against frequent opponents")
    opponent_summary = results_by(games_df, "Opponent").set_index("Opponent")
    opponent_summary = opponent_summary[opponent_summary["Total"] >= min_games_opponent]
    opponent_summary = opponent_summary.sort_values("Total", ascending=False)
    if opponent_summary.empty:
        st.info("No opponents meet the selected minimum-games threshold.")
    else:
        donut_opponents = opponent_summary.head(12)
        cols = 4
        rows = math.ceil(len(donut_opponents) / cols)
        fig = make_subplots(
            rows=rows, cols=cols,
            specs=[[{"type": "domain"}] * cols for _ in range(rows)],
            subplot_titles=[f"{name} ({int(row['Total'])})"
                            for name, row in donut_opponents.iterrows()],
        )
        for i, (name, row) in enumerate(donut_opponents.iterrows()):
            fig.add_trace(go.Pie(
                labels=RESULTS, values=[row[r] for r in RESULTS], hole=0.55, sort=False,
                marker_colors=[RESULT_COLORS[r] for r in RESULTS], name=name,
                textinfo="none", showlegend=i == 0,
                hovertemplate="%{label}: %{value} games (%{percent})<extra>" + name + "</extra>",
            ), row=i // cols + 1, col=i % cols + 1)
        fig.update_layout(
            title=f"Results against top opponents (minimum {min_games_opponent} games)",
            height=230 * rows + 60,
        )
        st.plotly_chart(fig, width="stretch")

        st.dataframe(
            opponent_summary.style
            .background_gradient(subset=["Win"], cmap="Greens")
            .background_gradient(subset=["Loss"], cmap="Reds")
            .background_gradient(subset=["Tie"], cmap="Greys")
            .background_gradient(subset=["Winrate"], cmap="RdYlGn", vmin=0, vmax=1)
            .format({"Winrate": "{:.1%}"}, na_rep="–"),
            width="stretch",
        )

# Opponent countries
with tab_countries:
    st.subheader("Win rate by opponent country")
    if not has_countries:
        st.info(
            "No opponent country data found. Set IMPORT_OPPONENT_COUNTRIES=TRUE in "
            "parameters.env and run import_all_chess_dot_com_games.py, and make sure "
            "data/ISO_countries.csv exists."
        )
    else:
        frequent_countries = country_winrates[country_winrates["Total"] >= min_games_country]
        if frequent_countries.empty:
            st.info("No countries meet the selected minimum-games threshold.")
        else:
            fig = px.choropleth(
                frequent_countries,
                locations="CountryISO3",
                locationmode="ISO-3",
                color="Winrate",
                hover_name="Country",
                hover_data={"CountryISO3": False, "Win": True, "Loss": True, "Tie": True,
                            "Total": True, "Winrate": ":.1%"},
                color_continuous_scale="RdYlGn",
                range_color=[0, 1],
                projection="natural earth",
                title=f"Win rate by opponent country (minimum {min_games_country} games)",
            )
            fig.update_layout(
                geo=dict(showframe=False, showcoastlines=True, bgcolor="rgba(0,0,0,0)",
                         showland=True, landcolor="#d6d6d6"),
                margin=dict(l=0, r=0, t=50, b=0),
                height=550,
                coloraxis_colorbar=dict(tickformat=".0%", title="Win rate"),
            )
            # Let the mouse wheel scroll the page instead of zooming the map.
            st.plotly_chart(fig, width="stretch", config={"scrollZoom": False})

            st.dataframe(
                frequent_countries.drop(columns="CountryISO3").set_index("Country")
                .sort_values("Total", ascending=False).style
                .background_gradient(subset=["Winrate"], cmap="RdYlGn", vmin=0, vmax=1)
                .format({"Winrate": "{:.1%}"}, na_rep="–"),
                width="stretch",
            )
        unmatched = games_df["Country"].isna().sum()
        if unmatched:
            st.caption(f"{unmatched:,} games are against opponents with no known country "
                       "and are not included.")

# Data and downloads
with tab_data:
    st.subheader("Processed game data")
    st.caption("Use the filters and downloads below to inspect or export the processed dataset.")
    result_filter = st.multiselect(
        "Filter by result", options=RESULTS + ["Other"], default=RESULTS
    )
    filtered_df = games_df[games_df["RelativeResult"].isin(result_filter)]
    st.dataframe(filtered_df.sort_index(ascending=False), width="stretch",
                 height=450)
    st.download_button(
        "Download processed games (CSV)",
        data=filtered_df.to_csv(index=True).encode("utf-8"),
        file_name="mygames_dataframe.csv",
        mime="text/csv",
        width="stretch",
    )
    st.download_button(
        "Download opponent summary (CSV)",
        data=opponent_summary.to_csv(index=True).encode("utf-8"),
        file_name="opponent_summary.csv",
        mime="text/csv",
        width="stretch",
    )
    st.download_button(
        "Download opening usage (CSV)",
        data=monthly_openings(games_df).to_csv(index=True).encode("utf-8"),
        file_name="monthly_openings.csv",
        mime="text/csv",
        width="stretch",
    )
    st.download_button(
        "Download country win rates (CSV)",
        data=country_winrates.drop(columns="CountryISO3").to_csv(index=False).encode("utf-8"),
        file_name="country_winrates.csv",
        mime="text/csv",
        width="stretch",
    )
