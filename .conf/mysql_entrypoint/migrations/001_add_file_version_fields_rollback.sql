-- Rollback: Remove version management fields from file table
-- Date: 2025-02-24
-- Description: Rollback script for 001_add_file_version_fields.sql

USE ginkgo;

-- Drop indexes
DROP INDEX idx_file_version ON `file`;
DROP INDEX idx_file_parent ON `file`;

-- Remove columns
ALTER TABLE `file` DROP COLUMN `is_latest`;
ALTER TABLE `file` DROP COLUMN `parent_uuid`;
ALTER TABLE `file` DROP COLUMN `version`;
