import chess
import chess.pgn
import random
from stockfish import Stockfish

from single_player_coach import single_player_coach

stockfish = Stockfish("C:\\Users\\user\\PycharmProjects\\Databases\\stockfish-windows-x86-64-avx2\\stockfish\\stockfish-windows-x86-64-avx2.exe")


from my_functions import *

board = chess.Board()
board.reset()

x = 0

game_mode = input("Choose game mode(1p or 2p): ")

if game_mode == "2p":
    while not (x == 1) :
        print_board(board)
        print("\n", temp_move)
        print_legal_moves(board)

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



        if board.is_game_over():
            print_board(board)
            break

        print_board(board)
        print_legal_moves(board)

        while True:
            b_move = input("Black move: ")
            try:
                temp_move = board.parse_san(b_move)
                if board.is_legal(temp_move):
                    board.push(temp_move)
                    break
                else:
                    print("Illegal move")
            except:
                print("Illegal move")

        if board.is_game_over():
            print_board(board)
            break

    print_board(board)
    print(board.status())




elif game_mode == "1p":
    single_player_coach() #calling script from "single_player_coach.py"

