-- Run this once against the existing trip_planner database.
-- Existing users, trips, expenses and expense_splits are preserved.
USE trip_planner;

CREATE TABLE IF NOT EXISTS settlements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trip_id INT NOT NULL,
    paid_by INT NOT NULL,
    paid_to INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    note VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_settlement_amount CHECK (amount > 0),
    CONSTRAINT chk_settlement_different_users CHECK (paid_by <> paid_to),
    FOREIGN KEY (trip_id) REFERENCES trips(id) ON DELETE CASCADE,
    FOREIGN KEY (paid_by) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (paid_to) REFERENCES users(id) ON DELETE RESTRICT
);
