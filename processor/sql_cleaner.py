import re

def clean_generated_sql(sql_text: str) -> str:
    """
    Cleans and normalizes raw SQL text from LLM output.
    Makes it compatible with MySQL and removes unnecessary parts.
    """
    if not sql_text:
        return "-- No script generated"

    # --- Remove markdown/code block formatting ---
    sql_text = sql_text.strip()
    sql_text = sql_text.replace("```sql", "").replace("```", "")
    sql_text = sql_text.replace("<sql>", "").replace("</sql>", "")

    # --- Fix 'N/A' or missing comparisons ---
    sql_text = sql_text.replace("= 'N/A'", "IS NULL").replace("= N/A", "IS NULL")

    # --- Replace IsNumeric() with REGEXP for MySQL-like validation ---
    sql_text = re.sub(r'IsNumeric\((.*?)\)', r"\1 REGEXP '^[0-9]+$'", sql_text)

    # --- Fix COUNT(*) issues if escaped ---
    sql_text = sql_text.replace(r"COUNT(\*)", "COUNT(*)")

    # --- Wrap column names with spaces in backticks ---
    sql_text = re.sub(r'(?<![`])([A-Za-z_]+ [A-Za-z_]+)(?![`])', r'`\1`', sql_text)

    # --- Strip extra semicolons ---
    sql_text = sql_text.strip('; \n') + ";"

    return sql_text