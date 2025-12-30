# AI Chess Bot (Lichess)

AI-driven chess bot developed for the Artificial Intelligence course.
The bot connects to Lichess using the python-lichess library and plays
games using a custom AI decision-making algorithm.

## Features
- Connects to Lichess as a bot account
- Plays games automatically
- Uses an AI-based algorithm to select moves (not a hardcoded engine)

## Requirements
- Python 3.10+
- Lichess account with API token
- python-lichess
- python-chess

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
