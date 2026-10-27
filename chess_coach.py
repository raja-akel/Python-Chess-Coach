import chess
import chess.pgn
import random
from stockfish import Stockfish
from my_functions import *
from single_player_coach import *
from two_player_game import *
from chess_database import *

stockfish = Stockfish("C:\\Users\\user\\PycharmProjects\\Databases\\stockfish-windows-x86-64-avx2\\stockfish\\stockfish-windows-x86-64-avx2.exe")

coach_mode = input("Choose functionality (review or play): ") #pick between analyzing a chess database or playing chess

while coach_mode not in ("review", "play"): #checking user input
    coach_mode = input("Wrong input: ")

if coach_mode == "review":
    analyze_chess_database()

elif coach_mode == "play":
    game_mode = input("Choose game mode(1p or 2p): ") #choose between 1 player (against the coach) or 2 player (with a friend)

    while game_mode not in ("1p", "2p"): #checking user input
        game_mode = input("Wrong input: ")

    if game_mode == "2p":
        two_player_game()

    elif game_mode == "1p":
        single_player_coach() #calling script from "single_player_coach.py"