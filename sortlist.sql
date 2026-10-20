USE cpms2;

ALTER TABLE application
  ADD COLUMN status ENUM('applied','shortlisted','rejected') DEFAULT 'applied';