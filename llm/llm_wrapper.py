import ollama
import logging
import re
import json

MODEL_NAME = "mistral:7b-instruct-q4_0"
TEMPERATURE = 0.2
MAX_TOKENS = 500

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def ask_llm(prompt: str, expect_json: bool = False, fallback_field: str = "", fallback_rule: str = "") -> dict | str:
    """
    Sends a prompt to the local Ollama model and returns the response.
    If `expect_json=True`, attempts to parse JSON and return a dict.
    Otherwise, returns plain string response.
    """
    try:
        logger.info(f"\n📤 Prompt sent to LLM ({MODEL_NAME}):\n{prompt}\n")

        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": TEMPERATURE, "num_predict": MAX_TOKENS}
        )

        message = response.get("message", {}).get("content", "").strip()

        if not message:
            logger.warning("⚠️ LLM returned empty content.")
            return {
                "test_case_name": fallback_field or "Generated Test",
                "description": f"The field '{fallback_field}' must follow the rule: {fallback_rule}",
                "test_category": "Accuracy"
            } if expect_json else ""

        # Clean any markdown/code block wrappers like ```json ... ```
        message = re.sub(r"^```(?:json|yaml)?", "", message, flags=re.IGNORECASE).strip()
        message = re.sub(r"```$", "", message).strip()

        # Try to parse JSON if required
        if expect_json:
            if isinstance(message, dict):
                return message  # Already a dict (not common)

            # Handle if LLM returns a string wrapped in quotes
            if message.startswith('"') and message.endswith('"'):
                logger.warning("⚠️ LLM returned a quoted string instead of a JSON object.")
                return {
                    "test_case_name": message.strip('"'),
                    "description": f"The field '{fallback_field}' must follow the rule: {fallback_rule}",
                    "test_category": "Accuracy"
                }

            try:
                parsed = json.loads(message)
                if isinstance(parsed, dict) and "test_case_name" in parsed:
                    parsed.setdefault("description", f"The field '{fallback_field}' must follow the rule: {fallback_rule}")
                    parsed.setdefault("test_category", "Accuracy")
                    return parsed
                else:
                    raise ValueError("Parsed object missing required keys.")
            except Exception as e:
                logger.warning(f"❌ JSON parse failed: {e}\n📥 Raw message: {message}")

            # Fallback response if parsing fails
            return {
                "test_case_name": fallback_field or "Generated Test",
                "description": f"The field '{fallback_field}' must follow the rule: {fallback_rule}",
                "test_category": "Accuracy"
            }

        # If not expecting JSON, return as plain text
        return message

    except Exception as e:
        logger.error(f"❌ LLM Request Failed: {str(e)}")
        return {
            "test_case_name": fallback_field or "Generated Test",
            "description": f"The field '{fallback_field}' must follow the rule: {fallback_rule}",
            "test_category": "Accuracy"
        } if expect_json else ""