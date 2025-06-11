import mysql.connector
from datetime import datetime

# --- DB CONNECTION ---
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Kdata@2025",
        database="ai_product_db"
    )

# --- Project Insert ---
def insert_new_project(project_name, project_description):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO projects (project_name, project_description) VALUES (%s, %s)",
        (project_name, project_description)
    )
    project_id = cursor.lastrowid
    conn.commit()
    cursor.close()
    conn.close()
    return project_id

# --- File Insert ---
def insert_file(project_id, file_type, file_name, file_path):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO files (project_id, file_type, file_name, file_path) VALUES (%s, %s, %s, %s)",
        (project_id, file_type, file_name, file_path)
    )
    conn.commit()
    cursor.close()
    conn.close()

# --- Get All Projects ---
def get_all_projects():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.project_id, p.project_name, p.project_description, p.created_at,
               GROUP_CONCAT(CASE WHEN f.file_type='source' THEN f.file_name END) AS source_files,
               GROUP_CONCAT(CASE WHEN f.file_type='mapping' THEN f.file_name END) AS mapping_files
        FROM projects p
        LEFT JOIN files f ON p.project_id = f.project_id
        GROUP BY p.project_id
        ORDER BY p.created_at DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

# --- Get Project Metadata ---
def get_project_by_id(project_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM projects WHERE project_id = %s", (project_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

# --- Get File Paths ---
def get_project_files(project_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM files WHERE project_id = %s", (project_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

# --- Insert AI Query Log ---
def log_ai_query(project_id, question, response):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO ai_logs (project_id, question, response, created_at) VALUES (%s, %s, %s, %s)",
        (project_id, question, response, datetime.now())
    )
    conn.commit()
    cursor.close()
    conn.close()

# --- Fetch Validation Rules ---
def fetch_validation_rules():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT column_name, data_type, rule FROM validation_rules")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

# --- Delete Project by ID ---
def delete_project_by_id(project_id):
    conn = get_connection()
    cursor = conn.cursor()

    # Delete files linked to project
    cursor.execute("DELETE FROM files WHERE project_id = %s", (project_id,))
    
    # Delete AI logs if applicable
    cursor.execute("DELETE FROM ai_logs WHERE project_id = %s", (project_id,))

    # Delete project
    cursor.execute("DELETE FROM projects WHERE project_id = %s", (project_id,))

    conn.commit()
    cursor.close()
    conn.close()
