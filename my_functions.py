import chess
import random
import pandas as pd

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