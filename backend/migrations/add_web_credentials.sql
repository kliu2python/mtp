-- Add web console credential fields to virtual_machines table
-- Run this migration if you have an existing database

ALTER TABLE virtual_machines
ADD COLUMN IF NOT EXISTS web_username VARCHAR,
ADD COLUMN IF NOT EXISTS web_password VARCHAR;

-- Verify the new columns were added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'virtual_machines'
AND column_name IN ('web_username', 'web_password');
