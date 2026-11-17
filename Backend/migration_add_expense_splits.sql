-- Run this against the existing trip_planner database.
-- It adds only the table required to store each member's share.
USE trip_planner;

CREATE TABLE IF NOT EXISTS expense_splits (
    id INT AUTO_INCREMENT PRIMARY KEY,
    expense_id INT NOT NULL,
    user_id INT NOT NULL,
    owed_amount DECIMAL(10,2) NOT NULL,
    is_settled TINYINT(1) NOT NULL DEFAULT 0,
    UNIQUE KEY uq_expense_user (expense_id, user_id),
    FOREIGN KEY (expense_id) REFERENCES expenses(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT
);
