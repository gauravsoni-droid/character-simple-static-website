import os
from dotenv import load_dotenv
import asyncio

from PyCharacterAI import get_client
from PyCharacterAI.exceptions import CreateError, InvalidArgumentError

load_dotenv()

token = os.getenv("TOKEN")
WEB_NEXT_AUTH = os.getenv("WEB_NEXT_AUTH")

if token is None:
    raise RuntimeError("TOKEN environment variable is not set")


def prompt_required(label: str, min_len: int, max_len: int) -> str:
    """Prompt the user for a required field with length validation."""
    while True:
        value = input(f"{label} ({min_len}-{max_len} chars): ").strip()
        if len(value) < min_len or len(value) > max_len:
            print(f"  ⚠ Must be between {min_len} and {max_len} characters. Try again.")
        else:
            return value


def prompt_optional(label: str, max_len: int, min_len: int = 0) -> str:
    """Prompt the user for an optional field. Press Enter to skip."""
    value = input(f"{label} (optional, max {max_len} chars — press Enter to skip): ").strip()
    if not value:
        return ""
    if min_len and len(value) < min_len:
        print(f"  ⚠ Must be at least {min_len} characters. Skipping.")
        return ""
    if len(value) > max_len:
        print(f"  ⚠ Exceeds {max_len} characters. Skipping.")
        return ""
    return value


def prompt_visibility() -> str:
    """Prompt the user to choose character visibility."""
    while True:
        value = input("Visibility [private/unlisted/public] (default: private): ").strip().lower()
        if value == "":
            return "private"
        if value in ("private", "unlisted", "public"):
            return value
        print("  ⚠ Must be one of: private, unlisted, public. Try again.")


def prompt_yes_no(label: str, default: bool = False) -> bool:
    """Prompt the user for a yes/no answer."""
    default_hint = "Y/n" if default else "y/N"
    value = input(f"{label} [{default_hint}]: ").strip().lower()
    if value == "":
        return default
    return value in ("y", "yes")


def collect_character_details() -> dict:
    """Interactively collect all character details from the user."""
    print("\n╔══════════════════════════════════════╗")
    print("║   Create a New Character on C.AI     ║")
    print("╚══════════════════════════════════════╝\n")

    name = prompt_required("Character name", 3, 20)
    greeting = prompt_required("Greeting message", 3, 4096)
    title = prompt_optional("Title", max_len=50, min_len=3)
    description = prompt_optional("Description", max_len=500)
    definition = prompt_optional("Definition / personality", max_len=32000)
    visibility = prompt_visibility()
    copyable = prompt_yes_no("Allow others to copy this character?", default=False)

    return {
        "name": name,
        "greeting": greeting,
        "title": title,
        "description": description,
        "definition": definition,
        "visibility": visibility,
        "copyable": copyable,
    }


async def create_new_character(client):
    # Collect character details before authenticating
    details = collect_character_details()

    # Show summary and confirm
    print("\n── Character Summary ──────────────────")
    print(f"  Name:        {details['name']}")
    print(f"  Greeting:    {details['greeting'][:80]}{'...' if len(details['greeting']) > 80 else ''}")
    if details["title"]:
        print(f"  Title:       {details['title']}")
    if details["description"]:
        print(f"  Description: {details['description'][:80]}{'...' if len(details['description']) > 80 else ''}")
    if details["definition"]:
        print(f"  Definition:  {details['definition'][:80]}{'...' if len(details['definition']) > 80 else ''}")
    print(f"  Visibility:  {details['visibility']}")
    print(f"  Copyable:    {'Yes' if details['copyable'] else 'No'}")
    print("───────────────────────────────────────\n")

    confirm = input("Proceed with character creation? [y/N]: ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Cancelled.")
        return None

    try:
        print("Creating character...")
        character = await client.character.create_character(
            name=details["name"],
            greeting=details["greeting"],
            title=details["title"],
            description=details["description"],
            definition=details["definition"],
            visibility=details["visibility"],
            copyable=details["copyable"],
        )

        print("\n✅ Character created successfully!")
        print(f"  Name:         {character.name}")
        print(f"  Character ID: {character.character_id}")
        return character.character_id

    except (CreateError, InvalidArgumentError) as e:
        print(f"\n❌ Failed to create character: {e}")
        return None
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return None

async def main():
    # Authenticate and create the character
    print("\nConnecting to Character.AI...")
    client = await get_client(token=token, web_next_auth=WEB_NEXT_AUTH)

    try:
        me = await client.account.fetch_me()
        print(f"Authenticated as @{me.username}\n")
        
        char_id = await create_new_character(client)
        if char_id:
            print(f"\nYou can now chat with this character using ID: {char_id}")

    finally:
        await client.close_session()


if __name__ == "__main__":
    asyncio.run(main())
