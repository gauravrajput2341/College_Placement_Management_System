USE cpms2;

ALTER TABLE drive
  ADD COLUMN status ENUM('pending','approved') DEFAULT 'pending';

UPDATE drive SET status = 'approved';

CREATE TABLE admin (
  admin_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL
);