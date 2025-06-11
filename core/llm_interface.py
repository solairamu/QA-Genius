import ollama

# --- Set model names ---
SQL_MODEL = "mistral:7b-instruct-q4_0"
INSIGHT_MODEL = "mistral:7b-instruct-q4_0"  

# --- Core LLM call ---
def query_llm(prompt: str, model: str = INSIGHT_MODEL) -> str:
    try:
        response = ollama.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}]
        )
        return response['message']['content'].strip()
    except Exception as e:
        return f"ERROR: {str(e)}"

# --- SQL Cleanup Function ---
def clean_sql_response(response: str) -> str:
    cleaned = response.replace("<sql>", "").replace("</sql>", "").strip()

    # Remove markdown-style code block wrappers (```sql ... ```)
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")  # removes all backticks
        if cleaned.lower().startswith("sql"):
            cleaned = cleaned[3:].strip()

    lines = cleaned.splitlines()
    sql_lines = [line for line in lines if not line.strip().startswith(("<s", "#"))]
    cleaned_sql = "\n".join(sql_lines).strip()

    if not cleaned_sql or cleaned_sql.lower().startswith("error"):
        return "SELECT * FROM data_table LIMIT 10"

    return cleaned_sql

# --- SQL Query Generator ---
def generate_sql_query(table_schema: str, question: str) -> str:
    prompt = f"""
You are an expert SQL analyst. Generate a syntactically correct SQL query based on the given schema and user question.

=== SCHEMA START ===
{table_schema}
=== SCHEMA END ===

User Question: "{question}"

Instructions:
- You MUST write valid SQL that answers the user's question, even approximately.
- The data is in a table named `data_table`.
- Use DuckDB SQL syntax only. Do NOT use PostgreSQL-style functions like ::text or to_date().
- Use direct filters like `order_timestamp BETWEEN 'YYYY-MM-DD' AND 'YYYY-MM-DD'` for date conditions.
- Do not output explanations, comments, or special tags — only clean SQL.
- If the question mentions a year, assume `order_timestamp` is a valid column to use for filtering by that year.

SQL:
"""
    raw_sql = query_llm(prompt, model=SQL_MODEL)
    return clean_sql_response(raw_sql)

# --- Data Insight Generator ---
def generate_data_insight(table_schema: str, sample_rows: list, question: str) -> str:
    prompt = f"""
You are a highly accurate and detail-oriented data analyst.

Your task is to analyze the data provided below and answer the user's question with insights derived directly from that data.

=== SCHEMA START ===
{table_schema}
=== SCHEMA END ===

=== DATA START ===
{sample_rows}
=== DATA END ===

User Question: "{question}"

Instructions:
- Only use the data shown to answer the question. Do not assume other records exist.
- If the question refers to a condition that is not met in the data, state that clearly.
- Optionally suggest the closest matching result, but only if it is significantly relevant — and clearly label it as "closest match".
- Never guess or fabricate values.
- Make your response precise, readable, and fact-based.

Insight:
"""
    return query_llm(prompt, model=INSIGHT_MODEL)
