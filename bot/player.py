import chess

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

CENTER = [chess.D4, chess.E4, chess.D5, chess.E5]

def evaluate(board: chess.Board) -> int:
    if board.is_checkmate():
        return -999999 if board.turn else 999999
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0

    for piece_type, v in PIECE_VALUES.items():
        score += len(board.pieces(piece_type, chess.WHITE)) * v
        score -= len(board.pieces(piece_type, chess.BLACK)) * v

    for sq in CENTER:
        piece = board.piece_at(sq)
        if piece:
            score += 15 if piece.color == chess.WHITE else -15

    score += board.legal_moves.count() if board.turn == chess.WHITE else -board.legal_moves.count()

    if board.is_check():
        score += -30 if board.turn == chess.WHITE else 30

    return score

def negamax(board: chess.Board, depth: int, alpha: int, beta: int) -> int:
    if depth == 0 or board.is_game_over():
        return evaluate(board)

    best = -10**9
    for move in board.legal_moves:
        board.push(move)
        val = -negamax(board, depth - 1, -beta, -alpha)
        board.pop()

        if val > best:
            best = val
        if best > alpha:
            alpha = best
        if alpha >= beta:
            break
    return best

def choose_move(board: chess.Board, depth: int = 2) -> chess.Move:
    best_move = None
    best_val = -10**9
    alpha = -10**9
    beta = 10**9

    for move in board.legal_moves:
        board.push(move)

        rep_penalty = 50 if board.is_repetition(2) else 0

        val = -negamax(board, depth - 1, -beta, -alpha)
        val2 = val - rep_penalty

        board.pop()

        if val2 > best_val:
            best_val = val2
            best_move = move

        if best_val > alpha:
            alpha = best_val

    if best_move is None:
        return next(iter(board.legal_moves))
    return best_move
