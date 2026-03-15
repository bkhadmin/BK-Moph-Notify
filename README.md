# BK-Moph Notify – Module 9

สิ่งที่เพิ่ม
- ปรับ CSS ใหม่ ไม่ให้ sidebar/content ทับกัน
- ฟอร์มหน้า Approved Queries จัด layout ใหม่
- ปุ่มทดสอบการเชื่อมต่อ HOSxP
- หน้า System Connections สำหรับตรวจสอบ HOSxP และ Provider config
- Provider callback error จะแสดงกลับหน้า login แบบอ่านง่าย ไม่ปล่อย Internal Server Error
- SQL guard อนุญาต trailing semicolon ได้ แต่ยังบล็อก multi-statement

แนวทาง
- ต่อจาก Module 8 แบบ additive
- เน้น usability + diagnostics + ลด error ตอนใช้งานจริง
