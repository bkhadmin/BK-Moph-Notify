-- ใช้เฉพาะกรณีต้องการแก้ข้อมูลเดิมที่ถูกบันทึกเป็น UTC ทั้งที่ควรเป็น Asia/Bangkok
-- โปรดตรวจสอบข้อมูลก่อนรันจริง

UPDATE alert_cases
SET first_sent_at = DATE_SUB(first_sent_at, INTERVAL 7 HOUR)
WHERE first_sent_at IS NOT NULL;

UPDATE alert_cases
SET last_sent_at = DATE_SUB(last_sent_at, INTERVAL 7 HOUR)
WHERE last_sent_at IS NOT NULL;
