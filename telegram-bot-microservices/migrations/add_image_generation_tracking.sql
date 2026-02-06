-- Add image generation tracking to dialogs table
-- Migration: add_image_generation_tracking
-- Date: 2026-02-06

-- Add last_image_generation_at column to track when last image was generated
ALTER TABLE dialogs
ADD COLUMN IF NOT EXISTS last_image_generation_at INTEGER DEFAULT NULL;

-- Add comment
COMMENT ON COLUMN dialogs.last_image_generation_at IS 'Message count when last image was generated (for trigger frequency tracking)';
