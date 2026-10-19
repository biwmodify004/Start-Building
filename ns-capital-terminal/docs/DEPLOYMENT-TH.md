# การเผยแพร่และดูแล NS Capital

คู่มือหลัก: [USER-MANUAL-TH.md](USER-MANUAL-TH.md) หัวข้อ Deployment, Login, HTTPS Gateway, Upgrade และ Backup

Frontend เป็น Static/PWA บน **GitHub Pages** แสดงที่ `/Start-Building/` ผ่าน GitHub Actions ส่วน Python Bridge, SQLite และ MT4/MT5 ยังรันบน Windows/VPS ของเจ้าของ Google Login ตรวจที่ Bridge ไม่ใช่ระบบสมาชิกของ Pages

ตั้งค่าครั้งแรก: Repository → Settings → Pages → Source: GitHub Actions จากนั้น Merge/PUSH main ที่เปลี่ยนแอป หรือเลือก Actions → Deploy NS Capital to GitHub Pages → Run workflow ดูสถานะสำเร็จและ URL ใน Environment github-pages ก่อนใช้เว็บใหม่

Workflow ใช้ Node 22/Python 3.12 ทดสอบ JavaScript/Python แล้วรัน `npm run build:pages` อัปโหลดเฉพาะ dist ไม่อัปโหลดฐานจริง/Token/Python runtime มี OIDC/Pages write เฉพาะ deploy job โค้ดโครงการอยู่ใต้ ns-capital-terminal/ ส่วน Workflow ที่ทำงานจริงอยู่ root .github/workflows/

Google Login ต้องมี Web OAuth Client ID ของเจ้าของ, JavaScript Origin ตรงเว็บ, Allowlist ที่ Bridge และติดตั้ง `py -m pip install -r requirements-google.txt` ดูขั้นตอนเต็มในคู่มือ Google Login ไม่มี Client Secret ในเว็บหรือ GitHub

ก่อนใช้จริงตรวจบัญชี Demo, Quote freshness, History reconciliation, Risk ก่อน Execute, Receipt หลัง Timeout, Backup/Restore และการเชื่อมจากอุปกรณ์เป้าหมาย ยังไม่มี multi-tenant SaaS หรือ Cloud ledger ข้าม VPS

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
| NS_GOOGLE_CLIENT_ID | Google Web OAuth Client ID ใช้ตรวจ audience |
| NS_GOOGLE_ALLOWED_EMAILS | Gmail/Workspace owner allowlist คั่น comma |
| NS_GOOGLE_ALLOWED_SUBS | Stable Google subject IDs ที่อนุญาต ใช้กับอีเมลภายนอก |
| NS_AI_PROVIDER | ollama / lm-studio / openai-compatible |
| NS_AI_BASE_URL | /v1 base ของโมเดล ต้อง HTTPS หรือ localhost HTTP |
| NS_AI_MODEL | Exact model ID |
| NS_AI_API_KEY | Secret ฝั่ง Bridge ถ้าจำเป็น |

เอกสารนี้ไม่มี Token ที่ใช้ได้จริง เก็บค่าของ production ใน secret/environment ของกระบวนการรันและสำรองโดยจำกัดสิทธิ์
