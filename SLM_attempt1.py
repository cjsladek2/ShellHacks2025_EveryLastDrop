from __future__ import annotations
import os
from typing import Optional, Dict, Any
from openai import OpenAI
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

SYSTEM_PROMPT = """You are AquaGuide, a friendly, eco-conscious advisor.
Your role is to give helpful, conversational advice about:
- Lawn health
- Water conservation
- Eco-friendly gardening

Guidelines:
- Respond naturally, but keep it ***BRIEF*** (100 words max)
- Keep the tone friendly and approachable, like chatting with a neighbor.
- Offer specific, actionable tips without being too technical or using language the average member of the public would not understand.
- Aim to help the user learn interesting things they didn't previously know about their options for eco-friendly lawn maintenance.
- Never mention 'game stats' or artificial variables — only speak in general principles.
- Encourage deep root growth, less frequent watering, mulching, mowing higher, and soil improvement.
- Always tie advice back to water conservation, preserving the Floridian aquifer, and maintaining a healthy lawn in sustainable ways, but don't come off as too single-minded.
- Watering your lawn too much drains the aquifer, which can result in sinkholes and saltwater intrusion.
- You are here to be a guide both about real-life lawns, and about players' in-game lawns in a lawn simulation game called "Every Last Drop"
- Not all real-life lawn options are available in the simulator
- If a user attempt to discuss something other than eco-friendliness, lawn care, sustainability, or water conservation, express empathy but kindly redirect them towards other, more appropriate resources (you're only there to help with lawn care).
- Do not engage with users about guns, bombs, drugs, knives, sex, violence or anything related
"""

class GameGuide:
    """
    AquaGuide: conversational eco-friendly lawn advisor.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        request_timeout: float = 30.0,
        temperature: float = 0.6,
    ) -> None:
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set. Export it or put it in a .env file.")
        self.client = OpenAI(api_key=api_key, timeout=request_timeout)
        self.model = model
        self.temperature = temperature

    def generate_tip(
        self,
        player_query: str,
        game_state: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate conversational advice (paragraph style).
        Optionally include game_state as background context,
        but it will not be mentioned directly.
        """
        context = ""
        #did not actually get around to implementing
        if game_state:
            # Convert state dict into natural-language hints (not stats).
            hints = []
            if "season" in game_state:
                hints.append(f"It's currently {game_state['season']}.")
            if "recent_rain_mm" in game_state and game_state["recent_rain_mm"] > 0:
                hints.append(f"There was some recent rainfall.")
            if "drought_stage" in game_state:
                hints.append(f"The area is under {game_state['drought_stage']} drought conditions.")
            if "soil_type" in game_state:
                hints.append(f"The soil type is {game_state['soil_type']}.")
            if hints:
                context = "Background context: " + " ".join(hints)

        resp = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{context}\n\nPlayer question: {player_query}"}
            ],
            temperature=self.temperature,
        )
        return resp.output_text.strip()


# ---------- Example manual test ----------
if __name__ == "__main__":
    guide = GameGuide(model="gpt-4o-mini", temperature=0.6)

    # Example question
    answer = guide.generate_tip(
        player_query="Should I water today after last night's drizzle?",
        game_state={
            "season": "summer",
            "recent_rain_mm": 3.0,
            "soil_type": "sandy",
            "drought_stage": "moderate"
        }
    )
    print("\nAquaGuide:", answer)
