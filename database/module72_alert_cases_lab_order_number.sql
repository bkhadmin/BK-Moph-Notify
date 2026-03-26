ALTER TABLE alert_cases
ADD COLUMN lab_order_number VARCHAR(100) NULL AFTER item_value;

CREATE INDEX idx_alert_cases_lab_order_number ON alert_cases (lab_order_number);
