import mysql.connector
from mysql.connector import Error
from utils.logger import get_logger
import pandas as pd
import os

# --- Logger Setup ---
logger = get_logger(__name__)

# --- Database Configuration ---
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Kdata@2025",  # 🔐 Secure this in production
    "database": "qa_genius"
}

# Configuration for initial connection (without specifying database)
INIT_DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "Kdata@2025"
}

def create_database_if_not_exists():
    """
    Create the qa_genius database if it doesn't exist.
    """
    try:
        conn = mysql.connector.connect(**INIT_DB_CONFIG)
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS qa_genius")
        logger.info("✅ Database 'qa_genius' created or already exists.")
        
        cursor.close()
        conn.close()
        return True
    except Error as e:
        logger.error(f"❌ Failed to create database: {str(e)}")
        return False

def create_tables_if_not_exist():
    """
    Create the required tables if they don't exist.
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Create projects table
        projects_table_sql = """
        CREATE TABLE IF NOT EXISTS projects (
            project_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(projects_table_sql)
        logger.info("✅ Projects table created or already exists.")
        
        # Create test_cases table
        test_cases_table_sql = """
        CREATE TABLE IF NOT EXISTS test_cases (
            id INT AUTO_INCREMENT PRIMARY KEY,
            project_id INT,
            test_case_id VARCHAR(100),
            data_field VARCHAR(255),
            rule_description TEXT,
            sql_script TEXT,
            priority VARCHAR(50),
            status VARCHAR(50),
            execution_date DATE,
            requirement_id VARCHAR(100),
            FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
        )
        """
        cursor.execute(test_cases_table_sql)
        logger.info("✅ Test cases table created or already exists.")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
    except Error as e:
        logger.error(f"❌ Failed to create tables: {str(e)}")
        return False

def initialize_database():
    """
    Initialize the database and tables if they don't exist.
    This function should be called once at application startup.
    """
    logger.info("🔧 Initializing database...")
    
    # Step 1: Create database if it doesn't exist
    if not create_database_if_not_exists():
        return False
    
    # Step 2: Create tables if they don't exist
    if not create_tables_if_not_exist():
        return False
    
    logger.info("✅ Database initialization completed successfully.")
    return True

def get_connection():
    """
    Establish a connection to the MySQL database.
    Automatically initializes database and tables if they don't exist.
    """
    try:
        # Try to connect directly first
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            logger.info("✅ Connected to MySQL database.")
            return conn
    except Error as e:
        # If connection fails, it might be because database doesn't exist
        if "Unknown database" in str(e):
            logger.info("🔧 Database doesn't exist, initializing...")
            if initialize_database():
                # Try connecting again after initialization
                try:
                    conn = mysql.connector.connect(**DB_CONFIG)
                    if conn.is_connected():
                        logger.info("✅ Connected to MySQL database after initialization.")
                        return conn
                except Error as e2:
                    logger.error(f"❌ Database connection failed after initialization: {str(e2)}")
            else:
                logger.error("❌ Failed to initialize database.")
        else:
            logger.error(f"❌ Database connection failed: {str(e)}")
    return None

def insert_project(name: str, description: str) -> int:
    """
    Insert a new project record and return the project_id.
    """
    conn = get_connection()
    if not conn:
        logger.error("❌ Project insert aborted due to DB connection failure.")
        return -1

    try:
        cursor = conn.cursor()
        query = "INSERT INTO projects (name, description, created_at) VALUES (%s, %s, NOW())"
        cursor.execute(query, (name, description))
        conn.commit()
        project_id = cursor.lastrowid
        logger.info(f"🆕 Project inserted successfully — ID={project_id}, Name='{name}'")
        return project_id
    except Error as e:
        logger.error(f"❌ Failed to insert project: {str(e)}")
        return -1
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def insert_test_artifact(project_id: int, row_data: dict) -> bool:
    """
    Insert one row of test case + SQL script into test_cases table.
    """
    conn = get_connection()
    if not conn:
        logger.error("❌ Test artifact insert aborted due to DB connection failure.")
        return False

    try:
        cursor = conn.cursor()
        query = """
            INSERT INTO test_cases (
                project_id,
                test_case_id,
                data_field,
                rule_description,
                sql_script,
                priority,
                status,
                execution_date,
                requirement_id
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            project_id,
            row_data.get("Test Case ID"),
            row_data.get("Data Field"),
            row_data.get("Business Rule (Plain English)"),
            row_data.get("SQL Script(s)"),
            row_data.get("Priority"),
            row_data.get("Status"),
            row_data.get("Execution Date"),
            row_data.get("Requirement ID")
        )
        cursor.execute(query, values)
        conn.commit()
        logger.info(f"✅ Test artifact inserted — {row_data.get('Test Case ID')}")
        return True
    except Error as e:
        logger.error(f"❌ Failed to insert test artifact: {str(e)}")
        return False
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def fetch_all_projects():
    """
    Fetch all projects for dropdown display.
    Returns a list of dicts: [{project_id, name}, ...]
    """
    conn = get_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT project_id, name FROM projects ORDER BY created_at DESC")
        return cursor.fetchall()
    except Error as e:
        logger.error(f"❌ Failed to fetch projects: {str(e)}")
        return []
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

def fetch_test_cases_by_project(project_id: int) -> pd.DataFrame:
    """
    Fetch all test cases for a specific project.
    Returns a DataFrame.
    """
    conn = get_connection()
    if not conn:
        return pd.DataFrame()

    try:
        query = """
            SELECT 
                test_case_id AS `Test Case ID`,
                data_field AS `Data Field`,
                rule_description AS `Business Rule (Plain English)`,
                sql_script AS `SQL Script(s)`,
                priority AS `Priority`,
                status AS `Status`,
                execution_date AS `Execution Date`,
                requirement_id AS `Requirement ID`
            FROM test_cases
            WHERE project_id = %s
        """
        return pd.read_sql(query, conn, params=(project_id,))
    except Error as e:
        logger.error(f"❌ Failed to fetch test cases: {str(e)}")
        return pd.DataFrame()
    finally:
        if conn.is_connected():
            conn.close()
