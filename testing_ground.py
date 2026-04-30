import chess
import chess.pgn
import random

from my_functions import print_board

board = chess.Board.from_chess960_pos(random.randint(0, 959))

#print(board.root())

board.reset()

#print(board.root())

#print(board.is_game_over())

x = 0

while not (x == 1) :
    #print(board.legal_moves)
    print_board(board)

    w_move = input("White move: ")
    temp_move = chess.Move.from_uci(w_move)
    print(board.is_legal(temp_move))
    x = 1
