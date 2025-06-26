-- ===============================
--  QA Genius Database Schema
-- ===============================

-- 1. Projects Table
CREATE TABLE projects (
    project_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Test Artifacts Table (Combined Test Case + Script)
CREATE TABLE test_cases (
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
);

