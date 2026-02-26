# Character AI FastAPI Project

This project provides a FastAPI wrapper for the Character AI API using `PyCharacterAI`.

## Features

- **Authentication**: Uses token from `.env`.
- **Character Management**: Fetch recent chats, my characters, search for characters, and create new ones.
- **Chatting**: Start chats and send messages to characters.

## Installation

1. Install dependencies:
   ```bash
   uv sync
   ```
2. Configure environment:
   Create a `.env` file with:
   ```env
   TOKEN=your_token_here
   WEB_NEXT_AUTH=your_auth_token_here
   ```

## Running the API

Start the FastAPI server:
```bash
uv run run.py
```
The API will be available at `http://localhost:8000`.
You can view the interactive documentation at `http://localhost:8000/docs`.

## Endpoints

### User
- `GET /me`: Get authenticated user information.

### Characters
- `GET /characters/recent`: Fetch recent chats.
- `GET /characters/my`: Fetch characters created by the user.
- `GET /characters/search?query=name`: Search for characters.
- `POST /characters/create`: Create a new character.

### Chat
- `POST /chat/create?character_id=ID`: Start a new chat session.
- `POST /chat/send`: Send a message to a character.
