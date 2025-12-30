import chess
from opening_book import book_move

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

CENTER = [chess.D4, chess.E4, chess.D5, chess.E5]

MATE = 10**9

def _piece_value(piece):
    if piece is None:
        return 0
    return PIECE_VALUES.get(piece.piece_type, 0)

def queen_development_penalty(board: chess.Board) -> int:
    penalty = 0
    if board.fullmove_number <= 8:
        wq = board.pieces(chess.QUEEN, chess.WHITE)
        bq = board.pieces(chess.QUEEN, chess.BLACK)
        if wq and next(iter(wq)) != chess.D1:
            penalty -= 30
        if bq and next(iter(bq)) != chess.D8:
            penalty += 30
    return penalty

def king_safety(board: chess.Board) -> int:
    # Very simple: prefer castling / discourage king wandering in early-mid game
    score = 0

    # If queens are still on the board, king exposure matters more
    queens_on = bool(board.pieces(chess.QUEEN, chess.WHITE)) and bool(board.pieces(chess.QUEEN, chess.BLACK))
    factor = 2 if queens_on else 1

    wk = board.king(chess.WHITE)
    bk = board.king(chess.BLACK)

    # Penalize white king if not on typical castled squares during early game
    if board.fullmove_number <= 20 and wk is not None:
        if wk in (chess.E1, chess.D1, chess.F1, chess.E2, chess.D2, chess.F2):
            score -= 25 * factor
        if wk in (chess.G1, chess.C1):
            score += 20 * factor

    # Penalize black king if not on typical castled squares during early game
    if board.fullmove_number <= 20 and bk is not None:
        if bk in (chess.E8, chess.D8, chess.F8, chess.E7, chess.D7, chess.F7):
            score += 25 * factor
        if bk in (chess.G8, chess.C8):
            score -= 20 * factor

    return score

def evaluate(board: chess.Board) -> int:
    if board.is_checkmate():
        return -MATE if board.turn else MATE
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0

    # Material
    for pt, v in PIECE_VALUES.items():
        score += len(board.pieces(pt, chess.WHITE)) * v
        score -= len(board.pieces(pt, chess.BLACK)) * v

    # Center occupancy (very simple)
    for sq in CENTER:
        p = board.piece_at(sq)
        if p:
            score += 15 if p.color == chess.WHITE else -15

    # In-check penalty
    if board.is_check():
        score += -30 if board.turn == chess.WHITE else 30

    # Queen early penalty
    score += queen_development_penalty(board)

    # King safety
    score += king_safety(board)

    return score

def score_move(board: chess.Board, move: chess.Move) -> int:
    # Move ordering for better alpha-beta:
    # captures > promotions > checks > everything else, using MVV-LVA-ish
    s = 0

    if board.is_capture(move):
        victim = board.piece_at(move.to_square)
        attacker = board.piece_at(move.from_square)
        s += 10_000 + _piece_value(victim) - (_piece_value(attacker) // 10)

    if move.promotion:
        s += 9_000 + PIECE_VALUES.get(move.promotion, 0)

    board.push(move)
    if board.is_check():
        s += 2_000
    board.pop()

    # small center bias
    if move.to_square in CENTER:
        s += 50

    return s

def max_hanging_loss_1ply(board_after_my_move: chess.Board) -> int:
    # opponent to move; worst immediate capture of OUR piece
    worst = 0
    for r in board_after_my_move.legal_moves:
        if board_after_my_move.is_capture(r):
            captured = board_after_my_move.piece_at(r.to_square)
            val = _piece_value(captured)
            if val > worst:
                worst = val
    return worst

def quiescence(board: chess.Board, alpha: int, beta: int) -> int:
    stand_pat = evaluate(board)
    if stand_pat >= beta:
        return beta
    if alpha < stand_pat:
        alpha = stand_pat

    # only explore captures (and promotions if they are captures/promo moves)
    moves = [m for m in board.legal_moves if board.is_capture(m) or m.promotion]
    moves.sort(key=lambda m: score_move(board, m), reverse=True)

    for move in moves:
        board.push(move)
        score = -quiescence(board, -beta, -alpha)
        board.pop()

        if score >= beta:
            return beta
        if score > alpha:
            alpha = score

    return alpha

def negamax(board: chess.Board, depth: int, alpha: int, beta: int) -> int:
    if depth == 0 or board.is_game_over():
        return quiescence(board, alpha, beta)

    best = -MATE
    moves = list(board.legal_moves)
    moves.sort(key=lambda m: score_move(board, m), reverse=True)

    for move in moves:
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

def choose_move(board: chess.Board, depth: int = 4) -> chess.Move:
    # Opening book
    if board.fullmove_number <= 10:
        m = book_move(board)
        if m is not None and m in board.legal_moves:
            return m

    best_move = None
    best_val = -MATE
    alpha = -MATE
    beta = MATE

    moves = list(board.legal_moves)
    moves.sort(key=lambda m: score_move(board, m), reverse=True)

    for move in moves:
        board.push(move)

        # Strong 1-ply blunder filter: don't hang big pieces for free
        hanging = max_hanging_loss_1ply(board)
        blunder_penalty = 0
        if hanging >= 900:
            blunder_penalty = 2500
        elif hanging >= 500:
            blunder_penalty = 1600
        elif hanging >= 330:
            blunder_penalty = 1000
        elif hanging >= 320:
            blunder_penalty = 900
        elif hanging >= 100:
            blunder_penalty = 200

        val = -negamax(board, depth - 1, -beta, -alpha)
        val2 = val - blunder_penalty

        board.pop()

        if val2 > best_val:
            best_val = val2
            best_move = move

        if best_val > alpha:
            alpha = best_val

    if best_move is None:
        return next(iter(board.legal_moves))
    return best_move
