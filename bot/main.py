import os
import json
import time
import threading
import urllib.request

import chess
from player import choose_move

TOKEN = os.environ.get("LICHESS_TOKEN")
if not TOKEN:
    print("Token not found")
    raise SystemExit(1)

def api_get(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={"Authorization": "Bearer " + TOKEN}
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))

def api_post(url: str) -> str:
    req = urllib.request.Request(
        url,
        method="POST",
        headers={"Authorization": "Bearer " + TOKEN}
    )
    with urllib.request.urlopen(req) as res:
        return res.read().decode("utf-8")

def stream_lines(url: str):
    req = urllib.request.Request(
        url,
        headers={"Authorization": "Bearer " + TOKEN}
    )
    with urllib.request.urlopen(req) as res:
        for raw in res:
            line = raw.decode("utf-8").strip()
            if not line:
                continue
            yield line

def accept_challenge(challenge_id: str):
    return api_post(f"https://lichess.org/api/challenge/{challenge_id}/accept")

def play_move(game_id: str, uci: str):
    return api_post(f"https://lichess.org/api/bot/game/{game_id}/move/{uci}")

def build_board(initial_fen: str, moves_uci: str) -> chess.Board:
    if initial_fen and initial_fen != "startpos":
        board = chess.Board(initial_fen)
    else:
        board = chess.Board()

    if moves_uci:
        for uci in moves_uci.split():
            try:
                board.push_uci(uci)
            except Exception:
                break
    return board

def game_worker(game_id: str, my_username: str):
    url = f"https://lichess.org/api/bot/game/stream/{game_id}"
    print("Game started:", game_id)

    my_color = None
    initial_fen = "startpos"
    last_played_moves = ""

    for line in stream_lines(url):
        event = json.loads(line)
        t = event.get("type")

        if t == "gameFull":
            white_name = (event.get("white") or {}).get("name")
            black_name = (event.get("black") or {}).get("name")
            if white_name == my_username:
                my_color = "white"
            elif black_name == my_username:
                my_color = "black"
            else:
                my_color = None

            initial_fen = event.get("initialFen", "startpos")
            state = event.get("state", {}) or {}
            last_played_moves = state.get("moves", "") or ""

        elif t == "gameState":
            last_played_moves = event.get("moves", "") or ""

        else:
            continue

        if my_color is None:
            continue

        status = event.get("status") or (event.get("state", {}) or {}).get("status")
        if status in ("mate", "resign", "stalemate", "draw", "timeout", "aborted"):
            print("Game ended:", game_id, "status:", status)
            return

        board = build_board(initial_fen, last_played_moves)

        is_my_turn = (board.turn == chess.WHITE and my_color == "white") or (board.turn == chess.BLACK and my_color == "black")
        if not is_my_turn:
            continue

        if board.is_game_over():
            print("Game over (board):", game_id)
            return

        try:
            move = choose_move(board, depth=3)
            uci = move.uci()
            play_move(game_id, uci)
            print("Played", uci, "in", game_id)
            time.sleep(0.2)
        except Exception as e:
            print("Move failed:", e)
            time.sleep(1.0)

def main():
    me = api_get("https://lichess.org/api/account")
    my_username = me.get("username")
    print("Connected as:", my_username)
    print("Bot online. Waiting for challenges...")

    for line in stream_lines("https://lichess.org/api/stream/event"):
        event = json.loads(line)
        et = event.get("type")

        if et == "challenge":
            ch = event.get("challenge", {}) or {}
            ch_id = ch.get("id")
            challenger = (ch.get("challenger", {}) or {}).get("name")
            print("Challenge from:", challenger, "id:", ch_id)
            if ch_id:
                try:
                    accept_challenge(ch_id)
                    print("Accepted challenge:", ch_id)
                except Exception as e:
                    print("Failed to accept:", e)

        elif et == "gameStart":
            game = event.get("game", {}) or {}
            game_id = game.get("id")
            if game_id:
                th = threading.Thread(target=game_worker, args=(game_id, my_username), daemon=True)
                th.start()

if __name__ == "__main__":
    main()
