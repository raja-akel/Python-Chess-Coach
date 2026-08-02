import chess
import random
import pandas as pd
import matplotlib.pyplot as plt

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def print_board(board):
    print("\n\n\n\n\n\n")
    print(board, "\n")
    return

def print_legal_moves(board):
    list_of_moves = {
        "N": [],
        "P": [],
        "K": [],
        "Q": [],
        "R": [],
        "B": []
    }
    for i in board.legal_moves:
        temp_piece = str(board.piece_at(chess.parse_square(i.uci()[0:2]))).upper()
        list_of_moves[temp_piece].append(i.uci()[2:4])
    for i in list_of_moves.items():
        if not len(i[1]) == 0:
            print(i[0], i[1])
    return

def import_games(source_pgn):
    player_database_pgn = open(source_pgn, encoding="utf-8")

    all_games = {}
    game_uid = 1
    current_game = {}
    moves = []

    for line in player_database_pgn:
        line = line.strip()

        if not line:
            continue

        if line.startswith("["):
            tag_name = line.split(" ", 1)[0][1:]
            tag_value = line.split('"')[1]

            if tag_name == "Event" and current_game:
                current_game["game_pgn"] = " ".join(moves)
                all_games[game_uid] = current_game
                game_uid += 1
                current_game = {}
                moves = []

            current_game[tag_name] = tag_value

        else:
            moves.append(line)

    # save the final game
    if current_game:
        current_game["game_pgn"] = " ".join(moves)
        all_games[game_uid] = current_game

    return all_games


def add_opening_group(df, opening_col="Opening", new_col="Opening_Group"):
    df = df.copy()
    df[new_col] = df[opening_col].apply(clump_opening)
    return df

def clump_opening(opening):
    OPENING_GROUPS = {
        "Sicilian Defense": [
            "Alapin Sicilian Defense",
            "Closed Sicilian Defense",
            "Sicilian Defense",
        ],
        "Alekhine Defense": ["Alekhines Defense"],
        "Benoni Defense": ["Benoni Defense", "Old Benoni Defense"],
        "Bird Opening": ["Birds Opening"],
        "Bishop's Opening": ["Bishops Opening"],
        "Caro-Kann Defense": ["Caro Kann Defense"],
        "Center Game": ["Center Game"],
        "Colle System": ["Colle System"],
        "English Opening": ["English Opening"],
        "Englund Gambit": ["Englund Gambit"],
        "Four Knights Game": ["Four Knights Game"],
        "French Defense": ["French Defense"],
        "Grunfeld Defense": ["Grunfeld Defense", "Neo Grunfeld Defense"],
        "Indian Game": ["Indian Game"],
        "Italian Game": ["Italian Game"],
        "King's Gambit": ["Kings Gambit"],
        "King's Indian": ["Kings Indian Attack", "Kings Indian Defense"],
        "King's Pawn Opening": ["Kings Pawn Opening"],
        "Modern Defense": ["Modern Defense"],
        "Nimzowitsch-Larsen Attack": ["Nimzowitsch Larsen Attack"],
        "Old Indian Defense": ["Old Indian Defense"],
        "Petrov Defense": ["Petrovs Defense"],
        "Philidor Defense": ["Philidor Defense"],
        "Pirc Defense": ["Pirc Defense"],
        "Polish Opening": ["Polish Opening"],
        "Ponziani Opening": ["Ponziani Opening"],
        "Queen's Gambit": ["Queens Gambit"],
        "Queen's Pawn Opening": ["Queens Pawn Opening"],
        "Reti Opening": ["Reti Opening"],
        "Ruy Lopez": ["Ruy Lopez Opening"],
        "Scandinavian Defense": ["Scandinavian Defense"],
        "Scotch Game": ["Scotch Game"],
        "Slav/Semi-Slav Defense": ["Slav Defense", "Semi Slav Defense"],
        "Three Knights Opening": ["Three Knights Opening"],
        "Vienna Game": ["Vienna Game"],
    }
    if pd.isna(opening):
        return "Unknown"

    opening = str(opening).strip()

    for group, patterns in OPENING_GROUPS.items():
        for pattern in patterns:
            if opening.startswith(pattern):
                return group

    return "Other"

"""
def monthly_opening_counts_by_color(
    df,
    opening_col="Opening_Group",
    min_total_games=50,
    freq="ME"
):
    df = df.copy()
    df = df.sort_index()
    df.index = pd.to_datetime(df.index)

    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        horizontal_spacing=0.2,
        subplot_titles=["White", "Black"],
    )

    color_specs = [
        ("White", df["isWhite"] == True, 1),
        ("Black", df["isBlack"] == True, 2),
    ]

    for color_name, mask, row in color_specs:
        subset = df.loc[mask]

        monthly = (
            subset.groupby(pd.Grouper(freq=freq))[opening_col]
            .value_counts()
            .reset_index()
        )

        # Drop openings with fewer than min_total_games for this color
        monthly = monthly.loc[:, monthly.sum(axis=0) >= min_total_games]

        fig.add_trace(go.Scatter(x=monthly.index, y=monthly['count'], color, mode='lines'))

        ax.set_title(f"{color_name} Opening Families Over Time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Games per Month")
        ax.legend(title="Opening", bbox_to_anchor=(1.02, 1), loc="upper left")

    plt.tight_layout()
    plt.show()
"""
