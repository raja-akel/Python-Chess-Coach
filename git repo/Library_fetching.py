import chess
import chess.pgn
import random
import pandas

def print_moves(game):
    temp_output = ""
    for move in game.mainline_moves():
        temp_output = temp_output + str(move)[2:4] + " 0"

    print(temp_output)
    return

library_pgn = open("C:\\Users\\user\\rajakel_all_games.pgn")


criteria_length = input("Input the number of moves to search for (e.g., e4 e5 counts as 2 moves): ")
criteria_moves = input("Input the moves to search for, separated by a space (e.g., e4 e5 f4): ")

games_matching_user_criteria = []

for i in range(1,2): #database has 3,366 games
    #temp_game.append(chess.pgn.read_game(library_pgn))
    temp_game = chess.pgn.read_game(library_pgn)
    temp_line = ""

    counter = 0
    for temp_move in temp_game.mainline_moves():
        #print(temp_move)
        temp_line = temp_line + str(temp_move)[2:4]
        counter += 1
        if counter == int(criteria_length):
            break

    if temp_line.strip() == criteria_moves.strip():
        games_matching_user_criteria.append(temp_game)
    #print(temp_line)

print_moves(games_matching_user_criteria[0])
#print(len(temp_game))
#print(temp_game)