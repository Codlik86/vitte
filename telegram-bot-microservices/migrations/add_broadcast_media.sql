-- Add broadcast_media table for storing media files in database
-- Run this migration: psql -U <user> -d <database> -f add_broadcast_media.sql

CREATE TABLE IF NOT EXISTS broadcast_media (
    id VARCHAR(64) PRIMARY KEY,
    file_data BYTEA NOT NULL,
    content_type VARCHAR(128) NOT NULL,
    file_size INTEGER NOT NULL,
    media_type VARCHAR(16) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_broadcast_media_id ON broadcast_media(id);
CREATE INDEX IF NOT EXISTS idx_broadcast_media_created_at ON broadcast_media(created_at);
