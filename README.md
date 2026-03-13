# BK-Moph Notify Final

โปรเจกต์นี้เป็นชุดรวมใหม่ทั้งระบบในโครงสร้างเดียวกัน เพื่อให้เริ่มทดสอบใหม่จากศูนย์ได้ง่ายขึ้น

## สิ่งที่มี
- FastAPI backend
- Local login + session + CSRF
- Dashboard / Users / Queries / Templates / Send / Audit pages
- Query safety guard
- Audit log พื้นฐาน
- MySQL + Redis + Nginx + Docker Compose
- DB bootstrap สำหรับ role + superadmin

## วิธีเริ่ม
```bash
cp .env.example .env
docker compose -f docker-compose.prod.yml up -d --build
```

เปิด:
- http://SERVER_IP:8012/login

## หมายเหตุ
ชุดนี้เป็นเวอร์ชัน consolidated final candidate สำหรับรีเซ็ตและทดสอบใหม่แบบสะอาด
โดยโครงสร้างไฟล์ทั้งหมดถูกทำให้สอดคล้องกันในชุดเดียว
