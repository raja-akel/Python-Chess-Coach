import chess
import chess.pgn
import random

from my_functions import *

board = chess.Board()
board.reset()

def two_player_game():

    while True:
        temp_move = ""
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
            print("Checkmate. White wins!")
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
            print("Checkmate. Black wins!")
            break

    print_board(board)
    print(board.status())