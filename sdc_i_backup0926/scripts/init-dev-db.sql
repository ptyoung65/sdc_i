-- SDC Development Database Initialization

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create development schema
CREATE SCHEMA IF NOT EXISTS sdc_dev;

-- Create development user with limited permissions
DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sdc_dev_user') THEN
      CREATE ROLE sdc_dev_user WITH LOGIN PASSWORD 'sdc_dev_pass_2025';
   END IF;
END
$$;

-- Grant permissions
GRANT USAGE ON SCHEMA sdc_dev TO sdc_dev_user;
GRANT CREATE ON SCHEMA sdc_dev TO sdc_dev_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA sdc_dev TO sdc_dev_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA sdc_dev TO sdc_dev_user;

-- Create basic development tables
CREATE TABLE IF NOT EXISTS sdc_dev.dev_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level VARCHAR(10) NOT NULL,
    message TEXT NOT NULL,
    service VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert sample development data
INSERT INTO sdc_dev.dev_logs (level, message, service) VALUES
('INFO', 'Development environment initialized', 'system'),
('INFO', 'VSCode server ready', 'vscode'),
('INFO', 'Backend development server ready', 'backend'),
('INFO', 'Frontend development server ready', 'frontend');

COMMENT ON SCHEMA sdc_dev IS 'SDC Development Environment Schema';