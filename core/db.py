import mysql.connector
from datetime import datetime
import json

# ----------------- DB CONNECTION -----------------
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Kdata@2025",
        database="ai_product_db"
    )

def create_database_if_not_exists():
    """
    Create the database if it doesn't exist.
    """
    try:
        # Connect without specifying database
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Kdata@2025"
        )
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS ai_product_db")
        cursor.execute("USE ai_product_db")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("[SUCCESS] Database 'ai_product_db' created/verified successfully!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to create database: {e}")
        return False

def get_connection_safe():
    """
    Get database connection with automatic database creation if needed.
    """
    try:
        return get_connection()
    except mysql.connector.Error as e:
        if "Unknown database" in str(e):
            print("[INFO] Database not found, creating it...")
            if create_database_if_not_exists():
                return get_connection()
            else:
                raise e
        else:
            raise e

# ----------------- AUTO TABLE CREATION -----------------
def create_tables_if_not_exist():
    """
    Automatically create all required tables if they don't exist.
    This ensures the application works out of the box for new users.
    """
    conn = get_connection_safe()
    cursor = conn.cursor()
    
    try:
        # 1. Create projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                project_id INT AUTO_INCREMENT PRIMARY KEY,
                project_name VARCHAR(255) NOT NULL,
                project_description TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Create files table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                file_id INT AUTO_INCREMENT PRIMARY KEY,
                project_id INT NOT NULL,
                file_type VARCHAR(50) NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                file_path TEXT NOT NULL,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            )
        """)
        
        # 3. Create validation_rules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS validation_rules (
                rule_id INT AUTO_INCREMENT PRIMARY KEY,
                project_id INT NOT NULL,
                column_name VARCHAR(255),
                rule_type VARCHAR(100),
                friendly_rule_name VARCHAR(255),
                dimension VARCHAR(100),
                number_of_rows_passed INT DEFAULT 0,
                number_of_rows_failed INT DEFAULT 0,
                total_rows_evaluated INT DEFAULT 0,
                passed_score DECIMAL(5,2) DEFAULT 0.00,
                failed_score DECIMAL(5,2) DEFAULT 0.00,
                rule_application_status VARCHAR(50) DEFAULT 'Pending',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            )
        """)
        
        # 4. Create ai_logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_logs (
                log_id INT AUTO_INCREMENT PRIMARY KEY,
                project_id INT NOT NULL,
                question TEXT,
                response TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            )
        """)
        
        # 5. Create test_case_batches table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_case_batches (
                batch_id INT AUTO_INCREMENT PRIMARY KEY,
                project_id INT NOT NULL,
                batch_name VARCHAR(255) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                test_case_count INT DEFAULT 0,
                sql_validation_count INT DEFAULT 0,
                FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE
            )
        """)
        
        # 6. Create test_cases table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_cases (
                test_case_id INT AUTO_INCREMENT PRIMARY KEY,
                batch_id INT NOT NULL,
                test_id VARCHAR(50),
                category VARCHAR(100),
                title TEXT,
                description TEXT,
                steps JSON,
                expected_result TEXT,
                severity VARCHAR(20) DEFAULT 'Medium',
                FOREIGN KEY (batch_id) REFERENCES test_case_batches(batch_id) ON DELETE CASCADE
            )
        """)
        
        # 7. Create sql_validations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sql_validations (
                sql_validation_id INT AUTO_INCREMENT PRIMARY KEY,
                batch_id INT NOT NULL,
                test_id VARCHAR(50),
                query_sql TEXT,
                description TEXT,
                FOREIGN KEY (batch_id) REFERENCES test_case_batches(batch_id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        print("[SUCCESS] All database tables created/verified successfully!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to create tables: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def check_and_setup_database():
    """
    Check if all required tables exist and create them if they don't.
    This function should be called when the application starts.
    """
    try:
        conn = get_connection_safe()
        cursor = conn.cursor()
        
        # Check if main tables exist
        cursor.execute("SHOW TABLES")
        existing_tables = [table[0] for table in cursor.fetchall()]
        
        required_tables = [
            'projects', 'files', 'validation_rules', 'ai_logs',
            'test_case_batches', 'test_cases', 'sql_validations'
        ]
        
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        cursor.close()
        conn.close()
        
        if missing_tables:
            print(f"[INFO] Missing tables detected: {missing_tables}")
            print("[INFO] Creating missing database tables...")
            return create_tables_if_not_exist()
        else:
            print("[INFO] All required database tables exist")
            return True
            
    except Exception as e:
        print(f"[WARNING] Could not verify database tables: {e}")
        print("[INFO] Attempting to create tables anyway...")
        return create_tables_if_not_exist()

# Initialize database on module import
try:
    database_status = check_and_setup_database()
    if database_status:
        print("[INFO] QA Genius database is ready!")
    else:
        print("[WARNING] Database setup incomplete - some features may not work")
except Exception as e:
    print(f"[WARNING] Database auto-setup failed: {e}")
    print("[INFO] You may need to check your MySQL connection and credentials")

# ----------------- PROJECT & FILE OPERATIONS -----------------

def insert_new_project(project_name, project_description):
    conn = get_connection()
    cursor = conn.cursor()

    # Insert basic info first
    cursor.execute(
        "INSERT INTO projects (project_name, project_description) VALUES (%s, %s)",
        (project_name, project_description)
    )
    project_id = cursor.lastrowid

    # Don't try to update project_path column since it doesn't exist
    # The project path will be generated dynamically when needed

    conn.commit()
    cursor.close()
    conn.close()
    return project_id


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

def get_all_projects():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT p.project_id, p.project_name, p.project_description, p.created_at,
               GROUP_CONCAT(CASE WHEN f.file_type='source' THEN f.file_name END) AS source_files,
               GROUP_CONCAT(CASE WHEN f.file_type='mapping' THEN f.file_name END) AS mapping_files,
               GROUP_CONCAT(CASE WHEN f.file_type='business_rules' THEN f.file_name END) AS business_rules_files
        FROM projects p
        LEFT JOIN files f ON p.project_id = f.project_id
        GROUP BY p.project_id
        ORDER BY p.created_at DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def get_project_by_id(project_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM projects WHERE project_id = %s", (project_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

def get_project_files(project_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM files WHERE project_id = %s", (project_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def delete_project_by_id(project_id):
    conn = get_connection()
    cursor = conn.cursor()

    # Step 1: Delete from dependent child tables (with error handling)
    try:
        cursor.execute("DELETE FROM validation_rules WHERE project_id = %s", (project_id,))
    except Exception as e:
        print(f"[WARNING] Could not delete validation rules: {e}")
        
    try:
        cursor.execute("DELETE FROM files WHERE project_id = %s", (project_id,))
    except Exception as e:
        print(f"[WARNING] Could not delete files: {e}")
        
    try:
        cursor.execute("DELETE FROM ai_logs WHERE project_id = %s", (project_id,))
    except Exception as e:
        print(f"[WARNING] Could not delete ai_logs: {e}")

    # Step 2: Delete from parent table
    cursor.execute("DELETE FROM projects WHERE project_id = %s", (project_id,))

    # Finalize
    conn.commit()
    cursor.close()
    conn.close()

# ----------------- AI LOGGING -----------------

def log_ai_query(project_id, question, response):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO ai_logs (project_id, question, response, created_at) VALUES (%s, %s, %s, %s)",
            (project_id, question, response, datetime.now())
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[WARNING] Could not log AI query: {e}")

# ----------------- VALIDATION RULE METRICS -----------------

def rule_exists(column_name, rule_type, dimension, project_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM validation_rules
            WHERE column_name = %s AND rule_type = %s AND dimension = %s AND project_id = %s
        """, (column_name, rule_type, dimension, project_id))
        exists = cursor.fetchone()[0] > 0
        cursor.close()
        conn.close()
        return exists
    except Exception as e:
        print(f"[WARNING] Could not check validation rules: {e}")
        return False

def insert_validation_rule(project_id, column_name, rule_type, friendly_rule_name, dimension):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO validation_rules (
                project_id, column_name, rule_type, friendly_rule_name, dimension,
                number_of_rows_passed, number_of_rows_failed, total_rows_evaluated,
                passed_score, failed_score, rule_application_status
            ) VALUES (%s, %s, %s, %s, %s, 0, 0, 0, 0, 0, 'Pending')
        """, (project_id, column_name, rule_type, friendly_rule_name, dimension))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[WARNING] Could not insert validation rule: {e}")

def update_validation_metrics(column_name, rule_type, dimension, valid_count, invalid_count, null_count, total, score, project_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        print(f"[UPDATE] {column_name} | {rule_type} | {dimension} | Score: {score} | Total: {total}")
        cursor.execute("""
            UPDATE validation_rules
            SET number_of_rows_passed = %s,
                number_of_rows_failed = %s,
                total_rows_evaluated = %s,
                passed_score = %s,
                failed_score = %s,
                rule_application_status = %s
            WHERE column_name = %s AND rule_type = %s AND dimension = %s AND project_id = %s
        """, (
            valid_count, invalid_count, total,
            score, round(100 - score, 2),
            "Rule Applied",
            column_name, rule_type, dimension, project_id
        ))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Failed to update metrics: {e}")

def clear_validation_rules(project_id):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM validation_rules WHERE project_id = %s", (project_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[WARNING] Could not clear validation rules: {e}")

# ----------------- TEST CASE BATCH OPERATIONS -----------------

def save_test_case_batch(project_id, batch_name, test_cases_data):
    """
    Save a batch of test cases and SQL validations for a project.
    Returns the batch_id of the saved batch.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Insert batch record
        cursor.execute("""
            INSERT INTO test_case_batches (project_id, batch_name, created_at, test_case_count, sql_validation_count)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            project_id, 
            batch_name, 
            datetime.now(),
            len(test_cases_data.get('test_cases', [])),
            len(test_cases_data.get('sql_validations', []))
        ))
        batch_id = cursor.lastrowid
        
        # Save individual test cases
        for test_case in test_cases_data.get('test_cases', []):
            cursor.execute("""
                INSERT INTO test_cases (
                    batch_id, test_id, category, title, description, 
                    steps, expected_result, severity
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                batch_id,
                test_case.get('id', ''),
                test_case.get('category', ''),
                test_case.get('title', ''),
                test_case.get('description', ''),
                json.dumps(test_case.get('steps', [])),
                test_case.get('expected_result', ''),
                test_case.get('severity', 'Medium')
            ))
        
        # Save SQL validations
        for sql_validation in test_cases_data.get('sql_validations', []):
            cursor.execute("""
                INSERT INTO sql_validations (
                    batch_id, test_id, query_sql, description
                ) VALUES (%s, %s, %s, %s)
            """, (
                batch_id,
                sql_validation.get('test_id', ''),
                sql_validation.get('query', ''),
                sql_validation.get('description', '')
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"[SUCCESS] Saved test case batch {batch_id} with {len(test_cases_data.get('test_cases', []))} test cases")
        return batch_id
        
    except Exception as e:
        print(f"[WARNING] Could not save test case batch: {e}")
        return None

def get_test_case_batches_by_project(project_id):
    """
    Get all test case batches for a specific project.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT batch_id, batch_name, created_at, test_case_count, sql_validation_count
            FROM test_case_batches 
            WHERE project_id = %s 
            ORDER BY created_at DESC
        """, (project_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Exception as e:
        print(f"[WARNING] Could not retrieve test case batches: {e}")
        return []

def get_test_case_batch_by_id(batch_id):
    """
    Get a complete test case batch with all test cases and SQL validations.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get batch info
        cursor.execute("""
            SELECT tcb.*, p.project_name 
            FROM test_case_batches tcb
            JOIN projects p ON tcb.project_id = p.project_id
            WHERE tcb.batch_id = %s
        """, (batch_id,))
        batch_info = cursor.fetchone()
        
        if not batch_info:
            return None
        
        # Get test cases
        cursor.execute("""
            SELECT test_id, category, title, description, steps, expected_result, severity
            FROM test_cases 
            WHERE batch_id = %s
            ORDER BY test_id
        """, (batch_id,))
        test_cases = cursor.fetchall()
        
        # Parse steps JSON
        for tc in test_cases:
            try:
                tc['steps'] = json.loads(tc['steps']) if tc['steps'] else []
            except:
                tc['steps'] = [tc['steps']] if tc['steps'] else []
        
        # Get SQL validations
        cursor.execute("""
            SELECT test_id, query_sql, description
            FROM sql_validations 
            WHERE batch_id = %s
            ORDER BY test_id
        """, (batch_id,))
        sql_validations = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {
            'batch_info': batch_info,
            'test_cases': test_cases,
            'sql_validations': sql_validations
        }
        
    except Exception as e:
        print(f"[WARNING] Could not retrieve test case batch {batch_id}: {e}")
        return None

def delete_test_case_batch(batch_id):
    """
    Delete a test case batch and all associated test cases and SQL validations.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Delete in correct order due to foreign keys
        cursor.execute("DELETE FROM sql_validations WHERE batch_id = %s", (batch_id,))
        cursor.execute("DELETE FROM test_cases WHERE batch_id = %s", (batch_id,))
        cursor.execute("DELETE FROM test_case_batches WHERE batch_id = %s", (batch_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"[SUCCESS] Deleted test case batch {batch_id}")
        return True
        
    except Exception as e:
        print(f"[WARNING] Could not delete test case batch {batch_id}: {e}")
        return False

def get_database_status():
    """
    Get detailed database setup status for display in the UI.
    Returns a dictionary with status information.
    """
    status = {
        'database_exists': False,
        'tables_exist': [],
        'missing_tables': [],
        'all_tables_ready': False,
        'connection_ok': False,
        'error_message': None
    }
    
    try:
        # Test database connection
        conn = get_connection_safe()
        status['connection_ok'] = True
        status['database_exists'] = True
        
        cursor = conn.cursor()
        
        # Check existing tables
        cursor.execute("SHOW TABLES")
        existing_tables = [table[0] for table in cursor.fetchall()]
        
        required_tables = [
            'projects', 'files', 'validation_rules', 'ai_logs',
            'test_case_batches', 'test_cases', 'sql_validations'
        ]
        
        status['tables_exist'] = existing_tables
        status['missing_tables'] = [table for table in required_tables if table not in existing_tables]
        status['all_tables_ready'] = len(status['missing_tables']) == 0
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        status['error_message'] = str(e)
        status['connection_ok'] = False
    
    return status