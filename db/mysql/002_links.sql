CREATE TABLE IF NOT EXISTS links (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    owner_id BIGINT NOT NULL,
    code VARCHAR(16) NOT NULL UNIQUE,
    original_url TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_deleted BOOLEAN DEFAULT FALSE,
    expires_at DATETIME NULL,
    deleted_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_links_owner
        FOREIGN KEY (owner_id) REFERENCES users(id)
        ON DELETE CASCADE,
    INDEX idx_links_code (code),
    INDEX idx_links_owner (owner_id),
    INDEX idx_links_active (is_active, expires_at),
    INDEX idx_links_deleted (is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
