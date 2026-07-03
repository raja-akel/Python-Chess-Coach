import chess
from stockfish import Stockfish

stockfish = Stockfish()
stockfish.set_skill_level(10)
stockfish.set_depth(15)
stockfish.get_top_moves(3)

#chess_database_pgn = open("C:\\Users\\user\\PycharmProjects\\Databases\\lichess_db_standard_rated_2017-01.pgn\\lichess_db_standard_rated_2017-01.pgn")

def analyze_chess_database():
    player_database_pgn = open(
        "\\rajakel_all_games.pgn"
    )
    #for


    return