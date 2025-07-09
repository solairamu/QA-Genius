import mysql.connector
from mysql.connector import Error
from utils.logger import get_logger
import pandas as pd
import shutil
import os

# --- Logger Setup ---
logger = get_logger(__name__)

# --- Database Configuration ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Kdata@2025",
    "database": "qa_genius_v3"
}

def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            logger.info("Connected to MySQL database.")
            return conn
    except Error as e:
        logger.error(f" Database connection failed: {str(e)}")
    return None

def insert_project(name: str, description: str, mapping_file: str = None, brd_file: str = None) -> int:
    conn = get_connection()
    if not conn:
        logger.error(" Project insert aborted due to DB connection failure.")
        return -1
    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO projects (name, description, mapping_file, brd_file, created_at)
            VALUES (%s, %s, %s, %s, NOW())
        """
        cursor.execute(query, (name, description, mapping_file, brd_file))
        conn.commit()
        project_key = cursor.lastrowid
        logger.info(f" Project inserted — ID={project_key}, Name='{name}'")
        return project_key
    except Error as e:
        logger.error(f" Failed to insert project: {str(e)}")
        return -1
    finally:
        cursor.close()
        conn.close()

def update_uploaded_files(project_key: int, mapping_file: str, brd_file: str):
    conn = get_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        query = """
            UPDATE projects
            SET mapping_file = %s, brd_file = %s
            WHERE project_key = %s
        """
        cursor.execute(query, (mapping_file, brd_file, project_key))
        conn.commit()
        logger.info(f" Updated uploaded file names for project_key={project_key}")
    except Error as e:
        logger.error(f" Failed to update uploaded files: {e}")
    finally:
        cursor.close()
        conn.close()

def get_next_test_script_id(project_key: int, conn) -> str:
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT test_script_id FROM test_cases
            WHERE project_key = %s AND test_script_id IS NOT NULL
            ORDER BY id DESC LIMIT 1
        """, (project_key,))
        result = cursor.fetchone()
        cursor.close()
        if result and result[0]:
            last_num = int(result[0].replace("SQL", ""))
            return f"SQL{last_num + 1:03d}"
        return "SQL001"
    except Exception as e:
        logger.error(f" Failed to generate test_script_id: {e}")
        return "SQL001"

def insert_test_artifact(project_key: int, row_data: dict) -> bool:
    conn = get_connection()
    if not conn:
        logger.error(" Test artifact insert aborted due to DB connection failure.")
        return False
    try:
        test_script_id = get_next_test_script_id(project_key, conn)
        cursor = conn.cursor()
        query = """
            INSERT INTO test_cases (
                project_key,
                test_case_id,
                test_case_name,
                description,
                table_name,
                column_name,
                test_category,
                test_script_id,
                test_script_sql,
                requirement_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            project_key,
            row_data.get("test_case_id"),
            row_data.get("test_case_name"),
            row_data.get("description"),
            row_data.get("table_name"),
            row_data.get("column_name"),
            row_data.get("test_category"),
            test_script_id,
            row_data.get("test_script_sql"),
            row_data.get("requirement_id")
        )
        cursor.execute(query, values)
        conn.commit()
        logger.info(f" Test artifact inserted — {row_data.get('test_case_id')} ({test_script_id})")
        return True
    except Error as e:
        logger.error(f" Failed to insert test artifact: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def fetch_all_projects():
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT project_key, name, description, mapping_file, brd_file, created_at 
            FROM projects ORDER BY created_at DESC
        """)
        return cursor.fetchall()
    except Error as e:
        logger.error(f" Failed to fetch projects: {str(e)}")
        return []
    finally:
        cursor.close()
        conn.close()

def fetch_test_cases_by_project(project_key: int) -> pd.DataFrame:
    conn = get_connection()
    if not conn:
        return pd.DataFrame()
    try:
        query = """
            SELECT 
                test_case_id AS `Test Case ID`,
                test_case_name AS `Test Case Name`,
                description AS `Description`,
                table_name AS `Table Name`,
                column_name AS `Column Name`,
                test_category AS `Test Category`,
                test_script_id AS `Test Script ID`,
                test_script_sql AS `Test Script (SQL)`,
                requirement_id AS `Requirement ID`,
                project_key AS `Project Key`
            FROM test_cases
            WHERE project_key = %s
        """
        df = pd.read_sql(query, conn, params=(project_key,))
        return df
    except Error as e:
        logger.error(f" Failed to fetch test cases: {str(e)}")
        return pd.DataFrame()
    finally:
        conn.close()

def delete_project_and_artifacts(project_key: int) -> bool:
    conn = get_connection()
    if not conn:
        return False
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM test_cases WHERE project_key = %s", (project_key,))
        cursor.execute("DELETE FROM projects WHERE project_key = %s", (project_key,))
        conn.commit()

        # --- Delete uploaded files folder ---
        upload_dir = f"uploads/project_{project_key}"
        if os.path.exists(upload_dir):
            shutil.rmtree(upload_dir)
            logger.info(f" Deleted file folder: {upload_dir}")

        logger.info(f" Deleted project and artifacts for project_key = {project_key}")
        return True
    except Error as e:
        logger.error(f" Failed to delete project and artifacts: {str(e)}")
        return False
    finally:
        cursor.close()
        conn.close()

def fetch_all_project_keys_in_test_cases() -> list:
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT project_key FROM test_cases")
        keys = [row[0] for row in cursor.fetchall()]
        return keys
    except Error as e:
        logger.error(f" Failed to fetch project keys from test_cases: {str(e)}")
        return []
    finally:
        cursor.close()
        conn.close()

def initialize_database():
    """Initialize the database and create tables if they don't exist"""
    try:
        # First connect without specifying database to create it if needed
        config_without_db = DB_CONFIG.copy()
        database_name = config_without_db.pop('database')
        
        conn = mysql.connector.connect(**config_without_db)
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name}")
        cursor.execute(f"USE {database_name}")
        
        logger.info(f"Database '{database_name}' created or already exists")
        
        # Create tables if they don't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_key INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                mapping_file VARCHAR(255),
                brd_file VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_cases (
                id INT AUTO_INCREMENT PRIMARY KEY,
                project_key INT,
                test_case_id VARCHAR(100),
                test_case_name VARCHAR(255),
                description TEXT,
                table_name VARCHAR(255),
                column_name VARCHAR(255),
                test_category VARCHAR(100),
                test_script_id VARCHAR(100),
                test_script_sql TEXT,
                requirement_id VARCHAR(100),
                FOREIGN KEY (project_key) REFERENCES projects(project_key) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        logger.info("Database tables created or already exist")
        
    except Error as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()