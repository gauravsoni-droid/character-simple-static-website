import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio

from PyCharacterAI import get_client
from PyCharacterAI.exceptions import SessionClosedError, CreateError, InvalidArgumentError

load_dotenv()

TOKEN = os.getenv("TOKEN")
WEB_NEXT_AUTH = os.getenv("WEB_NEXT_AUTH")

if TOKEN is None:
    raise RuntimeError("TOKEN environment variable is not set")

class CharacterInfo(BaseModel):
    character_id: str
    name: str
    title: Optional[str] = None
    description: Optional[str] = None
    author_username: Optional[str] = None

class ChatMessage(BaseModel):
    character_id: str
    chat_id: str
    message: str

class CreateCharacterRequest(BaseModel):
    name: str
    greeting: str
    title: Optional[str] = ""
    description: Optional[str] = ""
    definition: Optional[str] = ""
    visibility: str = "private"
    copyable: bool = False

class AppState:
    def __init__(self):
        self.client = None
        self.me = None

state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    state.client = await get_client(token=TOKEN, web_next_auth=WEB_NEXT_AUTH)
    state.me = await state.client.account.fetch_me()
    print(f"Authenticated as @{state.me.username}")
    yield
    # Shutdown
    if state.client:
        await state.client.close_session()

app = FastAPI(title="Character AI API", lifespan=lifespan)

# Mount static files
if not os.path.exists("static"):
    os.makedirs("static")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/me")
async def get_me():
    if not state.me:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {
        "username": state.me.username,
        "name": state.me.name,
        "bio": getattr(state.me, 'bio', ''),
        # If avatar_url is missing, we'll return None and let frontend use a default
        "avatar_url": getattr(state.me, 'avatar_url', None)
    }

@app.get("/characters/recent", response_model=List[CharacterInfo])
async def get_recent_chats():
    try:
        recent = await state.client.chat.fetch_recent_chats()
        return [
            CharacterInfo(
                character_id=chat.character_id,
                name=chat.character_name,
                title=None, 
                description=None,
                author_username=None
            ) for chat in recent
        ]
    except Exception as e:
        print(f"Error fetching recent: {e}")
        return []

@app.get("/characters/my", response_model=List[CharacterInfo])
async def get_my_characters():
    try:
        my_chars = await state.client.account.fetch_my_characters()
        return [
            CharacterInfo(
                character_id=char.character_id,
                name=char.name,
                title=char.title,
                description=getattr(char, 'description', None),
                author_username=state.me.username
            ) for char in my_chars
        ]
    except Exception as e:
        print(f"Error fetching my chars: {e}")
        return []

@app.get("/characters/search", response_model=List[CharacterInfo])
async def search_characters(query: str = Query(..., min_length=1)):
    try:
        results = await state.client.character.search_characters(query)
        return [
            CharacterInfo(
                character_id=char.character_id,
                name=char.name,
                title=char.title,
                description=getattr(char, 'description', None),
                author_username=getattr(char, 'author_username', 'unknown')
            ) for char in results
        ]
    except Exception as e:
        print(f"Error searching chars: {e}")
        return []

@app.post("/chat/create")
async def create_chat(character_id: str):
    try:
        chat, greeting_message = await state.client.chat.create_chat(character_id)
        return {
            "chat_id": chat.chat_id,
            "character_name": greeting_message.author_name,
            "greeting": greeting_message.get_primary_candidate().text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/send")
async def send_message(request: ChatMessage):
    async def event_generator():
        last_text = ""
        try:
            # send_message is an async function that returns an AsyncGenerator when streaming=True
            # We must await it first to get the generator
            generator = await state.client.chat.send_message(
                request.character_id, 
                request.chat_id, 
                request.message, 
                streaming=True
            )
            async for answer in generator:
                new_text = answer.get_primary_candidate().text
                if new_text.startswith(last_text):
                    chunk = new_text[len(last_text):]
                    if chunk:
                        yield chunk
                        # Add a tiny delay to slow down the streaming
                        await asyncio.sleep(0.03) 
                else:
                    # Fallback if structure changes unexpectedly
                    yield new_text
                last_text = new_text
        except SessionClosedError:
            yield " [Session closed]"
        except Exception as e:
            yield f" [Error: {str(e)}]"

    return StreamingResponse(event_generator(), media_type="text/plain")

@app.post("/characters/create")
async def create_character(req: CreateCharacterRequest):
    try:
        character = await state.client.character.create_character(
            name=req.name,
            greeting=req.greeting,
            title=req.title,
            description=req.description,
            definition=req.definition,
            visibility=req.visibility,
            copyable=req.copyable,
        )
        return {
            "character_id": character.character_id,
            "name": character.name
        }
    except (CreateError, InvalidArgumentError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
