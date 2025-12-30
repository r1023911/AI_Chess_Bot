import chess
import chess.polyglot

BOOK_PATH = "data/opening.bin"

def book_move(board: chess.Board):
    try:
        with chess.polyglot.open_reader(BOOK_PATH) as reader:
            entry = reader.weighted_choice(board)
            return entry.move
    except Exception:
        return None
