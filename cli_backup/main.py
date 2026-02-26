import os
from dotenv import load_dotenv
import asyncio
from PyCharacterAI import get_client
from PyCharacterAI.exceptions import SessionClosedError
from create_character import create_new_character

load_dotenv()

token = os.getenv("TOKEN")
web_next_auth = os.getenv("WEB_NEXT_AUTH")

if token is None:
    raise RuntimeError("TOKEN environment variable is not set")

async def select_character(client):
    while True:
        print("\n=== Character Selection ===")
        print("1. Recent Chats")
        print("2. My Characters")
        print("3. Search Characters")
        print("4. Create New Character")
        print("5. Enter Character ID Manually")
        print("6. Exit")
        
        choice = input("\nSelect an option: ").strip()
        
        if choice == '1':
            recent = await client.chat.fetch_recent_chats()
            if not recent:
                print("No recent chats found.")
                continue
            print("\n--- Recent Chats ---")
            for i, chat in enumerate(recent[:15]):
                print(f"{i+1}. {chat.character_name}")
            
            idx = input("\nSelect character number (or 'b' to go back): ").strip()
            if idx.lower() == 'b': continue
            try:
                return recent[int(idx)-1].character_id
            except (ValueError, IndexError):
                print("Invalid selection.")
                
        elif choice == '2':
            my_chars = await client.account.fetch_my_characters()
            if not my_chars:
                print("No characters found.")
                continue
            print("\n--- My Characters ---")
            for i, char in enumerate(my_chars):
                print(f"{i+1}. {char.name}")
            
            idx = input("\nSelect character number (or 'b' to go back): ").strip()
            if idx.lower() == 'b': continue
            try:
                return my_chars[int(idx)-1].character_id
            except (ValueError, IndexError):
                print("Invalid selection.")
                
        elif choice == '3':
            query = input("Search for character: ").strip()
            if not query: continue
            results = await client.character.search_characters(query)
            if not results:
                print("No characters found.")
                continue
            print(f"\n--- Search Results for '{query}' ---")
            for i, char in enumerate(results[:15]):
                author = getattr(char, 'author_username', 'unknown')
                print(f"{i+1}. {char.name} (@{author}) - {char.title}")
            
            idx = input("\nSelect character number (or 'b' to go back): ").strip()
            if idx.lower() == 'b': continue
            try:
                return results[int(idx)-1].character_id
            except (ValueError, IndexError):
                print("Invalid selection.")
                
        elif choice == '4':
            char_id = await create_new_character(client)
            if char_id:
                return char_id
                
        elif choice == '5':
            char_id = input("Enter Character ID: ").strip()
            if char_id:
                return char_id
                
        elif choice == '6':
            return None
        
        else:
            print("Invalid option. Please try again.")

async def chat_with_character(client, character_id, me):
    chat, greeting_message = await client.chat.create_chat(character_id)

    print(f"\n--- Chatting with {greeting_message.author_name} ---")
    print(f"[{greeting_message.author_name}]: {greeting_message.get_primary_candidate().text}")

    try:
        while True:
            message = input(f"[{me.name}]: ")
            if message.lower() in ["exit", "quit", "/back"]:
                break
            
            answer = await client.chat.send_message(character_id, chat.chat_id, message, streaming=True)

            printed_length = 0
            async for chunk in answer:
                if printed_length == 0:
                    print(f"[{chunk.author_name}]: ", end="")

                text = chunk.get_primary_candidate().text
                print(text[printed_length:], end="")
                printed_length = len(text)
            print("\n")

    except SessionClosedError:
        print("Session closed.")

async def main():
    client = await get_client(token=token, web_next_auth=web_next_auth)
    try:
        me = await client.account.fetch_me()
        print(f'Authenticated as @{me.username}')

        while True:
            character_id = await select_character(client)
            if character_id:
                await chat_with_character(client, character_id, me)
                print("\nReturned to menu.")
            else:
                break

    finally:
        await client.close_session()

if __name__ == "__main__":
    asyncio.run(main())