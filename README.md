# BK-Moph Notify – Module 11

สิ่งที่เพิ่ม
- แก้ SQL guard ให้รองรับ comment style `--`, `#`, `/* */` ได้ โดยยังบล็อกคำสั่งอันตราย
- ปรับ MOPH Notify URL join ให้ไม่เกิด `//api/notify/send`
- เพิ่ม Provider token exchange fallback หลายรูปแบบเพื่อลดปัญหา 401
- เพิ่ม diagnostics ของ provider token attempts แบบ sanitize
- เพิ่ม Flex Message Builder แบบฟอร์มใช้งานง่าย
- additive upgrade จาก Module 10
