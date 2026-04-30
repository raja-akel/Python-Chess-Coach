import chess
import chess.pgn
import random



from my_functions import *

board = chess.Board()
board.reset()

x = 0

while not (x == 1) :
    print("\n\n\n\n\n\n")

    print_board(board)
    print_legal_moves(board)

    w_move = input("White move: ")
    temp_move = board.parse_san(w_move)

    if board.is_legal(temp_move):
        board.push(temp_move)
    else:
        print("Illegal move")
        break

    print("\n\n\n\n\n\n")

    print_board(board)
    print_legal_moves(board)

    b_move = input("Black move: ")
    temp_move = board.parse_san(b_move)

    if board.is_legal(temp_move):
        board.push(temp_move)
    else:
        print("Illegal move")
        break




print_board(board)
print(board.status())