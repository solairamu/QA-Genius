import ollama
import logging

# --- Model Settings ---
MODEL_NAME = "mistral:7b-instruct-q4_0"
TEMPERATURE = 0.2
MAX_TOKENS = 500

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ask_llm(prompt: str) -> str:
    """
    Sends a prompt to the local Ollama model and returns the plain response text.
    """
    try:
        logger.info(f"🔍 Prompting model '{MODEL_NAME}' with prompt:\n{prompt[:300]}...")

        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            options={
                "temperature": TEMPERATURE,
                "num_predict": MAX_TOKENS
            }
        )

        message = response.get("message", {}).get("content", "").strip()

        if not message:
            logger.warning("⚠️ LLM returned empty content.")
            return "ERROR: No content returned by model"

        # Optional: Clean markdown-style output if LLM wraps response in ``` or YAML
        if message.startswith("```") and message.endswith("```"):
            message = message.strip("```").strip()

        logger.info("✅ LLM response received successfully.")
        return message

    except Exception as e:
        logger.error(f"❌ LLM Error: {str(e)}")
        return f"ERROR: {str(e)}"