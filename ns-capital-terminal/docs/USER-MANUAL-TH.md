# คู่มือ NS Capital Terminal ภาษาไทย

เวอร์ชัน 1.8.0 · ปรับปรุง 19 ตุลาคม 2569 (2026-10-19)

คู่มือนี้ตรงกับโค้ดเวอร์ชัน 1.8 ไม่ต้องมีบัญชีโบรกเกอร์เพื่อเปิดกราฟ Binance แต่ต้องติดตั้ง Broker Bridge และเชื่อม Terminal ของคุณก่อนใช้ราคาโบรกเกอร์ Auto Journal หรือส่งคำสั่งซื้อขาย

เว็บ: [เปิด NS Capital Terminal](https://ns-capital-terminal.biw-modify004.chatgpt.site) · [หน้าเข้าสู่ระบบ](../login.html) · [ดาวน์โหลด Broker Bridge](../downloads/NS-Capital-Broker-Bridge.zip)

## เริ่มใช้งานเร็ว

1. เปิดเว็บใน Chrome, Edge หรือ Safari และเข้าสู่ระบบด้วย ChatGPT ที่มีสิทธิ์เข้าถึง Site
2. เลือก **Binance · Crypto** เพื่อดูข้อมูลจริงได้ทันที ใช้ปุ่มค้นหาสินทรัพย์เพื่อเปิดรายการทั้งหมด
3. ถ้าจะใช้ MT5 ให้ดาวน์โหลดและแตก Broker Bridge ไปที่ `C:\NS-Capital-Bridge` บน Windows เครื่องเดียวกับ Terminal
4. เปิด MT5 และเข้าสู่บัญชี Demo ของคุณก่อน ติดตั้ง Python และแพ็กเกจ MetaTrader5 ตามหัวข้อ MT5
5. เปิด PowerShell ในโฟลเดอร์ Bridge แล้วรัน `py bridge.py --mode mt5` เพื่อเริ่มในโหมดดูข้อมูล
6. ที่เว็บกด **บัญชีเทรด → เพิ่มบัญชี** ใส่ URL และ Bridge token จากหน้าต่าง Bridge แล้วเชื่อมต่อ ตรวจชื่อโบรกเกอร์ เซิร์ฟเวอร์ เลขบัญชีที่ปิดบัง และสกุลเงิน
7. เปิด **Journal** แล้วกด **ซิงก์ประวัติจริง** ตรวจต้นทุนและรายการรอจำแนกกับ Statement
8. เมื่อต้องการเปิดสิทธิ์เทรด ให้ทำตามหัวข้อการซื้อขายและตั้ง Risk Engine รายบัญชีก่อน ไม่มีการเลือกเพดานความเสี่ยงให้คุณอัตโนมัติ
9. ต้องการใช้จากมือถือหรือแท็บเล็ต ให้ตั้ง HTTPS Gateway ที่เข้าถึง Bridge บน Windows ตามหัวข้อเครือข่าย
10. อ่านหัวข้อ Backup, Unknown receipt และข้อจำกัดก่อนเปลี่ยนจาก Demo เป็นบัญชีเงินจริง

## ส่วนที่มีในเวอร์ชันนี้

| ความสามารถ | สถานะและขอบเขต |
| --- | --- |
| Login เว็บไซต์ | ใช้ ChatGPT sign-in และสิทธิ์เข้าถึงของ Sites เว็บปัจจุบันเป็นพื้นที่ส่วนตัวของเจ้าของ |
| Binance | รายการ Spot ที่ API รายงานว่าเปิดซื้อขายได้ ราคาและแท่งจริง ไม่ใช้ราคา Sample |
| ทอง เงิน Forex และ Index | วิดเจ็ตอ้างอิง TradingView หรือข้อมูล Symbol จริงจาก MT4/MT5 ที่เชื่อมไว้ |
| หลายบัญชี | เก็บหลายโปรไฟล์ สลับทำงานทีละบัญชี แต่ละบัญชีมี Bridge/Terminal และกฎแยกกัน |
| MT5 | ดึงราคา แท่ง สถานะ และประวัติ Deal ผ่าน Python API ของ Terminal บน Windows |
| MT4 | EA ส่งราคา สถานะ และ Account History ไป Bridge ต้อง Compile และตั้งค่าด้วยตนเอง |
| Auto Journal | SQLite กลางบนเครื่อง/VPS ของคุณ แยก platform + server + login รวม Commission, Swap และ Fee |
| Dashboard | Booked P&L, Win Rate, Profit Factor, Booked drawdown, สถิติ Symbol/Setup และกราฟสะสม |
| Risk Engine | ตรวจฝั่ง Backend ทั้ง Preview และ Execute พร้อม Daily halt และ Drawdown halt |
| AI | Ollama, LM Studio หรือ API แบบ OpenAI-compatible ทำ Draft และ Journal Coaching |
| Track Record | Snapshot อ่านอย่างเดียว สร้างเมื่อยินยอม กำหนดหมดอายุและยกเลิกลิงก์ได้ ไม่ใช่การรับรองโดยโบรกเกอร์ |
| Leaderboard | ภายในฐานข้อมูล Bridge นี้เท่านั้น เฉพาะบัญชียินยอมและผ่านเกณฑ์ ไม่มีอันดับจำลอง |
| Backtest/Paper | วิจัยในเบราว์เซอร์ แยกจากบัญชีจริง จำนวนเป็นหน่วยสินทรัพย์ ไม่ใช่ CFD Lot |
| ติดตั้งเป็นแอป | PWA บนเบราว์เซอร์ที่รองรับ ใช้เปลือกแอปออฟไลน์ได้ ไม่ส่งคำสั่งออฟไลน์ |

ไม่มีระบบเทรนโมเดลอัตโนมัติ ไม่มีการเปิดเทรดต่อเนื่องโดย AI ไม่มี Copy trade ทุกบัญชี ไม่มีการเชื่อมบัญชี Binance เพื่อส่ง Spot/Futures orders และยังไม่มีระบบสมาชิกแบบอีเมล/รหัสผ่านที่แยกจาก ChatGPT

## Login และสิทธิ์เข้าถึง

เปิด `login.html` แล้วกด **เข้าสู่ระบบด้วย ChatGPT** ระบบจะนำทางระดับหน้าเว็บไปยังบริการยืนยันตัวตนของโฮสติ้ง หลังยืนยันแล้วกลับเข้า Terminal ได้ หากเข้าสู่ระบบอยู่แล้วใช้ **เปิด Terminal** ได้เลย

เมนูวงกลม **N / บัญชีผู้ใช้** ที่ส่วนหัวมีปุ่มเข้าสู่ระบบ ออกจากระบบ และลิงก์คู่มือ บนมือถือเข้าผ่านเมนู **เพิ่มเติม → บัญชีผู้ใช้ / Login** ได้

บัญชีเว็บไซต์ใช้ยืนยันผู้เข้าเว็บ ส่วนบัญชีโบรกเกอร์ใช้ส่งคำสั่งและอ่านข้อมูลผ่าน Bridge คนละระบบกัน อย่าใส่รหัสผ่านโบรกเกอร์ในหน้า Login ของเว็บไซต์

เวอร์ชันที่เผยแพร่นี้ยังเป็น Owner-private การเพิ่มผู้ใช้คนอื่นต้องกำหนดสิทธิ์ Site ก่อน ลิงก์ Track Record ไม่ข้ามสิทธิ์นี้ การเข้าสู่ระบบสำเร็จไม่ได้แปลว่าได้รับอนุญาตให้เปิดใช้ Terminal ของคนอื่น

ระบบไม่ได้สร้างฐานรหัสผ่านหรือหน้าสมัครสมาชิกซ้ำกับโฮสติ้ง เมื่อนำไฟล์ `dist/` ไปโฮสต์เอง ต้องเพิ่มบริการ Authentication และการกำหนดสิทธิ์ฝั่งเซิร์ฟเวอร์ของผู้ให้บริการนั้นก่อนใช้เป็นเว็บไซต์สมาชิก เส้นทาง Login ของ ChatGPT ในแพ็กเกจนี้ทำงานกับ Sites

ข้อมูลโปรไฟล์และงานวิจัยบางส่วนอยู่ในเบราว์เซอร์ของเครื่องนั้น ส่วนประวัติจริงและกฎ Risk อยู่ที่ Bridge การเปลี่ยนอุปกรณ์ไม่ดึงโปรไฟล์ในเบราว์เซอร์ให้อัตโนมัติ และไม่ใช่ระบบ Cloud sync ของสมาชิกหลายคน

## รู้จักหน้าจอ

**กราฟ:** ดูราคา เปลี่ยน Symbol/Timeframe เพิ่ม Indicator วาดกราฟและ Replay แถบสถานะบอกแหล่งข้อมูลและความสดของราคา

**ตลาดโลก:** เปิดกราฟอ้างอิง TradingView ของทอง เงิน คู่เงินหลัก และ Index ข้อมูลวิดเจ็ตนี้ไม่ส่งออกเป็น Quote ให้คำสั่งโบรกเกอร์หรือกราฟ Vela

**Strategy Lab:** ปรับกฎ EMA, Mean Reversion หรือ Breakout และทดสอบกับข้อมูลที่โหลดบนกราฟ ส่วน Local rules เป็นตัวอ่านคีย์เวิร์ด ไม่ใช่โมเดลที่เทรนแล้ว

**Journal:** Dashboard จากประวัติจริง กราฟ P&L, Coaching, การสังเกตพฤติกรรม, ตาราง Deal และโน้ตรายบัญชี เลือกช่วงเวลา 7/30/90/365 วันได้

**บัญชีเทรด:** เพิ่มและสลับโปรไฟล์ เชื่อม Bridge ใส่ Trade token ดูข้อมูล Symbol และสถานะการเชื่อมต่อ

**แผงซื้อขาย:** Buy/Sell, Lot, SL/TP, ตรวจคำสั่งและ Receipt รวมถึงตั้งกฎ Backend Risk

โหมดสว่าง/มืดและภาษาเปลี่ยนได้จากส่วนหัว บนหน้าจอเล็กเมนูบางอย่างอยู่ใต้ **เพิ่มเติม** ปัดตารางในแนวนอนเพื่อดูคอลัมน์ทั้งหมด

## Binance และสินทรัพย์ตลาดโลก

เลือก **Binance · Crypto** แล้วเปิดตัวค้นหาสินทรัพย์ รายการมาจาก Exchange Information ของ Binance Spot รวมคู่ที่มี Quote asset ต่างกันและชื่อ Unicode ตามที่ API ให้มา ไม่ได้จำกัดเฉพาะ USDT

คู่ที่หยุดซื้อขายหรือ API ไม่รายงานว่าเทรดได้จะไม่ถูกสร้างเป็นสินทรัพย์จำลอง หากอ่าน API หรือ WebSocket ไม่ได้ ระบบแสดงสถานะผิดพลาด/รอเชื่อม ไม่แทนด้วยราคาสุ่ม

ข้อมูล Binance ในเว็บนี้ใช้ทำกราฟและงานวิจัย การส่งคำสั่งโบรกเกอร์ใช้ Symbol และ Quote จาก Bridge ของบัญชีนั้นเสมอ ไม่ใช้ราคา Binance หรือวิดเจ็ตตลาดโลกแทน

เลือก **TradingView · ตลาดโลก** เพื่อดูกราฟอ้างอิง หรือเลือก **Broker · CFD / Futures** หลังเชื่อม MT4/MT5 เพื่อใช้สัญญาที่โบรกเกอร์ของคุณเปิดให้จริง ทองอาจชื่อ `XAUUSD`, `GOLD` หรือมี suffix เช่น `.pro` ให้เลือกชื่อตามรายการจากโบรกเกอร์

## เตรียมเครื่องสำหรับ Broker Bridge

- Windows ที่ติดตั้ง MT4 หรือ MT5 และ Terminal เชื่อมต่อบัญชีได้ตามปกติ
- Python 3.11 ขึ้นไป ตรวจด้วย `py --version` และตรวจรุ่น Python ที่แพ็กเกจ MetaTrader5 รองรับก่อนติดตั้ง
- ไฟล์ Broker Bridge รุ่นเดียวกับเว็บ แตกทั้งโฟลเดอร์ อย่าคัดลอกเฉพาะ `bridge.py`
- อินเทอร์เน็ตและเวลาเครื่องถูกต้อง
- ใช้ Windows VPS เมื่อต้องการให้ Bridge/Terminal ทำงานต่อเนื่อง แม้ปิดหน้าเว็บ

ไฟล์สำคัญในชุดดาวน์โหลด:

| ไฟล์ | หน้าที่ |
| --- | --- |
| `bridge.py` | HTTP Gateway, การยืนยัน Token และ worker ซิงก์ประวัติ |
| `trading.py` | Preview/Execute, สถานะและ Receipt |
| `database.py` | ฐาน SQLite และคำสั่ง Backup |
| `journal.py` | นำเข้าประวัติจริงและแยกบัญชี |
| `analytics.py` | สถิติ วินัย Track Record และ Leaderboard |
| `risk.py` | ตรวจเพดานความเสี่ยงฝั่ง Backend |
| `ai_advisor.py` | เชื่อมโมเดลเพื่อทำ Draft และ Coaching |
| `mcp_server.py` | MCP แบบ stdio และเครื่องมืออ่านข้อมูล/ขอ Draft |
| `NS_Market_Bridge.mq4` | EA สำหรับ MT4 |
| `README-TH.md`, `JOURNAL-RISK-TH.md` | คู่มือเฉพาะส่วน Bridge และ Risk |

Bridge ฟังที่ `127.0.0.1` โดยค่าเริ่มต้น ไม่เปิดพอร์ตสู่ทั้งเครือข่ายเอง บัญชีจริงและรหัสผ่านล็อกอินอยู่ใน Terminal ของคุณ

## เชื่อม MT5 ทีละขั้น

1. เปิด Terminal MT5 ของโบรกเกอร์และเข้าสู่บัญชีที่ต้องการ ตรวจ Server และเลขบัญชี
2. เปิด PowerShell ในโฟลเดอร์ Bridge ตัวอย่าง `Set-Location C:\NS-Capital-Bridge`
3. ติดตั้งแพ็กเกจ Python ของ MetaQuotes แล้วเริ่ม Bridge:

```powershell
py -m pip install MetaTrader5
py bridge.py --mode mt5
```

4. ถ้ามีหลาย Terminal ให้ระบุไฟล์ `terminal64.exe` ของตัวที่ถูกต้องก่อนเริ่ม:

```powershell
$env:NS_MT5_PATH = "C:\Program Files\YOUR-BROKER-MT5\terminal64.exe"
py bridge.py --mode mt5 --port 8787
```

5. Bridge จะแสดง **Bridge token** ชั่วคราว หากไม่ได้ตั้งค่าไว้ก่อน คัดลอกไปใช้กับหน้าเว็บ ห้ามเผยแพร่ Token ในภาพหน้าจอหรือ GitHub
6. ในเว็บกด **บัญชีเทรด → เพิ่มบัญชี** ตั้งชื่อโปรไฟล์ เลือกประเภท CFD/Futures ให้ตรงกับบัญชี ใส่ URL และ Bridge token
7. เครื่องเดียวกันลอง URL `http://127.0.0.1:8787` ได้เมื่อเบราว์เซอร์อนุญาต ถ้าถูกบล็อก Local network ให้ใช้ HTTPS Gateway ตามหัวข้อเครือข่าย
8. กดเชื่อมต่อ ตรวจชื่อบริษัท Server เลขบัญชี สกุลเงิน และรายการ Symbol ก่อนเลือกใช้งาน
9. เปิด Journal รอซิงก์ครบหรือกด **ซิงก์ประวัติจริง** ค่าเริ่มต้นนำเข้า 90 วัน เบื้องหลังซิงก์ทุก 30 วินาที พร้อมอ่านซ้ำช่วงซ้อนและทบทวนช่วงนำเข้าอย่างน้อยวันละครั้งขณะทำงาน

การอ่านข้อมูลไม่ต้องเปิด `--enable-trading` การส่งคำสั่งต้องเปิดเพิ่มตามหัวข้อซื้อขาย บัญชี Investor/read-only อาจดูข้อมูลได้แต่ส่งคำสั่งไม่ได้

## เชื่อม MT4 ทีละขั้น

1. แตกชุด Bridge แล้วเปิด PowerShell ในโฟลเดอร์นั้น เริ่มด้วย `py bridge.py --mode mt4 --port 8787`
2. จด **Bridge token** และ **EA Publish token** ที่แสดง ทั้งสองเป็นคนละค่า
3. ใน MT4 เลือก **File → Open Data Folder** วาง `NS_Market_Bridge.mq4` ใน `MQL4\Experts`
4. เปิด MetaEditor, Compile EA และแก้ Compile error ให้หมดก่อนนำไปติดกราฟ
5. ใน MT4 เปิด **Tools → Options → Expert Advisors → Allow WebRequest for listed URL** เพิ่ม `http://127.0.0.1:8787`
6. เปิดแท็บ **Account History → คลิกขวา → All History** ให้โหลดรายการย้อนหลังครบ
7. ลาก EA ลงกราฟที่เปิดอยู่ ตั้ง Inputs ตามตาราง แล้วดู Experts/Journal ของ MT4 ว่าไม่มีข้อผิดพลาด
8. เพิ่มสินทรัพย์ที่ต้องการใน Market Watch เมื่อใช้ `MarketWatchOnly=true`
9. ในเว็บเพิ่มบัญชีด้วย URL และ Bridge token เช่นเดียวกับ MT5 ไม่ใส่ Publish token ในเว็บ
10. เปิด Journal และรอ History publication ครบทั้งชุด จึงใช้ประกอบ Risk ได้ หาก EA ไม่ส่งประวัติใหม่เกิน 90 วินาที การเปิดคำสั่งใหม่จะถูกระงับ

| Input ใน EA | วิธีตั้ง |
| --- | --- |
| `BridgeURL` | URL Bridge ที่ EA เข้าถึง เช่น `http://127.0.0.1:8787` |
| `BridgeToken` | Token ดูข้อมูลให้ตรงกับ Bridge |
| `PublishToken` | EA Publish token แยกเฉพาะเครื่องส่งข้อมูล ไม่ใช้ในเว็บ |
| `HistoryReady` | ตั้ง `true` หลังเลือก All History และตรวจความครบแล้ว |
| `HistoryDays` | จำนวนวันย้อนหลัง ค่าเริ่มต้น 90 |
| `ServerUTCOffsetHours` | UTC offset จริงของเวลา Server โบรกเกอร์ ไม่ใช่เวลาไทย |
| `PollSeconds` | รอบ Poll ค่าเริ่มต้น 2 วินาที |
| `MarketWatchOnly` | `true` อ่าน Symbol ใน Market Watch |
| `EnableTrading` | เริ่ม `false` เปลี่ยนเป็น `true` เมื่อตั้งสิทธิ์เทรดครบ |
| `TradeToken` | Token ส่งคำสั่งแยกจาก Bridge/Publish token |

EA ใช้ offset ที่คุณกำหนดเพื่อแปลงเวลาเป็น UTC ถ้าโบรกเกอร์เปลี่ยน DST ต้องตรวจและปรับเอง ประวัติที่คร่อม DST อาจต้องตรวจเวลากับ Statement อย่าถือว่าเลือก All History แล้วแปลว่าโบรกเกอร์ส่งประวัติครบทั้งชีวิตบัญชีเสมอ

ไฟล์ EA ในเวอร์ชันนี้ยังไม่ได้ Compile ด้วย MetaEditor หรือทดสอบกับ Terminal จริงในสภาพแวดล้อมที่ใช้พัฒนา ต้องตรวจขั้นตอนนี้บนเครื่อง Windows ของคุณ

## Token และการเชื่อมผ่าน HTTPS

| รายการ | ใส่ที่ไหน | สิทธิ์ |
| --- | --- | --- |
| ChatGPT Login | หน้าเว็บไซต์/โฮสติ้ง | เข้า Site ตามสิทธิ์ |
| Bridge token | เว็บ, EA, MCP client | อ่านข้อมูลและจัดการ Journal ของ Bridge นั้น |
| Trade token | เว็บที่ต้องเทรด และ EA ของ MT4 ที่เปิดเทรด | ส่งคำสั่งและเปลี่ยนกฎ Risk |
| Publish token | EA MT4 เท่านั้น | ส่งข้อมูลราคา สถานะและประวัติให้ Backend |
| AI API key | Environment ฝั่ง Bridge เท่านั้น | เรียกผู้ให้บริการโมเดล |
| Report link token | เฉพาะลิงก์ Track Record ที่สร้าง | อ่าน Snapshot นั้นจนหมดอายุหรือถูกยกเลิก |

Token ทั้งสามของ Bridge ต้องสุ่มต่างกันและยาวอย่างน้อย 32 ตัว โหมดสร้างอัตโนมัติเปลี่ยนค่าเมื่อ Restart ต้องนำค่าใหม่ไปใส่ที่เว็บ/EA/MCP ให้ตรงกัน ใช้ Secret manager หรือ environment ของกระบวนการรันสำหรับค่าคงที่ อย่าใส่ค่าจริงในไฟล์ตัวอย่างหรือ commit

**มือถือไม่ได้มอง `127.0.0.1` เป็นคอมพิวเตอร์ของคุณ** แต่เป็นมือถือเอง การใช้จากหลายเครื่องต้องมี Reverse proxy หรือ Tunnel HTTPS ไปที่ Bridge บน Windows ใช้ hostname ของคุณจริง เช่น `https://bridge.your-domain.example` แล้วตั้ง host/origin ให้ตรง

```powershell
$env:NS_ALLOWED_ORIGINS = "https://ns-capital-terminal.biw-modify004.chatgpt.site"
$env:NS_ALLOWED_HOSTS = "localhost,127.0.0.1,::1,bridge.your-domain.example"
py bridge.py --mode mt5 --port 8787
```

ตัวอย่างโดเมนข้างต้นเป็น Placeholder ต้องแทนด้วยโดเมน Gateway ที่คุณตั้งจริง คงพอร์ต Bridge ไว้เฉพาะ loopback ให้ proxy ส่ง Host ที่อยู่ใน allowlist และส่ง `Authorization`/`X-Trade-Token` โดยไม่เขียนค่าเหล่านี้ลง access log

ทุกคำขอที่มี Origin ต้องตรง allowlist ห้ามแก้เป็น `*` เพื่อข้ามปัญหา ใน production ต้องใช้ HTTPS ที่ใบรับรองถูกต้องและกำหนดการเข้าถึง Gateway ให้เหมาะกับ Token ของคุณ คู่มือนี้ไม่ได้สร้าง Tunnel โดเมน Windows VPS หรือใบรับรองให้เอง

## หลายบัญชี CFD และ Futures

ใช้ Terminal และ Bridge แยก process/port ต่อบัญชี ตัวอย่างบัญชีที่สองใช้พอร์ต `8788` และ path Terminal อีกตัว บัญชีบนเว็บเป็นโปรไฟล์ที่ยืนยันกับ Bridge แล้ว ไม่ใช่ช่องให้เปลี่ยน Server/Login ของ Terminal จากระยะไกล

ตั้ง `NS_DB_PATH` เป็นไฟล์เดียวกันบนดิสก์เครื่องเดียวกันได้ เพื่อรวม Ledger กลางโดยข้อมูลแยก `MT4/MT5 + Server + Login` ห้ามใช้ไฟล์ SQLite เดียวกันผ่าน Network share ข้าม VPS

```powershell
$env:NS_DB_PATH = "C:\NS-Capital-Data\trading.sqlite3"
$env:NS_MT5_PATH = "C:\Program Files\BROKER-SECOND-MT5\terminal64.exe"
py bridge.py --mode mt5 --port 8788
```

กำหนด Token ของ Bridge แต่ละ process แยกกัน และใช้ Bridge เดียวที่ส่งคำสั่งต่อบัญชีหนึ่งบัญชี หากใช้หลาย Windows VPS จะมีฐานข้อมูลแยกกัน เวอร์ชันนี้ยังไม่มีบริการ Cloud รวม Ledger ข้ามเครื่อง

ในเว็บเพิ่มโปรไฟล์แต่ละบัญชี แล้วสลับจากเมนูบัญชี/Journal/แผงซื้อขาย การเปลี่ยนบัญชีจะล้าง Preview ที่ยังไม่ส่งและปิดหน้าต่างแก้กฎเก่า ผลลัพธ์คำขอจากบัญชีเก่าจะไม่มาแทนหน้าบัญชีใหม่

Futures รองรับเฉพาะสัญญาจริงที่ MT5 และบัญชีโบรกเกอร์นั้นรายงาน ไม่ถือว่า CFD ของ Index เป็น Exchange Futures และไม่ได้เชื่อม Exchange Futures ทุกแห่งอัตโนมัติ

## เปิดสิทธิ์และส่งคำสั่งซื้อขาย

1. เริ่ม Bridge ใหม่ด้วย `py bridge.py --mode mt5 --enable-trading` หรือ `--mode mt4 --enable-trading`
2. คัดลอก Trade token ที่แยกจาก Bridge token ไปใส่ในบัญชีเว็บ
3. MT5 ต้องมีสิทธิ์บัญชี เปิด Algo Trading และอนุญาตการเทรดจาก external Python API ตามการตั้งค่า Terminal
4. MT4 ต้องมีสิทธิ์บัญชี เปิด AutoTrading/Allow live trading และตั้ง EA `EnableTrading=true`, `TradeToken` ให้ตรงกับ Bridge
5. ซิงก์ประวัติและตั้ง Risk Engine ของบัญชีนั้นก่อนเปิดสถานะใหม่
6. เลือก Symbol จริงจากโบรกเกอร์ เลือก Buy หรือ Sell ระบุ Lot, SL, TP และ Deviation
7. กด **ตรวจสอบคำสั่ง** แล้วอ่านบัญชีปลายทาง ราคา ปริมาณ ต้นทุนประมาณการและความเสี่ยงใน Preview
8. กดยืนยันเพื่อส่งจริง Preview อายุ 30 วินาที ใช้ได้ครั้งเดียว ถ้าบัญชี/กฎ/ราคาเปลี่ยนให้ตรวจใหม่
9. ดู Receipt และตรวจ Positions/History ใน Terminal ให้สอดคล้องกัน

รองรับ Market order, ปิดเต็มสถานะตาม ticket และปรับ SL/TP เวอร์ชันนี้ไม่มีหน้าส่ง Pending order, ปิดบางส่วนแบบกำหนดจำนวน, OCO หรือ Copy trade แบบหลายบัญชีในคำสั่งเดียว

`Lot` ของบัญชีโบรกเกอร์อ้างอิงสเปกสัญญาของ Symbol ไม่ใช่หน่วยสินทรัพย์ใน Paper/Backtest บัญชี MT5 แบบ Netting รวมสถานะของ Symbol เดียวกัน การกลับฝั่งใช้คำสั่ง Close/SLTP ให้ชัดก่อนเปิดฝั่งใหม่เมื่อ Risk Engine ปฏิเสธ

สถานะ `filled` คือยืนยันผลตามข้อมูลโบรกเกอร์ ส่วน `partial`, `accepted`, `pending` และ `unknown` ยังต้องตรวจรายละเอียด **อย่าส่งคำสั่งใหม่ซ้ำเพียงเพราะเว็บ Timeout** ใช้ Receipt เดิมและตรวจ Terminal ก่อน รายการที่ไม่ทราบผลไม่ถูก Retry execution อัตโนมัติ

Receipt และ Request ID เก็บในฐานกลางข้ามการ Restart ได้ แต่ Preview ที่ยังไม่ส่งอยู่ในหน่วยความจำและใช้ต่อหลัง Restart ไม่ได้ ราคาที่ได้จริงอาจต่างจาก Preview

## ตั้งค่า Backend Risk Engine

เปิดแผงซื้อขาย → **Backend Risk → ตั้งกฎ** ต้องเชื่อมบัญชี มี Trade token เปิดโหมดเทรด และมีประวัติที่ซิงก์ครบ

| ช่อง | ความหมาย |
| --- | --- |
| `Risk / trade % equity` | ขาดทุนประมาณการถึง SL ต่อคำสั่ง เทียบ Equity ปัจจุบัน |
| `Daily Loss %` | เพดานขาดทุนรายวันเทียบ Balance ต้นวันตามวันซื้อขายที่ตั้ง |
| `Max Drawdown %` | เพดานลดลงจากยอด Equity สูงสุดที่ Backend สังเกตหลัง Reference |
| `Cost / lot` | เผื่อต้นทุนไป-กลับต่อ Lot ในสกุลเงินบัญชี |
| `Slippage points` | เผื่อราคาที่ Entry/SL ตาม Points ของ Symbol |
| `Reset time UTC` | เวลาเริ่มวันซื้อขายใหม่ หน้าฟอร์มใช้ UTC |
| `หยุดเปิดใหม่` | Pause การเพิ่มความเสี่ยงด้วยตนเอง |

เลือกเปอร์เซ็นต์ตามแผนของคุณ ระบบไม่เติมเพดานความเสี่ยงอัตโนมัติ ค่าเวลาเริ่มฟอร์ม `17:00 UTC` ตรงกับ `00:00` เวลาไทยของวันถัดไป วันในหน้าเกณฑ์พฤติกรรมใช้ UTC แยกจากวัน Risk ที่ตั้งได้

**Daily P&L** = กำไรขาดทุนสุทธิที่บันทึกในวันนั้น + Equity − Balance − Credit ดังนั้นรวมผลลอยตัวปัจจุบันด้วย ไม่ใช่การเปลี่ยน Equity จากต้นวันอย่างเดียว

**Balance ต้นวัน** = Balance ปัจจุบัน − ผลกระทบ Balance ของรายการวันนี้ เพื่อแยกผลเงินฝากถอนออกจากฐาน Daily limit; Daily loss = ค่าสูงสุดระหว่าง 0 กับค่าติดลบของ Daily P&L

**Drawdown** คำนวณจากยอด Equity สูงสุดที่ Backend สังเกต ปรับฐานเมื่อมีเงินเข้าออก/เครดิตที่จำแนกแล้ว เป็น trailing observed peak หลัง Reference ไม่ใช่สถิติ Tick ย้อนหลังครบทั้งชีวิตบัญชี

Backend ประมาณขาดทุนถึง SL ในสกุลเงินบัญชี MT5 ใช้ `order_calc_profit` ของ Terminal ส่วน MT4 ใช้ Tick size/value ที่ EA รายงาน หากไม่มีสเปกที่เชื่อถือได้จะไม่เปิดใหม่ รวม Deviation/Slippage และต้นทุนที่ตั้งไว้ด้วย

ตรวจทั้ง Preview และก่อน Execute อีกครั้ง Risk ต้องผ่านเพดานต่อไม้และงบ Daily/DD ที่เหลือ การเพิ่มสถานะฝั่งเดียวกันใน MT5 Netting พิจารณาความเสี่ยงรวมของสถานะที่เพิ่มด้วย

เมื่อ Daily limit ถูกแตะ จะล็อกหยุดเปิดใหม่จนถึงวันถัดไปตาม Reset time แม้ P&L ฟื้นแล้ว เมื่อ DD limit ถูกแตะ จะล็อกต่อข้าม Restart จนตรวจบัญชีและ Reset Reference ตามเงื่อนไข

ยังอนุญาตให้ Close และปรับ SL เพื่อลดความเสี่ยงแม้ Pause/ชนเพดาน แต่ต้องผ่านสิทธิ์และเงื่อนไขโบรกเกอร์ การขยับ SL ให้เสี่ยงมากขึ้นต้องผ่าน Risk ใหม่

Reset DD Reference ต้องไม่มีสถานะเปิด ตรวจ Statement ใส่เหตุผลและยืนยัน การ Reset นี้ไม่ล้าง Daily halt และมี Audit log

Risk Engine คุมเฉพาะคำสั่งที่ผ่าน Bridge นี้ ไม่สั่งปิดสถานะเก่าทั้งหมดเมื่อชนเพดาน ไม่ควบคุม EA/แอปอื่น และยังไม่ใช่ระบบจองงบความเสี่ยงรวมทุกสถานะ กรณีหลายสถานะขาดทุนพร้อมกัน Gap หรือ Stop fill เกินราคาที่ประเมิน ขาดทุนจริงอาจเกินเพดานได้

## Auto Journal และการตรวจข้อมูล

เลือกบัญชีและช่วงเวลาใน Journal แล้วกด **ซิงก์ประวัติจริง** ตารางแสดง Deal/รายการที่โบรกเกอร์ส่งมา ไม่ใช่จำนวนเทรดปิดครบ แยก Profit, Commission, Swap, Fee และ Net ตามเครื่องหมายต้นทาง สกุลเงินเป็นสกุลเงินบัญชี

- MT5 นำเข้า Deal และอ่านช่วงซ้อนซ้ำเพื่ออัปเดตค่าที่โบรกเกอร์แก้ ไม่เพิ่มรายการซ้ำด้วย Ticket เดิม
- MT4 นำเข้า Account History เป็นชุด จะแสดงเป็นประวัติครบเมื่อรับทุก Batch สำเร็จ
- เงินฝาก ถอน และ Credit แยกจากกำไรการเทรด
- MT4 `Balance` อาจเป็นเงินฝากถอนหรือค่าบริการ จึงรอจำแนก ไม่เดาจาก Comment
- Correction/Cancelled adjustment ที่กำกวมอาจต้องตรวจและจำแนกด้วยเช่นกัน

ถ้ามี **รอจำแนก** ให้เปิด Statement ของโบรกเกอร์ ตรวจ Ticket แล้วกด **จำแนก** เลือก Cash flow หรือ Trading cost พร้อมเหตุผล ต้องมี Trade token ข้อมูลต้นทางยังเก็บและมี Audit log การจำแนกผูกกับบัญชี/Ticket และคงอยู่เมื่อซิงก์ซ้ำ

รายการรอจำแนกยังไม่รวมใน Net P&L ที่จำแนกแล้ว จะแสดงยอดแยกให้ทราบ และ Risk อาจหยุดเปิดใหม่จนตรวจครบ อย่าใช้การจำแนกเพื่อทำให้ตัวเลขดูดีหรือข้าม Halt

ฐานกลางมีค่าเริ่มต้นที่ `%LOCALAPPDATA%\NSCapital\trading.sqlite3` บน Windows ปรับด้วย `NS_DB_PATH` ได้ ประวัติ โน้ต กฎ Risk, Halt, Receipt, Coaching และรายการแชร์อยู่ในไฟล์นี้ **ไม่ใช่ข้อมูลที่เก็บในบัญชี ChatGPT หรือบน GitHub**

การซิงก์ทำงานต่อเมื่อ Bridge/Terminal เปิดอยู่ แม้ปิดหน้าเว็บ หากโบรกเกอร์ไม่ให้ข้อมูลเก่าหรือ Terminal โหลดมาไม่ครบ โปรแกรมไม่สามารถสร้างรายการที่หายไปให้เอง

## Dashboard และสูตรสถิติ

**MT5 Closed trades:** รวม Deal ของ Position เป็นรอบตั้งแต่เริ่มไม่มีสถานะจนปิดหมด เปิดเพิ่ม/ปิดบางส่วนยังนับเป็นรอบเดียว รายการ Reverse `INOUT` แยกส่วนปิดกับส่วนเปิดใหม่และแบ่ง Commission/Fee ตาม Volume ส่วน Profit/Swap ของขาปิดอยู่ในรอบเก่า

**MT4 Closed trades:** นับ Closed tickets ที่นำเข้า การปิดบางส่วนอาจแยกเป็นหลาย Ticket ตาม Terminal จึงไม่อ้างว่าเป็น flat-to-flat แบบ MT5

รอบที่ขาด Deal เปิด มีข้อมูลกลับด้านที่ต่อไม่ครบ หรือมีเงื่อนไขที่คำนวณต่อไม่ได้ จะถูกเว้นจาก Win Rate พร้อมจำนวนรายการที่เว้น สถานะยังเปิดไม่ถือว่าชนะ/แพ้

| ตัวเลข | นิยาม |
| --- | --- |
| Win Rate | จำนวนเทรดปิดที่ Net > 0 ÷ เทรดปิดทั้งหมด รวม Breakeven ในตัวหาร |
| Profit Factor | ผลรวม Net บวกของเทรดปิด ÷ ค่าสัมบูรณ์ผลรวม Net ลบ |
| `∞` | มีเทรดกำไรแต่ยังไม่มีเทรดขาดทุนในกลุ่มที่นับ ไม่ใช่หลักฐานว่าระบบไร้ความเสี่ยง |
| Closed Net | กำไรขาดทุนของรอบปิด รวมต้นทุนที่ผูกกับ Deal ของรอบนั้น |
| Booked Net | Net ของรายการเทรด/ต้นทุนที่บันทึกในช่วงที่เลือก รวมต้นทุนขาเปิดได้ ไม่รวมเงินฝากถอนหรือรายการรอจำแนก |
| Booked drawdown | ยอดลดลงสูงสุดของกราฟ Booked P&L รายวันในช่วงที่เลือก หน่วยเงิน ไม่ใช่ Equity DD รวม Floating |
| ต้นทุนแยกบัญชี | ค่าบริการที่ไม่มีข้อมูลให้ผูกเข้ารอบเทรดอย่างแน่ชัด รวมใน Booked Net แต่ไม่เดาไปเปลี่ยน Win Rate/PF |

สถิติเทรดปิดเลือกตามเวลาปิดของรอบ โดยอ่านขาเปิดที่เก็บไว้ก่อนช่วงหน้าจอประกอบด้วย หากรอบเปิดก่อนขอบเขตนำเข้าและไม่มีขาเปิด จะยังไม่นับรอบนั้น

กราฟ P&L รวมยอดตามวัน UTC ใช้เวลาไทยในการแสดงวัน/เวลาบางตำแหน่ง ตาราง Deal แสดงทั้ง UTC และ TH สถิติ Dashboard ไม่ควรถูกนำไปเปรียบเทียบกับ Equity DD ของ Risk Engine โดยตรงเพราะวัดคนละชุดข้อมูล

## แผน Setup และโน้ต

ส่วนโน้ตรายบัญชีอยู่ใต้ตาราง Ledger เลือก Setup ใส่ Position ID หากต้องการผูกกับเทรด แล้วเขียนแผน/บทเรียน กด **บันทึกที่ Backend** ข้อความยาวได้ไม่เกิน 2,000 ตัวอักษร

ใช้ **BTR** สำหรับทบทวนก่อนเทรด และ **DCE** สำหรับบทเรียนหลังจบ หรือเลือก Trend Following, Mean Reversion, Breakout, General ตามแผนคุณ ตัวเลือกเหล่านี้เป็นแท็กจัดกลุ่ม ไม่ใช่การรับรองกลยุทธ์

ตัวอย่างโครงสร้างโน้ต: บริบทตลาด → Setup → เงื่อนไขเข้า/ยกเลิก → SL/เหตุผล → การทำตามแผน → บทเรียนครั้งถัดไป ไม่ต้องใส่รหัสผ่านหรือ Token ในโน้ต

Dashboard ใช้ Setup ล่าสุดที่ผูกกับ Position ถ้า Position เดียวมีรอบปิดเพียงรอบเดียว สามารถใส่ Setup หลังปิดได้ ถ้า MT5 Netting ใช้ Position เดิมหลายรอบจาก Reverse จะใช้เฉพาะโน้ตในช่วงเปิด-ปิดรอบนั้นเพื่อเลี่ยงการจัดกลุ่มผิด

โน้ตเดิมในเบราว์เซอร์อยู่ในหัวข้อ **โน้ตในเบราว์เซอร์เดิม / CSV และงานวิจัย** ไม่มีบัญชีอ้างอิงจึงไม่ย้ายเข้าพอร์ตใดเอง Backup workspace ไม่ใช่ Backup ของ Ledger กลาง

## สังเกต Overtrade และการกลับเข้าเร็วหลังขาดทุน

เปิด **ตั้งเกณฑ์พฤติกรรม** ใน Journal เลือกเปิดการสังเกต ตั้งจำนวน Entry สูงสุดต่อวัน ช่วงพักหลังขาดทุน และอัตราขนาดที่เพิ่ม แล้วกดบันทึก เกณฑ์ตั้งแยกบัญชีและปิดอยู่จนคุณเลือกเปิด

**Entry count:** นับคำสั่งเข้าโดย deduplicate หลาย Fill ของ Order เดียวกัน ไม่ใช่นับทุก Deal เป็นหนึ่งไม้ วันใช้ UTC

**Rapid re-entry with increased size:** ดูการเข้า Symbol เดิมหลังเทรดขาดทุน ภายในเวลาที่กำหนด และขนาดเพิ่มถึงอัตราที่ตั้ง แสดง Ticket, จำนวนนาที และตัวคูณขนาดเป็นหลักฐาน

เงื่อนไขเหล่านี้เป็นข้อสังเกตให้คุณทบทวน ไม่สามารถรู้เจตนาหรือสรุปอารมณ์ว่าเป็น Revenge Trade ได้แน่ชัด ไม่เปรียบเทียบ Lot ข้าม Symbol และอาจมีเหตุผลตามแผนที่ถูกต้องอยู่เบื้องหลัง

การสังเกตใช้ประวัติที่นำเข้า MT4 จึงเห็น Entry จาก Closed tickets ที่มีเวลาเปิดแล้ว ไม่ใช่ตัวติดตามอารมณ์หรือนับ Open entries ทั้งหมดแบบทันที ฟังก์ชันนี้แสดงข้อสังเกตและไม่บล็อกคำสั่ง ใช้ Risk Engine สำหรับเพดานที่ Backend บังคับ

## Ollama, LM Studio และ AI Coaching

ติดตั้ง Ollama บนเครื่อง Bridge หรือเครื่องที่ Bridge ติดต่อได้ ดาวน์โหลดโมเดลที่คุณเลือก แล้วดูชื่อจริงด้วย `ollama list` ห้ามใช้ชื่อ Placeholder เป็น model ID

```powershell
ollama list
$env:NS_AI_PROVIDER = "ollama"
$env:NS_AI_BASE_URL = "http://127.0.0.1:11434/v1"
$env:NS_AI_MODEL = "YOUR_EXACT_INSTALLED_MODEL_ID"
py bridge.py --mode mt5
```

ถ้า Ollama ยังไม่มีโมเดล ให้ใช้ `ollama pull` ตามด้วยชื่อโมเดลที่คุณเลือกจากรายการของผู้ให้บริการ ประสิทธิภาพและหน่วยความจำขึ้นกับโมเดลและเครื่อง เว็บไม่ดาวน์โหลดหรือเทรนโมเดลให้เอง

สำหรับ LM Studio เปิด Local Server และเลือกโมเดลที่โหลดจริง:

```powershell
$env:NS_AI_PROVIDER = "lm-studio"
$env:NS_AI_BASE_URL = "http://127.0.0.1:1234/v1"
$env:NS_AI_MODEL = "YOUR_EXACT_LOADED_MODEL_ID"
py bridge.py --mode mt5
```

API อื่นใช้ `NS_AI_PROVIDER=openai-compatible`, `NS_AI_BASE_URL` ที่มี `/v1` ตาม API และ `NS_AI_MODEL` ถ้าผู้ให้บริการใช้ Key ให้ตั้ง `NS_AI_API_KEY` ฝั่ง Bridge ไม่ส่งให้เบราว์เซอร์ ต้อง HTTPS ยกเว้น localhost HTTP

ในแผง AI กดตรวจสถานะเพื่อเช็ก `/models` ชื่อโมเดลต้องตรง ตัวเลข **Configured**, **Reachable**, **Model available** เป็นคนละสถานะ การเห็นโมเดลในรายการยังไม่พิสูจน์ว่า Inference สำเร็จ

ใน Journal กด **วิเคราะห์บัญชีนี้ด้วย AI** หลังมีเทรดปิดครบ ระบบอ่านสถิติที่ Backend คำนวณเอง ส่งเฉพาะสถิติ เกณฑ์และหลักฐานตามเงื่อนไข ไม่ส่งเลขบัญชี Token, Comment โบรกเกอร์ หรือข้อความโน้ตส่วนตัว

Coaching แสดงภาพรวม สิ่งที่ทำได้ดี จุดควรทบทวน และแผนพัฒนากระบวนการ พร้อมชื่อโมเดล วันที่และจำนวนเทรด ณ ตอนวิเคราะห์ ผลเก่าคงอยู่จนกดวิเคราะห์ใหม่ ไม่อัปเดตเองเมื่อมีเทรดเพิ่ม และบันทึกแยกบัญชีที่ Backend

ถ้าใช้โมเดลผ่าน API ภายนอก สถิติที่ส่งจะไปยังผู้ให้บริการนั้นตาม URL ที่คุณตั้ง หากใช้ Ollama localhost ก็ประมวลผลที่เซิร์ฟเวอร์นั้น ไม่ได้แปลว่าใช้ในเครื่องเมื่อคุณเปลี่ยน Base URL ไปภายนอก

AI Draft ในแผงซื้อขายใช้ Symbol/Quote/Contract ของบัญชีจริง โมเดลเสนอ `open` หรือ `pass` ได้ แต่ไม่ส่งคำสั่ง ต้องกดนำ Draft มาใช้ ตรวจ Preview และยืนยันด้วยตนเอง Backend ตรวจ Risk เช่นเดียวกับคำสั่งปกติ

เวอร์ชันนี้ยังไม่มี Training dataset pipeline, Walk-forward optimization, Model registry หรือระบบรัน AI เทรด 24 ชั่วโมง การต่อ Ollama คือเชื่อม Inference ของโมเดลที่ติดตั้งแล้ว

## MCP

MCP ให้โปรแกรม AI ที่รองรับอ่านข้อมูลจาก Bridge และขอ Draft ได้ มี 6 เครื่องมือ: `get_connection_status`, `list_symbols`, `get_quote`, `get_candles`, `get_trading_state`, `suggest_trade` ไม่มีเครื่องมือส่ง Execute order

**แบบ stdio:** ใช้ไฟล์ `mcp-config.example.json` เป็นโครง ปรับ path Python, path `mcp_server.py`, URL และ Bridge token ให้ตรงกับเครื่องในโปรแกรมที่รองรับ MCP ขณะใช้งานต้องเปิด `bridge.py` ไว้ด้วย

**แบบ Streamable HTTP:** ใช้ `<Gateway URL>/mcp` และ Header `Authorization: Bearer <Bridge token>` ตามรูปแบบใน `mcp-http.example.json` ถ้า Client อยู่บน Cloud ต้องเข้าถึง HTTPS Gateway ได้ ไม่ใช้ localhost ของ Windows จาก Cloud โดยตรง

อย่าใส่ Trade token หรือ Publish token ใน MCP config เครื่องมือ `suggest_trade` เป็นคำขอโมเดลแบบมีค่าใช้จ่าย/ใช้ทรัพยากรและอาจเลือกไม่เทรด ผลลัพธ์ไม่ใช่คำสั่งที่ส่งแล้ว

หาก MCP client ไม่รองรับ Header หรือการเชื่อม Local network ให้ใช้ stdio บนเครื่อง Bridge หรือ Gateway ที่ตรงกับนโยบาย Client ไม่มีระบบติดตั้ง/เชื่อมบัญชี Axi ผ่าน MCP ให้อัตโนมัติ Axi หรือโบรกเกอร์อื่นต้องเปิดบัญชีใน MT4/MT5 ที่รองรับตามปกติ

## Backtesting และ Paper Trading

1. เลือกข้อมูลบนกราฟและ Timeframe ให้ถูกต้อง
2. ใน Strategy Lab เลือกแนวคิดหรือแก้กฎ JSON ตรวจค่าเงินเริ่มต้น ความเสี่ยง ค่าธรรมเนียม Slippage และ SL/TP
3. กด Run backtest แล้วอ่าน Performance, Trades และสมมติฐานท้ายผล
4. เปลี่ยนช่วงเวลา/สินทรัพย์ที่ไม่ได้ใช้ปรับกฎเพื่อดูความคงทนของผล และบันทึกเวอร์ชันกฎที่ทดสอบ

เครื่องมือวิจัยในเบราว์เซอร์นี้ใช้ข้อมูลที่โหลดบนกราฟและจำนวนเป็นหน่วยสินทรัพย์ ไม่ใช่ Simulator สัญญา CFD/Futures แบบครบถ้วน ไม่มีการจำลอง Margin/Swap calendar/สภาพคล่องของโบรกเกอร์ทั้งหมด ผลบนกราฟไม่ยืนยันผลที่จะได้กับบัญชีจริง

Paper Trading เป็นบัญชีจำลองในเบราว์เซอร์ ใช้ฝึกขั้นตอนและแยกจาก Ledger จริง ห้ามนับ Paper/Backtest เป็น Track Record โบรกเกอร์ ปิดเว็บไซต์อาจทำให้การจำลองไม่ติดตามตลาดต่อเนื่อง

## Track Record

เปิด Journal → **Track Record** เลือกช่วงเวลาที่ต้องการจากหน้า Journal ก่อน จากนั้นเลือกระยะลิงก์หมดอายุ 1/7/30 วัน ติ๊กยินยอมและกด **สร้างลิงก์รายงาน**

ระบบให้สร้างเมื่อมีเทรดปิดครบ ช่วงประวัติครบและสด ไม่มีรายการรอจำแนกและไม่มีรอบขาดข้อมูลเปิดที่ตรวจพบ หากสร้างไม่ได้ให้ซิงก์/ตรวจ Statement ก่อน ไม่แก้ข้อมูลเพื่อข้ามเงื่อนไข

คัดลอกลิงก์ทันที ระบบเก็บเฉพาะ Hash ของ Token จึงไม่แสดงลิงก์เดิมซ้ำ รายงานมีสถิติรวมและกราฟ ไม่มีเลขบัญชี Ticket, Position ID, โน้ตหรือ Trade token เป็น Snapshot คงที่ ไม่อัปเดตผลหลังสร้าง

ผู้มีลิงก์และเข้าถึง Site/Gateway ได้อ่านรายงานจนถึงเวลาหมดอายุ อย่าใส่ข้อมูลส่วนตัวในนามแฝงหรือนำลิงก์ลงที่สาธารณะโดยไม่ตั้งใจ ถ้าไม่ต้องการให้ใช้ต่อ กด **ยกเลิกลิงก์** ได้ทันทีจากรายการรายงาน

**สิทธิ์ Site ยังคงเดิม:** เว็บนี้เป็นส่วนตัว จึงต้องให้สิทธิ์ผู้รับผ่าน Site ก่อนหรือปรับนโยบายเข้าถึงโดยเจ้าของ รายงานไม่ทำให้ Terminal ทั้งเว็บเป็น Public และไม่ได้สร้าง Public broker-verified profile

Bridge ต้องทำงานและ Gateway ต้องเข้าถึงได้ตอนเปิดรายงาน ลิงก์ใส่ Report token ใน URL fragment แล้วส่งไปอ่าน Snapshot แยกจากเส้นทางเทรด ไม่ให้สิทธิ์อ่านบัญชีอื่นหรือส่งคำสั่ง

ข้อความ **ไม่ได้รับการยืนยันโดยโบรกเกอร์/ผู้ตรวจสอบอิสระ** แสดงในรายงานเสมอ แม้ข้อมูลเริ่มจาก Terminal ผู้ดูแลเครื่องอาจควบคุมข้อมูลใน Bridge ได้ จึงไม่ควรใช้คำว่า Verified broker record โดยไม่มีการรับรองเพิ่มเติม

## Leaderboard

Leaderboard อยู่ภายใน Bridge/ฐานข้อมูลกลางนี้ ไม่ใช่อันดับผู้ใช้ทั่วโลก ไม่เปิดเผยบัญชีโดยอัตโนมัติและไม่สร้างรายชื่อ Sample

เงื่อนไขเข้าร่วม: ยินยอม ใช้นามแฝง 2–40 ตัวอักษร มีข้อมูลครบ 30 วัน ไม่มีรายการกำกวม/รอบที่ขาดข้อมูล มีอย่างน้อย 20 เทรดปิดครบ และมีเทรดขาดทุนเพื่อคำนวณ Profit Factor แบบจำกัดได้

จัดเรียง **Profit Factor 30 วันหลังต้นทุนที่ผูกกับเทรด** แล้วจำนวนเทรด ไม่จัดจากจำนวนเงินกำไรที่ข้ามสกุลเงินกัน ต้นทุนรวมบัญชีที่ไม่ได้ผูกต่อไม้ไม่ถูกเดาไปกระจายใน PF จึงต้องอ่านคำอธิบายประกอบ ไม่ถือว่าอันดับสูงแปลว่าความเสี่ยงต่ำ

ติ๊กยินยอมแล้วกด **เข้าร่วม / อัปเดตสถิติ** ด้วยตนเอง Snapshot หมดอายุจากอันดับหลัง 24 ชั่วโมง ต้องกดอัปเดตใหม่เพื่อเข้าร่วมต่อ กด **ถอนบัญชีนี้จากอันดับ** เพื่อหยุดแสดงได้

## ส่งออกและสำรองข้อมูล

**CSV Journal:** กด CSV ในบัญชีและช่วงที่เลือก ดาวน์โหลดรายการ Deal พร้อม Cost fields และสกุลเงิน สูงสุด 100,000 แถวต่อครั้ง ถ้าเกินให้เลือกช่วงสั้นลง ข้อความที่ขึ้นต้นด้วยสูตร Spreadsheet จะถูก escape CSV เป็นสำเนาสำหรับวิเคราะห์ ไม่ใช่ Backup ฐานข้อมูลทั้งหมด

**Backup workspace:** เมนู Backup ของเว็บใช้กับ Layout/กฎ/ข้อมูลในเบราว์เซอร์ ไม่รวม Token และไม่ใช่ Backup ของฐานกลาง

**Backup Ledger:** ใช้คำสั่งของ `database.py` เพื่อสร้างสำเนา SQLite ที่สอดคล้องกัน ไม่คัดลอกไฟล์ดิบขณะที่หลาย process กำลังเขียน:

```powershell
Set-Location C:\NS-Capital-Bridge
$journalBackupStamp = Get-Date -Format "yyyyMMdd-HHmmss"
py database.py "$env:LOCALAPPDATA\NSCapital\trading.sqlite3" ".\backup\trading-$journalBackupStamp.sqlite3"
```

ถ้าใช้ `NS_DB_PATH` ให้เปลี่ยน Source เป็น path นั้น คำสั่งไม่ทับไฟล์ Backup ที่มีอยู่ เก็บสำเนาอีกที่หนึ่งที่จำกัดสิทธิ์และทดสอบเปิดกู้คืนเป็นระยะ

**กู้คืน:** หยุด Bridge ทุก process ที่ใช้ไฟล์เดียวกัน เก็บไฟล์ปัจจุบันแยกไว้ก่อน วาง Backup ที่ path ฐานจริงโดยตรวจชื่อให้ถูกต้อง เริ่ม Bridge อีกครั้ง ตรวจบัญชี ประวัติ Halt และ Receipt กับ Terminal ก่อนส่งคำสั่งใหม่

ฐานข้อมูลไม่ได้เข้ารหัสเอง ภายในมีประวัติบัญชีและข้อความ Journal ใช้สิทธิ์ไฟล์และการเข้ารหัสดิสก์/Backup ตามเครื่องของคุณ ไม่ใส่ `.sqlite3`, `.env`, Token, Statement จริงหรือไฟล์ Backup ลง GitHub

## มือถือ แท็บเล็ต และติดตั้งเป็นแอป

หน้าเว็บปรับตามหน้าจอ โทรศัพท์ใช้เมนูล่างและ Drawer; Tablet ใช้พื้นที่กราฟ/Journal กว้างขึ้น ตารางรายการยังเลื่อนแนวนอนได้ ตัวควบคุมและ Dialog ปรับตามพื้นที่ ไม่สร้างกราฟราคาอีกชุดแยกสำหรับมือถือ

**Android/คอมพิวเตอร์:** เปิดเว็บใน Chrome/Edge ที่รองรับ แล้วกดปุ่มติดตั้งในเว็บหรือเมนูเบราว์เซอร์ → ติดตั้งแอป

**iPhone/iPad:** เปิดใน Safari → แชร์ → เพิ่มไปยังหน้าจอโฮม ถ้าเปิดจากแอป ChatGPT ให้เปิด URL เดียวกันในเบราว์เซอร์ก่อน

โหมดออฟไลน์เก็บเฉพาะเปลือกแอปและข้อมูลในเครื่องที่มีอยู่ ราคา บัญชี AI และการส่งคำสั่งต้องออนไลน์ Service worker ไม่เก็บ API/Token/Quote/Order และไม่ Queue คำสั่งไว้ส่งเมื่อกลับออนไลน์

เมื่ออัปเดตเวอร์ชัน ให้จบการตรวจคำสั่ง ปิดแท็บ NS Capital ทุกแท็บแล้วเปิดใหม่ ระบบไม่บังคับ Reload ระหว่างเทรด ล็อกอินของ Site และนโยบาย Local network ของอุปกรณ์ยังมีผลแม้ติดตั้ง PWA แล้ว

## Deployment และการดูแล production

เว็บที่ให้ไว้เผยแพร่บน Sites แล้ว โดยใช้สิทธิ์ส่วนตัวและ Authentication ของโฮสติ้ง Frontend ไม่สามารถรัน MT4/MT5/Python หรือ Ollama บนเครื่อง Windows ให้คุณเอง ต้องมีส่วน Backend ตามผังนี้:

**เว็บ HTTPS/PWA → HTTPS Gateway → Broker Bridge + SQLite → MT4/MT5 บน Windows** และ **Bridge → Ollama/LM Studio/API** เมื่อตั้ง AI

สิ่งที่ต้องตั้งจริงก่อนใช้ต่อเนื่อง:

1. Windows/Windows VPS เปิด Terminal และ Bridge ของแต่ละบัญชีพร้อมระบบเริ่มใหม่หลังเครื่อง Restart
2. HTTPS Gateway ที่ใบรับรองใช้ได้ Host/Origin allowlist ตรง URL จริง และไม่บันทึก Token ลง Log
3. Token แยกบทบาทและแต่ละบัญชี จัดเก็บใน environment/secret ของกระบวนการ ไม่ส่งผ่าน URL query
4. ตำแหน่งฐานกลางและ Backup ที่กู้คืนได้ รวมพื้นที่ดิสก์และสิทธิ์ไฟล์
5. นาฬิกาเครื่อง/UTC offset ถูกต้องและประวัติครบ คอยดู Sync error ไม่ปล่อยเป็นข้อมูลเก่าที่ดูเหมือน Live
6. ตั้ง Risk ของบัญชีทุกบัญชีและทดสอบด้วย Demo ทั้งเปิด ปิด แก้ SL และ Halt
7. ถ้าใช้ AI ให้ตรวจชื่อโมเดลและ Inference จริง รวมทรัพยากร/ค่าใช้จ่ายของผู้ให้บริการ
8. ก่อนขยายเป็นบริการหลายสมาชิก เพิ่มฐานผู้ใช้/สิทธิ์ข้อมูลฝั่ง Backend, session ต่อผู้ใช้, การแยก Tenant, encrypted credentials, monitoring และการกู้คืนระบบ ปัจจุบันเป็นแพลตฟอร์มส่วนบุคคลที่ใช้ Token ของ Bridge

สำหรับนักพัฒนาที่ใช้ GitHub: โค้ดอยู่ในโฟลเดอร์ `ns-capital-terminal/` ของ Repository, หน้าจอใน `src/`, Backend ใน `broker-bridge/`, คู่มือใน `docs/`, Tests ใน `tests/`, Build ใน `scripts/` และ Workflow ใน `.github/workflows/` ที่ root ของ Repository

```bash
cd ns-capital-terminal
npm ci
npm test
python -W error::ResourceWarning -m unittest discover -s tests -p 'test_*.py' -q
npm run build
```

ผล Build คือ `dist/` ซึ่งมีเว็บ ไอคอน คู่มือและชุด Bridge ไม่มีฐานจริงหรือ Token ตรวจ CI และ PR ก่อน Merge ค่า Site identity อยู่ใน `.openai/hosting.json` ห้ามเปลี่ยน project_id เมื่ออัปเดต Site เดิม

การเผยแพร่ผ่าน Sites ใช้กระบวนการ Build/Package/Save version/Deploy ของ Sites เพื่อคง Authentication และ Audience เดิม การ Push GitHub branch เพียงอย่างเดียวไม่ได้ยืนยันว่าเวอร์ชันนั้นขึ้น production แล้ว

## อัปเกรดจากเวอร์ชันก่อนหน้า

1. ตรวจและจบคำสั่งที่ยัง Pending/Unknown ใน Terminal ก่อน
2. Backup Ledger ถ้ามี และ Backup workspace ในเว็บ
3. หยุด Bridge แล้วแตกชุด Bridge รุ่นใหม่ครบทุกไฟล์ทับโค้ด ไม่ทับฐานจริงด้วยไฟล์ Sample
4. MT4 ต้อง Compile EA ใหม่ เพิ่ม Publish token/HistoryReady และตรวจ All History อีกครั้ง
5. ใช้ `NS_DB_PATH` เดิมเพื่อคงประวัติและ Receipt ฐานรุ่นนี้สร้าง/เพิ่มตารางด้วย schema version 2 และปฏิเสธฐานที่ใหม่กว่าโปรแกรม
6. เริ่ม Bridge ด้วย Token/port/path/AI environment เดิม ตรวจ Account identity และ Sync status
7. ตั้งกฎ Risk หากเป็นบัญชีที่ยังไม่เคยตั้ง การอัปเดต Bridge ทำให้ New entries ต้องผ่าน Risk ก่อน แม้เว็บเวอร์ชันเก่าจะเคยเปิดเทรดได้
8. ปิดแท็บเว็บทุกแท็บและเปิดใหม่ ตรวจหมายเลขเวอร์ชันที่ Footer

อย่า Downgrade Bridge ทับฐานที่ schema ใหม่กว่าเพื่อข้ามข้อผิดพลาด เก็บ Binary/โค้ดเวอร์ชันที่ตรงกับ Backup ที่จะกู้คืนไว้ด้วย

## แก้ปัญหาตามอาการ

| อาการ | ตรวจและแก้ตามลำดับ |
| --- | --- |
| เข้าเว็บไม่ได้/Access denied | ตรวจบัญชี ChatGPT และสิทธิ์ Site ของผู้ใช้ เข้าหน้า Login อีกครั้ง การมีลิงก์ไม่เท่ากับมีสิทธิ์ |
| Binance ไม่อัปเดต | ตรวจอินเทอร์เน็ต สถานะ Feed กด Reconnect และตรวจว่าเครือข่ายอนุญาต API/WebSocket ของ Binance |
| เชื่อม Bridge ไม่ได้ | ตรวจ process, port, URL, Token, HTTPS และ Origin/Host allowlist; มือถือใช้ localhost ของ PC ไม่ได้ |
| `Invalid bridge token` | Token เปลี่ยนหลัง Restart หรือใส่ผิด Bridge ใส่ค่าใหม่และตรวจบัญชีก่อนทำงาน |
| MT5 initialize failed | เปิด Terminal ที่ล็อกอินถูกตัว ตรวจ `NS_MT5_PATH` และแพ็กเกจ Python ของ Windows |
| MT4 ไม่ส่งราคา/ประวัติ | ตรวจ Compile, EA บนกราฟ, WebRequest, Bridge/Publish token, All History, HistoryReady และ Experts log |
| เวลา MT4 คลาดเคลื่อน | ตรวจ UTC offset ของ Server และ DST เทียบเวลา Statement ไม่ใช้ +7 ตามเวลาไทยแทน |
| New entries blocked | อ่านเหตุผลใน Backend Risk: ยังไม่ตั้งกฎ, Pause, ประวัติเก่า, ปรับยอดรอจำแนก, Daily halt หรือ DD halt |
| SL/Volume ถูกปฏิเสธ | ใช้ Symbol จริง ตรวจ Lot min/max/step, Tick size, Stops level, ทิศทาง SL และเวลาตลาด |
| Pending/Unknown receipt | ห้ามส่งซ้ำ ตรวจ Receipt เดิมและ Positions/History ใน Terminal ก่อน ไม่ถือว่า Timeout แปลว่าโบรกเกอร์ไม่ได้รับ |
| AI Configured แต่ใช้ไม่ได้ | ตรวจเซิร์ฟเวอร์โมเดล, `/v1`, ชื่อจาก `/models`, โมเดลโหลดอยู่, Key และทรัพยากร Inference |
| Win Rate ต่างจาก Statement | เทียบช่วงเวลาปิด/สกุลเงิน/ต้นทุน, MT4 ticket vs MT5 cycle, Partial close, ขาเปิดนอกช่วงนำเข้าและต้นทุนแยกบัญชี |
| ตั้ง DD ใหม่ไม่ได้ | ต้องปิดทุกสถานะ มีข้อมูลล่าสุดและระบุเหตุผล Reset DD ไม่ล้าง Daily halt |
| Track Record เปิดไม่ได้ | ตรวจสิทธิ์ Site, Bridge/Gateway, ลิงก์ครบ, อายุและสถานะยกเลิก ไม่ใช้ Trade token อ่านรายงาน |
| Leaderboard ว่าง | ต้องยินยอม ผ่านเกณฑ์ 20 เทรด/30 วัน มีผลขาดทุนให้คำนวณ PF และ Snapshot ยังไม่เกิน 24 ชั่วโมง |
| หน้ายังเป็นรุ่นเก่า | ปิดทุกแท็บ/PWA แล้วเปิดใหม่ ตรวจ Footer ก่อนล้างข้อมูลเบราว์เซอร์ เก็บ Backup workspace ก่อน |
| เปลี่ยนเครื่องแล้วข้อมูลหาย | โปรไฟล์/Research อยู่ในเบราว์เซอร์ ส่วน Ledger อยู่ที่ Bridge ต้องเชื่อม Gateway เดิมและบัญชีเดิม |

## คำศัพท์

| คำ | ความหมายในแพลตฟอร์มนี้ |
| --- | --- |
| Terminal | โปรแกรม MT4/MT5 ของโบรกเกอร์บนเครื่องคุณ |
| Bridge/Gateway | Backend ที่เชื่อม Terminal กับเว็บ/AI/MCP |
| Deal | การจับคู่หรือรายการบัญชีหนึ่งรายการ อาจไม่ใช่เทรดทั้งรอบ |
| Position | สถานะถือครอง โดย MT5 Netting อาจรวมหลาย Deal |
| Commission/Swap/Fee | ค่าคอมมิชชัน ค่าถือข้ามคืน และค่าธรรมเนียมอื่นตามต้นทาง |
| Booked P&L | กำไรขาดทุน/ต้นทุนที่บันทึกแล้ว ไม่รวม Floating |
| Equity | มูลค่าบัญชีปัจจุบันตาม Terminal รวมผลลอยตัวตามวิธีของโบรกเกอร์ |
| Drawdown/DD | การลดลงจากยอดอ้างอิง ต้องอ่านว่ากราฟ Booked หรือ Risk Equity |
| Halt | หยุดเพิ่มความเสี่ยงตามกฎ ไม่ได้แปลว่าปิดทุกสถานะ |
| Preview | ผลตรวจคำสั่งก่อนส่งจริง มีอายุและใช้ได้ครั้งเดียว |
| Receipt | หลักฐานผลตอบกลับของคำสั่ง ใช้ตรวจคำสั่งที่ค้าง/ไม่ทราบผล |
| Inference | เรียกโมเดลที่มีอยู่ให้วิเคราะห์ ไม่ใช่การเทรนโมเดลใหม่ |
| Snapshot | รายงาน ณ เวลาหนึ่ง ไม่ใช่ผล Live ตลอดเวลา |

## ขอบเขตการตรวจสอบและแหล่งอ้างอิง

การทดสอบซอฟต์แวร์ใช้บัญชี/ราคา Fixture ที่ระบุชัดใน Tests ไม่ใช่ข้อมูล Sample ที่นำไปแสดงเป็นบัญชีจริงบนเว็บ ยังต้องตรวจด้วย MetaEditor, Terminal/บัญชีโบรกเกอร์, โมเดลที่คุณติดตั้ง และอุปกรณ์จริงของคุณ ไม่มีการรับรองว่าการเทรดหรือระบบ AI จะสร้างกำไร

- [MetaQuotes: Python integration](https://www.mql5.com/en/docs/python_metatrader5)
- [MetaQuotes: history_deals_get](https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py)
- [MetaQuotes: order_calc_profit](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py)
- [MetaQuotes: Deal properties และ INOUT](https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties)
- [MetaQuotes: MT4 OrdersHistoryTotal และช่วง Account History](https://docs.mql4.com/trading/ordershistorytotal)
- [Binance Spot API เอกสารทางการ](https://github.com/binance/binance-spot-api-docs)
- [Ollama: OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)
- [LM Studio: OpenAI-compatible endpoints](https://lmstudio.ai/docs/developer/openai-compat)

เมื่อรายงานปัญหา ให้แจ้งเวอร์ชันเว็บ/Bridge, MT4 หรือ MT5, อาการ, เวลาพร้อม Timezone และ Error ที่ลบข้อมูลลับแล้ว **ไม่แนบ Token, รหัสผ่าน, ฐานจริง หรือ Statement ที่มีข้อมูลส่วนตัวใน Issue สาธารณะ**
