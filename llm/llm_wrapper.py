import ollama
import logging
import re
import json

MODEL_NAME = "mistral:7b-instruct-q4_0"
TEMPERATURE = 0.2
MAX_TOKENS = 500

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ask_llm(prompt: str, expect_json: bool = False, fallback_field: str = "", fallback_rule: str = "") -> str:
    """
    Sends a prompt to the local Ollama model and returns the response.
    If `expect_json=True`, guarantees JSON structure even if the model returns a broken string.
    """
    try:
        logger.info(f" Prompting model '{MODEL_NAME}' with prompt:\n{prompt[:300]}...")

        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": TEMPERATURE, "num_predict": MAX_TOKENS}
        )

        message = response.get("message", {}).get("content", "").strip()

        if not message:
            logger.warning("⚠️ LLM returned empty content.")
            return json.dumps({
                "test_case_name": fallback_field or "Generated Test",
                "description": f"{fallback_field} must satisfy the rule: {fallback_rule}",
                "test_category": "Accuracy"
            })

        # Strip ```json or ``` wrappers
        message = re.sub(r"^```(?:json|yaml)?\s*", "", message, flags=re.IGNORECASE).strip()
        message = re.sub(r"```$", "", message).strip()

        if expect_json:
            # If it's a plain quoted string, wrap it
            if message.startswith('"') and message.endswith('"'):
                logger.warning("⚠️ Plain string returned — wrapping into fallback JSON.")
                return json.dumps({
                    "test_case_name": message.strip('"'),
                    "description": f"{fallback_field} must satisfy the rule: {fallback_rule}",
                    "test_category": "Accuracy"
                })

            try:
                parsed = json.loads(message)
                if isinstance(parsed, dict) and "test_case_name" in parsed:
                    parsed.setdefault("description", f"{fallback_field} must satisfy the rule: {fallback_rule}")
                    parsed.setdefault("test_category", "Accuracy")
                    return json.dumps(parsed)
            except Exception:
                logger.warning(" JSON parse failed. Using fallback format.")

            return json.dumps({
                "test_case_name": fallback_field or "Generated Test",
                "description": f"{fallback_field} must satisfy the rule: {fallback_rule}",
                "test_category": "Accuracy"
            })

        return message

    except Exception as e:
        logger.error(f" LLM Error: {str(e)}")
        return json.dumps({
            "test_case_name": fallback_field or "Generated Test",
            "description": f"{fallback_field} must satisfy the rule: {fallback_rule}",
            "test_category": "Accuracy"
        })