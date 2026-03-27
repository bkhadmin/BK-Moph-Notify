-- 1) เติม lab_order_number จาก source_row_json ให้ข้อมูลเก่า
UPDATE alert_cases
SET lab_order_number = JSON_UNQUOTE(JSON_EXTRACT(source_row_json, '$.lab_order_number'))
WHERE (lab_order_number IS NULL OR lab_order_number = '')
  AND source_row_json IS NOT NULL
  AND JSON_VALID(source_row_json)
  AND JSON_EXTRACT(source_row_json, '$.lab_order_number') IS NOT NULL;

-- 2) backfill เวลาส่งจาก send_logs สำหรับกรณีที่มี created_at
SET @has_created_at := (
  SELECT COUNT(*)
  FROM information_schema.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'send_logs'
    AND COLUMN_NAME = 'created_at'
);

SET @sql := IF(@has_created_at > 0,
'UPDATE alert_cases ac
JOIN (
    SELECT
        JSON_UNQUOTE(JSON_EXTRACT(ac2.source_row_json, ''$.lab_order_number'')) AS lab_order_number,
        MIN(sl.created_at) AS first_sent_at,
        MAX(sl.created_at) AS last_sent_at,
        COUNT(*) AS sent_count
    FROM alert_cases ac2
    JOIN send_logs sl
      ON sl.status = ''success''
     AND (
          sl.detail LIKE ''approved_query_id=%''
          OR sl.detail LIKE ''schedule_job_id=%''
         )
    WHERE ac2.source_row_json IS NOT NULL
      AND JSON_VALID(ac2.source_row_json)
      AND JSON_EXTRACT(ac2.source_row_json, ''$.lab_order_number'') IS NOT NULL
    GROUP BY JSON_UNQUOTE(JSON_EXTRACT(ac2.source_row_json, ''$.lab_order_number''))
) x
  ON ac.lab_order_number = x.lab_order_number
SET
  ac.first_sent_at = COALESCE(ac.first_sent_at, x.first_sent_at),
  ac.last_sent_at = COALESCE(ac.last_sent_at, x.last_sent_at),
  ac.sent_count = CASE WHEN COALESCE(ac.sent_count,0)=0 THEN x.sent_count ELSE ac.sent_count END,
  ac.updated_at = NOW()',
'SELECT ''skip send_logs backfill because send_logs.created_at not found'' AS info');

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;
