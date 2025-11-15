-- MySQL schema for file upload system
-- Run inside XAMPP phpMyAdmin or mysql client
-- CREATE DATABASE fileupload CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE fileupload;

DROP TABLE IF EXISTS users;
CREATE TABLE users (
  user_id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  quota_mb INT DEFAULT 1000,
  is_active TINYINT(1) DEFAULT 1,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Insert Guest user with user_id=0 for anonymous uploads
-- Insert Guest user with user_id=1 for anonymous uploads
INSERT INTO users (user_id, username, password_hash, quota_mb, is_active) 
VALUES (1, 'Guest', 'N/A', 9999999, 1);

DROP TABLE IF EXISTS files;
CREATE TABLE files (
  file_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  original_filename VARCHAR(255) NOT NULL,
  stored_filename VARCHAR(255) NOT NULL,
  file_size_bytes BIGINT NOT NULL,
  file_type VARCHAR(50) NULL,
  upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  expiration_date TIMESTAMP NULL,
  download_count INT DEFAULT 0,
  is_public TINYINT(1) DEFAULT 0,
  status ENUM('pending','in_progress','success','error','cancelled') DEFAULT 'pending',
  CONSTRAINT fk_files_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

DROP TABLE IF EXISTS upload_sessions;
CREATE TABLE upload_sessions (
  session_id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  file_id INT NOT NULL,
  ip_address VARCHAR(45) NULL,
  start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  end_time TIMESTAMP NULL,
  bytes_transferred BIGINT DEFAULT 0,
  status ENUM('in_progress','success','error','cancelled') DEFAULT 'in_progress',
  error_message TEXT NULL,
  CONSTRAINT fk_sessions_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_sessions_file FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE
) ENGINE=InnoDB;

DROP TABLE IF EXISTS statistics_daily;
CREATE TABLE statistics_daily (
  stat_date DATE PRIMARY KEY,
  total_uploads INT DEFAULT 0,
  total_bytes BIGINT DEFAULT 0,
  active_users INT DEFAULT 0,
  avg_upload_speed_mb FLOAT DEFAULT 0
) ENGINE=InnoDB;

-- Indexes for performance
CREATE INDEX idx_files_user ON files(user_id);
CREATE INDEX idx_files_status ON files(status);
CREATE INDEX idx_sessions_user ON upload_sessions(user_id);
CREATE INDEX idx_sessions_file ON upload_sessions(file_id);
