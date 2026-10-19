# การเผยแพร่และดูแล NS Capital

คู่มือหลัก: [USER-MANUAL-TH.md](USER-MANUAL-TH.md) หัวข้อ Deployment, Login, HTTPS Gateway, Upgrade และ Backup

Frontend ของเวอร์ชันนี้เป็น Static/PWA บน Sites โดย Authentication และ Audience อยู่ที่โฮสติ้ง ส่วน Python Bridge, SQLite และ MT4/MT5 ต้องรันบนเครื่อง/Windows VPS ของเจ้าของ บริการโมเดลแยกตาม Environment ของ Bridge

ก่อนส่งมอบ production ต้องตรวจด้วยบัญชี Demo: Login/Audience, Symbol จริง, Quote freshness, History reconciliation, Risk halt ก่อน Execute, Receipt หลัง Timeout, การปิดและลด SL ขณะ Halt, Backup/Restore, Model inference และ Gateway จากอุปกรณ์เป้าหมาย การทดสอบ Fixture ไม่แทนการ Compile EA หรือทดสอบ Terminal จริง

หากย้าย Frontend ออกจาก Sites ต้องจัด Authentication ฝั่งโฮสติ้งใหม่ ไม่ใช้ไฟล์หน้า Login เป็นการป้องกันข้อมูล และไม่ถือว่า CORS เป็นระบบสมาชิก เวอร์ชันนี้ยังไม่รวม SaaS tenant isolation/การเก็บ credential แยกสมาชิก/ฐาน Cloud ข้าม VPS

## Environment ฝั่ง Bridge

| ตัวแปร | หน้าที่ |
| --- | --- |
| NS_BRIDGE_MODE / NS_BRIDGE_PORT | mt4/mt5 และ port ค่าเริ่มต้น 8787 |
| NS_MT5_PATH | Terminal executable ที่จะเชื่อม |
| NS_BRIDGE_TOKEN | Token อ่านข้อมูล 32+ ตัว |
| NS_TRADE_TOKEN | Token ส่งคำสั่ง/แก้ Risk แยกต่างหาก ใช้กับ --enable-trading |
| NS_PUBLISH_TOKEN | MT4 EA publisher เท่านั้น |
| NS_ALLOWED_ORIGINS | Origins ที่เรียก Bridge ได้ คั่นด้วย comma |
| NS_ALLOWED_HOSTS | Hostnames ที่รับได้ รวม Gateway hostname |
| NS_DB_PATH | ไฟล์ SQLite กลางบนดิสก์เครื่องเดียวกัน |
| NS_HISTORY_DAYS | วันย้อนหลังเริ่มต้น 90 รับ 2–3650 |
| NS_HISTORY_SYNC_SECONDS | รอบซิงก์เริ่มต้น 30 วินาที รับ 5–300; Risk ต้องการข้อมูลไม่เกิน 90 วินาที |
| NS_AI_PROVIDER | ollama / lm-studio / openai-compatible |
| NS_AI_BASE_URL | /v1 base ของโมเดล ต้อง HTTPS หรือ localhost HTTP |
| NS_AI_MODEL | Exact model ID |
| NS_AI_API_KEY | Secret ฝั่ง Bridge ถ้าจำเป็น |

เอกสารนี้ไม่มี Token ที่ใช้ได้จริง เก็บค่าของ production ใน secret/environment ของกระบวนการรันและสำรองโดยจำกัดสิทธิ์
