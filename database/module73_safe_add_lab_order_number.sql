SET @exists := (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'alert_cases'
    AND COLUMN_NAME = 'lab_order_number'
);

SET @sql := IF(@exists = 0,
'ALTER TABLE alert_cases ADD COLUMN lab_order_number VARCHAR(100) NULL AFTER item_value',
'SELECT ''lab_order_number already exists'' AS info');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @idx_exists := (
  SELECT COUNT(*)
  FROM information_schema.STATISTICS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'alert_cases'
    AND INDEX_NAME = 'idx_alert_cases_lab_order_number'
);
SET @sql2 := IF(@idx_exists = 0,
'CREATE INDEX idx_alert_cases_lab_order_number ON alert_cases (lab_order_number)',
'SELECT ''idx_alert_cases_lab_order_number already exists'' AS info');
PREPARE stmt2 FROM @sql2;
EXECUTE stmt2;
DEALLOCATE PREPARE stmt2;
