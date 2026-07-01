import chess
import chess.pgn
import random
from stockfish import Stockfish

stockfish = Stockfish("C:\\Users\\user\\PycharmProjects\\Databases\\stockfish-windows-x86-64-avx2\\stockfish\\stockfish-windows-x86-64-avx2.exe")
#stockfish.set_skill_level(10)
#stockfish.set_depth(15)
#stockfish.get_top_moves(3)


from my_functions import *

board = chess.Board()
board.reset()


def single_player_coach():

### SETTINGS FOR TUNING STOCKFISH ENGINE - asking the user for input on elo level ###
    user_input_elo_level = int(input("Choose the elo level you would like to play against (1320-2500): "))

    while user_input_elo_level not in range(1320,2500):
        user_input_elo_level = int(input("Please keep the value between 1320-2500: "))

    stockfish.set_elo_rating(int(user_input_elo_level))
    stockfish.set_depth(2)

########################################################################################
    temp_move = ""

### MAIN GAME LOOP ###
    while True:
        print_board(board)
        print_legal_moves(board)

        print("\n", temp_move)
        while True:
            w_move = input("White move: ")
            try:
                temp_move = board.parse_san(w_move)
                if board.is_legal(temp_move):
                    board.push(temp_move)
                    break
                else:
                    print("Illegal move")
            except:
                print("Illegal move")
        if board.is_game_over(): #if game ended, show the final state
            print_board(board)
            break


        print_board(board)

        temp_fen_position = board.fen()
        stockfish.set_fen_position(temp_fen_position, True)
        temp_move = board.parse_uci(stockfish.get_best_move_time(10))

        if board.is_legal(temp_move):
            board.push(temp_move)
        else:
            print("Illegal move")
            break

        if board.is_game_over():
            print_board(board)
            break

###################################################################################

    print_board(board)
    print(board.status())

    return