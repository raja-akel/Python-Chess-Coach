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


#board = chess.Board()
#print_board(board)
#print_legal_moves(board)