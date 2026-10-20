USE cpms2;

CREATE TABLE result (
  result_id INT AUTO_INCREMENT PRIMARY KEY,
  application_id INT UNIQUE NOT NULL,
  outcome ENUM('selected','not_selected') NOT NULL,
  offered_package DECIMAL(5,2),
  FOREIGN KEY (application_id) REFERENCES application(application_id)
);