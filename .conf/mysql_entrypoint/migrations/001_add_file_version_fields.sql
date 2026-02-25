-- Migration: Add version management fields to file table
-- Date: 2025-02-24
-- Description: Add version, parent_uuid, is_latest columns to support component versioning

USE ginkgo;

-- Add version column
ALTER TABLE `file`
  ADD COLUMN `version` VARCHAR(32) DEFAULT '1.0.0' COMMENT '版本号' AFTER `data`;

-- Add parent_uuid column
ALTER TABLE `file`
  ADD COLUMN `parent_uuid` VARCHAR(32) DEFAULT NULL COMMENT '父版本UUID' AFTER `version`;

-- Add is_latest column
ALTER TABLE `file`
  ADD COLUMN `is_latest` BOOLEAN DEFAULT TRUE COMMENT '是否最新版本' AFTER `parent_uuid`;

-- Create indexes for efficient version queries
CREATE INDEX idx_file_version ON `file`(`name`, `version`, `is_latest`);
CREATE INDEX idx_file_parent ON `file`(`parent_uuid`);

-- Update existing records to have default version values
UPDATE `file` SET `version` = '1.0.0', `is_latest` = TRUE WHERE `version` IS NULL;
