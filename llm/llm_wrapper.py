import ollama
import logging

# --- Model Settings ---
MODEL_NAME = "mistral:7b-instruct-q4_0"
TEMPERATURE = 0.2
MAX_TOKENS = 500

# --- Logging Setup (optional for debugging) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ask_llm(prompt: str) -> str:
    """
    Sends a prompt to the local Ollama model and returns the plain response text.

    Args:
        prompt (str): The natural language instruction to send to the model.

    Returns:
        str: LLM-generated output or error string.
    """
    try:
        logger.info(f"🔍 Prompting model '{MODEL_NAME}'...")

        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "user", "content": prompt}
            ],
            options={
                "temperature": TEMPERATURE,
                "num_predict": MAX_TOKENS
            }
        )

        message = response.get("message", {}).get("content", "").strip()

        if not message:
            logger.warning("⚠️ LLM returned empty content.")
            return "ERROR: No content returned by model"

        logger.info("✅ LLM response received successfully.")
        return message

    except Exception as e:
        logger.error(f"❌ LLM Error: {str(e)}")
        return f"ERROR: {str(e)}"
