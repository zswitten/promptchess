import chess
from chess import svg
import chess.pgn as pgn
import openai
import cohere
from langchain.llms import GooseAI, OpenAI, Cohere
import os
import math
import random
from IPython.display import display, Image, clear_output  # Comment out if not using notebook

os.environ["OPENAI_API_KEY"] = ""
os.environ["COHERE_API_KEY"] = ""
os.environ["GOOSEAI_API_KEY"] = ""

args = {'max_tokens': 50, 'temperature': 0}
cohere_llm = Cohere(**args)
openai_llm = OpenAI(**args)
gooseai_llm = GooseAI(**args)

def get_completion(prompt, company='openai', model='babbage'):
    if company == 'openai':
        llm = openai_llm
        llm.model_name = model
        # Below special case is needed because gooseai and openai overwrite the base and key
        openai.api_base = 'https://api.openai.com/v1'
        openai.api_key = os.environ["OPENAI_API_KEY"]
        completion = openai.Completion.create(
          model=model,
          prompt=prompt,
          **args
        )
        return completion.choices[0].text
    elif company == 'gooseai':
        llm = gooseai_llm
        llm.model_name = model
        openai.api_base = 'https://api.goose.ai/v1'
        openai.api_key = os.environ["GOOSEAI_API_KEY"]
    elif company == 'cohere':
        llm = cohere_llm
        llm.model = model
        import time; time.sleep(1)  # Avoid timeout on free tier
    else:
        print('Not implemented')
    return llm.generate([prompt]).generations[0][0].text
    
def piece_map_to_san(board):
    # Print a formatted string listing the position of each piece
    piece_map = board.piece_map()
    pieces = {'Black': [], 'White': []}
    for piece in piece_map:
        row = str(math.ceil((piece + 1) / 8))
        col = chr(97 + piece % 8)
        square = piece_map[piece].symbol().upper() + col + row
        if piece_map[piece].symbol().isupper():
            pieces['White'].append(square)
        else:
            pieces['Black'].append(square)
    return "Black: " + ', '.join(pieces['Black']) + ". White: " + ', '.join(pieces['White'])

class PromptPlayer:
    def __init__(self, board, company, model, prompt_template):
        self.board = board
        self.company = company
        self.model = model
        self.prompt_template = prompt_template
    
    def get_legal_moves_str(self):
        return ', '.join([self.board.san(move) for move in self.board.legal_moves])
    
    def get_move_history(self):
        # Formatted in algebraic notation
        copyboard = self.board.copy()
        moves = []
        while copyboard.move_stack:
            moves = [copyboard.pop()] + moves
        move_history = ''
        for i, move in enumerate(moves):
            if i % 2 == 0:
                move_history += str(math.ceil(i / 2.0)) + '. ' + copyboard.san(move) + ' '
            else:
                move_history += copyboard.san(move) + '\n'
            copyboard.push(move)
        return move_history.rstrip()

    def format_prompt(self):
        board_state = piece_map_to_san(self.board)
        legal_moves_str = self.get_legal_moves_str()
        move_history = self.get_move_history()
        return self.prompt_template.replace(
            "!board_state!", board_state).replace(
            '!legal_moves!', legal_moves_str).replace('!move_history!', move_history)
    
    def parse_completion(self, completion):
        # Take first string match of a legal move in the completion
        idx, selected_move = None, None
        legal_moves = [self.board.san(move) for move in self.board.legal_moves]
        moves_in_completion = {}
        for move in legal_moves:
            if move in completion:
                moves_in_completion[move] = completion.index(move)
        if not moves_in_completion:
            print("random move being chosen.")
            return (random.choice(legal_moves), True)
        else:
            return (sorted(moves_in_completion, key=lambda x: moves_in_completion[x])[0], False)
    
    def get_move(self):
        completion = get_completion(self.format_prompt(), self.company, self.model)
        print("Completion:", completion)
        return self.parse_completion(completion)

def simulate_game(white_player, black_player, board=None, max_moves=99):
    if not board:
        board = chess.Board()
    white_player.board = board
    black_player.board = board
    num_random_moves = {
        white_player: {True: 0, False: 0},
        black_player: {True: 0, False: 0}
    }
    moves = 0
    while not board.outcome():
        if board.turn:
            active_player = white_player
        else:
            active_player = black_player
        move, is_random = active_player.get_move()
        san_move = board.parse_san(move)
        board.push_san(move)
        num_random_moves[active_player][is_random] += 1
        # Comment out these if not running in notebook
        clear_output()
        display(svg.board(board, size=500, lastmove=san_move))
        moves += 1
        if moves > max_moves:
            break
    return board, num_random_moves

def export_game_to_pgn(game):
    pgn_game = pgn.Game()
    pgn_game.headers["Event"] = "Example"
    node = pgn_game.add_variation(game.move_stack[0])
    for move in game.move_stack[1:]:
        node = node.add_variation(move)
    return pgn_game
    # can call print(pgn_game) to get it in pastable format for e.g. chess.com

## Prompts ##
PROMPT1 = "Carlsen vs. Nakamura, Helsinki, 2023\nAnalyzed by Stockfish\n"
PROMPT1 += "Game Transcript So Far: !move_history!\n"
PROMPT1 += "Stockfish's Analysis:\nThe legal moves are !legal_moves!\n"
PROMPT1 += "The best next move is:"

PROMPT2 = "Carlsen vs. Nakamura, Helsinki, 2023\n!move_history!"

PROMPT3 = "INSTRUCTIONS\nYou are Magnus Carlsen, chess grandmaster."
PROMPT3 += "You will be presented with the set of legal moves and the game history so far. "
PROMPT3 += "Choose the best move from the set of legal moves provided. "
PROMPT3 += "Repeat, your move must always be in the set of legal moves.\n"
PROMPT3 += "- Whenever possible, prefer moves that capture a piece, and moves that deliver check. In other words, "
PROMPT3 += "if the set of legal moves contains one or more moves with x or +, choose one of those.\n"
PROMPT3 += "Prioritize pawn moves (moves that do not begin with N, K, Q, B, or R)."
PROMPT3 += "- Do NOT select any move that is in the last 4 moves of MOVE_HISTORY! "
PROMPT3 += "Repeat, do not select any move that you have played recently. For instance, if Nf7 is in "
PROMPT3 += "MOVE_HISTORY, and the set of legal_moves is [Nf7, Rh2, g3, g4], do not select Nf7. "
PROMPT3 += "Instead, you should select g3 or g4 because it is a pawn move.\n"
PROMPT3 += "- Prioritize moving a different piece than the last piece you moved. For example, if the last move in "
PROMPT3 += "MOVE_HISTORY was Bf4, your next move should not begin with B.\n"
PROMPT3 += "The *most important rule*: ALWAYS ALWAYS select any move with the # symbol. " 
PROMPT3 += "# denotes checkmate which is your goal!"
PROMPT3 += "Examples:\n 1. If the set of legal moves is [Nf3, Bxc6+, g3, g4], you might suggest Bxc6+ "
PROMPT3 += "because Bxc6+ contains an x (it is a capture) and a + (it is a check).\n"
PROMPT3 += "2. If MOVE_HISTORY contains '22. Nd6+ Kc7\23. Nc8 Kb7\n', you would NOT select Nd6+ because "
PROMPT3 += "it exists in MOVE_HISTORY.\n"
PROMPT3 += "3. If the set of legal moves is [Qg8, Qxf2, Qg7#], you should select Qg7# because it has a #"
PROMPT3 += "LEGAL_MOVES: !legal_moves!\n"
PROMPT3 += "MOVE_HISTORY: !move_history!\n"
PROMPT3 += "SELECTED_MOVE:"

PROMPT4 = """
You will be given a list of legal chess moves, LEGAL_MOVES. Pick one of them. Rules, in order of decreasing priority:
1. CHECKMATE. If one or more moves contains #, select a move that contains a #.
2. CAPTURE. If one or more moves contains x, select a move that contains x.
3. PROMOTION. If one or more moves contains =, select the move that contains =.
3. PAWN MOVE. Select a move that does not contain capital letters.
4. RANDOM MOVE. Select any move from the list.
Go through the list of rules in order, stating whether the rule applies. If a rule does apply, use it to select your move.

Example 1:
LEGAL_MOVES: Nf7, Rh2, g3, g4, Qxg8, Qg4#, Qc6, Qd6, Rb3, Rb2, Rb1
RESPONSE:
Rule CHECKMATE applies. Qg4# contains a #. 
SELECTED MOVE: Qg4#

Example 2:
LEGAL_MOVES: Nf7, Rh2, g3, g4, Qxg8, Qc6, Qd6, Rb3, Rb2, Rb1
RESPONSE:
Rule CHECKMATE: No.
Rule CAPTURE applies. Qxg8 contains x.
SELECTED MOVE: Qxg8

Example 3:
LEGAL_MOVES: Nf7+, Rh2, g3, g4, Qc6, Qd6, Rb3, Rb2, Rb1
Rule CHECKMATE: No.
Rule CAPTURE: No.
Rule PROMOTION: No.
Rule PAWN MOVE applies. g3 does not contain a capital letter.
SELECTED MOVE: g3.

Example 4:
LEGAL_MOVES: Ne7+, Na7, Nd6, Nb6, Bh8, Bg7, b8=Q, Bf6, Ba1, Kh3, Kh1, Kg1, Rf2, Re2, Rd2, Rc2, Rb2, Ra2, Rg1
Rule CHECKMATE: No.
Rule CAPTURE: No.
Rule PROMOTION applies. b8=Q contains =.
SELECTED MOVE: b8.

Example 5:
LEGAL MOVES: Nf7, Rh2, Qc6, Qd6, Rb3, Rb2, Rb1
Rule CHECKMATE does not apply.
Rule CAPTURE does not apply.
Rule PROMOTION does not apply
Rule PAWN MOVE does not apply.
Rule RANDOM MOVE applies.
Selected move: Nf7.

Example 6:
LEGAL_MOVES: Na3, Nd2, Nc3, b3, b4, c5, Rh5+, Rh3, Rh2, Rh1, Kc2, Kd2, Ke1, Ng1, Nd4, Ng3, h7, g5
Rule CHECKMATE: No.
Rule CAPTURE: No.
Rule PROMOTION: No.
Rule PAWN MOVE applies. h7 does not contain a capital letter.
SELECTED MOVE: h7.

Example 7:
LEGAL MOVES: Na3, Nc3, Ra2, Ra3, Ra4, Bb2, Ba3, Bd2, Be3, Kd2, Ke2, Kf1, Kf2, exd5, fxe5, Rh2, Rh3
Rule CHECKMATE: No.
Rule CAPTURE applies. exd5 contains x.
SELECTED MOVE: exd5

LEGAL MOVES: !legal_moves!
RESPONSE:
"""
