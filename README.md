# BK-Moph Notify – Module 10

สิ่งที่เพิ่ม
- จัดการ MOPH Notify send error ให้แสดงบนหน้าเว็บ ไม่หลุด Internal Server Error
- เก็บ error รายละเอียดลง send logs / access logs
- หน้า System Connections เพิ่มสถานะ MOPH Notify config
- หน้า MOPH Notify Test ใหม่ ใช้งานสะดวกขึ้น
- provider callback error handling คงไว้และใช้ debug ได้ง่ายขึ้น
- additive upgrade จาก Module 9

จุดที่ช่วย debug ได้มากขึ้น
- ถ้า MOPH Notify ตอบ 4xx/5xx จะเห็น http_status และ response_text ที่ sanitize แล้ว
- ถ้า config ไม่ครบ จะดูได้จาก /system/connections
