DROP DATABASE IF EXISTS cpms2;
CREATE DATABASE cpms2;
USE cpms2;

CREATE TABLE student (
  student_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  department VARCHAR(50) NOT NULL,
  cgpa DECIMAL(3,2) NOT NULL
);

CREATE TABLE company (
  company_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(100) UNIQUE,
  password_hash VARCHAR(255)
);

CREATE TABLE drive (
  drive_id INT AUTO_INCREMENT PRIMARY KEY,
  company_id INT NOT NULL,
  job_role VARCHAR(100) NOT NULL,
  package_lpa DECIMAL(5,2),
  min_cgpa DECIMAL(3,2) DEFAULT 0,
  drive_date DATE,
  deadline DATE,
  FOREIGN KEY (company_id) REFERENCES company(company_id)
);

CREATE TABLE application (
  application_id INT AUTO_INCREMENT PRIMARY KEY,
  student_id INT NOT NULL,
  drive_id INT NOT NULL,
  applied_on DATETIME DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (student_id, drive_id),
  FOREIGN KEY (student_id) REFERENCES student(student_id),
  FOREIGN KEY (drive_id) REFERENCES drive(drive_id)
);

INSERT INTO company (name) VALUES ('TCS'), ('Infosys'), ('Bosch');

INSERT INTO drive (company_id, job_role, package_lpa, min_cgpa, drive_date, deadline) VALUES
(1, 'System Engineer',    3.60, 6.0, '2026-11-10', '2026-11-05'),
(2, 'Software Developer', 6.50, 7.5, '2026-11-15', '2026-11-10'),
(3, 'Graduate Trainee',   4.50, 6.5, '2026-11-20', '2026-10-01'),
(1, 'Digital Specialist', 7.00, 9.0, '2026-12-01', '2026-11-25');