# Prompt Engineering Chess
Test your prompt engineering skills by writing prompts and battling them against each other.

## Try it out
0. `git clone https://github.com/zswitten/promptchess`
1. `pip install -r requirements.txt`
2. Plug in API creds to `prompt_player.py` for any models you want to use.
3. `jupyter notebook`, open up PromptPlayerExample.ipynb and initialize your players as desired using example prompts or your own prompts, and simulate a game.

#### Notes
- Warning: it's easy to eat up a lot of credits because this code makes looping calls to the LM API. You may want to set max moves to cap per-game usage,
or experiment with cheaper models first.
- So far, PROMPT4 with text-davinci-003 is the only prompt/model combo I've found that can actually deliver checkmate.

## Writing a Prompt
The rules of Prompt Engineering Chess are that you can access three variables: the move history of the game so far, the current board state, 
and the legal moves from the board state. You can use them in your prompt with !move_history!, !board_state!, and !legal_moves!. Example:
```
player2.board = prompt_player.chess.Board()
prompt = "Carlsen vs. Nakamura, Helsinki, 2023\nAnalyzed by Stockfish\n"
prompt += "Game Transcript So Far: !move_history!\nStockfish's Analysis:\nThe legal moves are !legal_moves!\n"
prompt += "The current board state is !board_state!.\n"
prompt += "The best next move is:"
print(player2.format_prompt())
```
Output (what gets sent to OpenAI):
```
Carlsen vs. Nakamura, Helsinki, 2023
Analyzed by Stockfish
Game Transcript So Far: 
Stockfish's Analysis:
The legal moves are Nh3, Nf3, Nc3, Na3, h3, g3, f3, e3, d3, c3, b3, a3, h4, g4, f4, e4, d4, c4, b4, a4
The best next move is:
```

Other examples can be found in prompt_player.py.

## Sample game
White is playing as a prompt which uses string parsing to prioritize checkmates, captures, promotions, and pawn moves from the set of legal moves,
while ignoring move history and board state. It doesn't actually make every possible capture. Black is playing as PROMPT2 from the examples.
White is using text-davinci-003 while Black is using Eleuther's GPT-J 6B.
![](https://github.com/zswitten/promptchess/blob/master/prompt4_v_baseline.gif)

### Credits
[python-chess](https://github.com/niklasf/python-chess) for the underlying chess engine.  
[This Reddit post](https://www.reddit.com/r/AnarchyChess/comments/10ydnbb/i_placed_stockfish_white_against_chatgpt_black/) for inspiring this wackiness.
