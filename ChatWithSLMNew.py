import re
import unicodedata
from SLM_attempt1 import GameGuide

import re
import unicodedata

import re
import unicodedata

def sanitize_output(text: str) -> str:
    """
    Clean model output for Pygame display:
    - Normalize Unicode width (fullwidth → ASCII width).
    - Replace curly quotes/apostrophes/dashes with straight ASCII.
    - Remove emojis and truly non-ASCII symbols.
    - Preserve apostrophes, quotes, commas, etc.
    """
    if text is None:
        return ""

    # Step 1: Normalize fullwidth forms (１２３ → 123, ， → , etc.)
    normalized = unicodedata.normalize("NFKC", str(text))

    # Step 2: Replace common curly punctuation explicitly
    replacements = {
        "‘": "'", "’": "'",  # single quotes
        "“": '"', "”": '"',  # double quotes
        "–": "-", "—": "-",  # dashes
        "…": "...",          # ellipsis
        " ": " ",            # non-breaking space → normal space
    }
    for bad, good in replacements.items():
        normalized = normalized.replace(bad, good)

    # Step 3: Remove characters outside ASCII (but keep \n)
    cleaned = re.sub(r"[^\x20-\x7E\n]", "", normalized)

    # Step 4: Remove stray asterisks
    cleaned = cleaned.replace("*", "")

    return cleaned



# Initialize your guide
guide = GameGuide(model="gpt-4o-mini", temperature=0.6)


def chat_with_slm(user_input: str) -> str:
    """
    Send a prompt to GameGuide and return a sanitized response.
    """
    try:
        # Your GameGuide exposes generate_tip(), so use that
        raw = guide.generate_tip(user_input)

        # Clean the output for pygame safety
        cleaned = sanitize_output(raw)

        return cleaned if cleaned.strip() else "[No valid response after sanitization]"
    except Exception as e:
        return sanitize_output(f"[Error contacting SLM: {e.__class__.__name__}: {e}]")


# Optional console loop
if __name__ == "__main__":
    print("AquaGuide is online! Type 'quit' to exit.\n")
    while True:
        q = input("You: ")
        if q.strip().lower() in {"quit", "exit"}:
            print("Goodbye!")
            break
        print("AquaGuide:", chat_with_slm(q), "\n")

