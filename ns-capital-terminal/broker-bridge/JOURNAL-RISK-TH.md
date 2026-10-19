# NS Capital — ฐานข้อมูลกลาง, Auto Journal และ Backend Risk (1.8)

## ระบบรันที่ไหน

เว็บ/PWA เป็นหน้าจอ ส่วนฐานข้อมูลและ Risk Engine รันใน Python Broker Bridge บน Windows PC / Windows VPS ที่เปิด MT4/MT5 อยู่ ไม่ใช่ฐานข้อมูลใน localStorage และไม่ใช่ Python ที่รันบน Sites

Bridge สร้าง SQLite จริงบนดิสก์ เก็บบัญชี, deals, notes, สถานะ sync, กฎความเสี่ยง, equity reference, receipts และ audit log ไม่เก็บ broker password, market-data token, Trade token, Publisher token หรือ API key ของโมเดลในฐานข้อมูล

ค่าเริ่มต้นบน Windows คือ `%LOCALAPPDATA%\NSCapital\trading.sqlite3` ถ้าต้องการให้หลาย Bridge ใช้ฐานข้อมูลกลางเดียวกัน ให้ตั้ง `NS_DB_PATH` เป็นไฟล์เดียวกันบน **Windows/VPS เครื่องเดียวกัน** แต่ละบัญชีใช้คนละ process/terminal/port/token มี namespace แยกตาม MT4/MT5 + server + login

```powershell
$env:NS_DB_PATH = "$env:LOCALAPPDATA\NSCapital\trading.sqlite3"
$env:NS_HISTORY_DAYS = "90"
$env:NS_HISTORY_SYNC_SECONDS = "30"
py bridge.py --mode mt5 --enable-trading
```

ใช้ Python 3.11+ และ MetaTrader5 package บน Windows ตามคู่มือหลัก SQLite เป็นส่วนหนึ่งของ Python อยู่แล้ว ฐานข้อมูลสร้างเมื่อเริ่ม Bridge; ไม่มีประวัติเทรดของคุณในระบบนี้จนกว่าจะเชื่อม Terminal และซิงก์จริง

หลายบัญชีบน VPS เดียว: คง NS_DB_PATH เดียวกัน เปิดแต่ละ terminal ด้วย NS_MT5_PATH ของบัญชีนั้น และใช้ --port ต่างกัน เช่น 8787/8788 ตั้ง URL HTTPS/Host/Origin และ token แยกตามคู่มือบัญชี API ของแต่ละ Bridge อ่านได้เฉพาะบัญชี Terminal ปัจจุบัน ไม่คืนข้อมูลของบัญชีอื่นแม้อยู่ในไฟล์เดียวกัน

อย่าวาง SQLite บน SMB/NFS/โฟลเดอร์ซิงก์ Cloud แล้วให้หลายเครื่องเขียนไฟล์พร้อมกัน มือถือและแท็บเล็ตอ่านผ่าน HTTPS Bridge ตามเดิม หากแยกหลาย VPS หรือขยายเป็นผู้ใช้จำนวนมาก ต้องเพิ่มบริการฐานข้อมูลกลาง เช่น PostgreSQL และระบบสิทธิ์แยกต่างหาก รุ่นนี้ยังไม่ติดตั้งบริการนั้น

## Auto Journal — MT5

- อ่าน `history_deals_get` จาก Terminal ที่ล็อกอินจริง ใช้ UTC และแบ่งช่วงอ่านครั้งละไม่เกิน 7 วัน
- ครั้งแรกนำเข้าตาม NS_HISTORY_DAYS (ค่าเริ่มต้น 90 วัน) จากนั้นตรวจซ้ำโดยซ้อนช่วงล่าสุด 2 วัน พร้อมกลับมาตรวจช่วงเต็มอย่างน้อยวันละครั้งขณะ Backend ทำงาน
- บันทึก ticket/position/order ID และช่อง profit, commission, swap, fee ตามโบรก รวม Net = profit + commission + swap + fee โดยเก็บเครื่องหมายเดิม
- คีย์บัญชี + ticket ป้องกันซ้ำ การซิงก์ซ้ำแก้ไขข้อมูล ticket เดิม ไม่เพิ่มกำไรซ้ำ และการซิงก์ที่ล้มเหลวไม่ลบประวัติเดิม
- แยกเงินฝากถอน/เครดิตออกจากกำไรเทรด รายการ correction, canceled deals หรือรายการที่แยกไม่ได้จะขึ้นให้ตรวจ Statement และจำแนกพร้อมเหตุผล/Trade token มี audit log การจำแนกคงอยู่เมื่อ sync ซ้ำ รายการที่ยังคลุมเครือแสดงยอดรอจำแนกแยกต่างหากและยังไม่รวมใน Net P&L ที่จำแนกแล้ว
- ตัวเลขเป็นสกุลเงินบัญชี ไม่มีการรวมข้ามสกุลเงินหรือแปลงเป็น USD ให้โดยเดา

ในเว็บเปิด **Journal → Auto Journal** เลือกบัญชีและช่วง 7/30/90/365 วัน กดซิงก์เพื่อขอนำเข้าช่วงที่เลือก ดูเวลา/ช่วงข้อมูลที่ซิงก์สำเร็จ ส่งออก CSV และบันทึก BTR/DCE/บทเรียนผูกกับ Position ID ได้ ข้อมูลจากโบรกเป็น Deals/รายการ ไม่ใช่สถิติจำนวน round-trip trades; partial fills และ entry/exit อาจมีหลายรายการต่อ Position

โน้ตในเบราว์เซอร์เดิมไม่มี account ID จึงแยกไว้ในหัวข้อโน้ตเดิม ไม่ย้ายเข้าบัญชีใดโดยอัตโนมัติ ส่วนโน้ตใหม่ใน Auto Journal เก็บที่ Backend เมื่อเปลี่ยนอุปกรณ์ให้เชื่อม Bridge เดิมเพื่ออ่านได้ การซิงก์อัตโนมัติทำต่อได้เมื่อปิดเว็บ ตราบใดที่ Bridge/Terminal ยังเปิด

## Auto Journal — MT4

1. อัปเดต EA `NS_Market_Bridge.mq4` รุ่นนี้และคอมไพล์ใน MetaEditor
2. ใน Account History เลือก **All History** แล้วตรวจว่า Terminal โหลดรายการที่ต้องการครบ
3. ตั้ง `HistoryReady=true`, `HistoryDays=90` (หรือช่วงที่ต้องการ) และ ServerUTCOffsetHours ให้ตรงกับโบรกจริง
4. ตั้ง **PublishToken** แยกจาก BridgeToken/TradeToken ใน EA ใช้ค่าจาก `NS_PUBLISH_TOKEN` หรือค่าที่ Bridge แสดงตอนเริ่ม MT4 ห้ามกรอก PublishToken ในเว็บ
5. EA ส่งประวัติเป็น batch เมื่อรับครบจึง commit เข้า DB การส่งซ้ำหลัง ACK หายไม่เพิ่มซ้ำ ระหว่างรอประวัติครบ Backend จะหยุดเปิดใหม่ แต่ยังให้ปิด/ลดความเสี่ยงเมื่อ snapshot Terminal สด

MT4 ไม่มี API เหมือน MT5 ฝั่ง Python จึงใช้ประวัติที่ Terminal โหลดอยู่ `OrdersHistoryTotal` ขึ้นกับการเลือก Account History การตั้ง HistoryReady คือการยืนยันว่าผู้ใช้ตรวจการโหลดประวัติแล้ว ระบบไม่สามารถรับรองว่าโบรกส่งประวัติตลอดอายุบัญชีมาให้ครบจากค่า count เพียงอย่างเดียว

รายการ OP_BALANCE ใน MT4 อาจเป็นเงินฝากถอนหรือค่าบริการ จึงต้องตรวจ Statement แล้วเลือก **Cash flow** หรือ **Trading cost** ใน Journal ก่อนใช้รายการที่คลุมเครือคำนวณความเสี่ยง การคิด commission/swap ที่อยู่บน Order ใช้ค่าจริงโดยไม่ต้องกรอกใหม่

เวลาประวัติ MT4 แปลงด้วย UTC offset ที่ตั้งใน EA ซึ่งเป็นค่าเดียว ถ้าช่วงประวัติข้ามการเปลี่ยน DST ของเซิร์ฟเวอร์ ให้ตรวจเวลาใน Statement ก่อนใช้วิเคราะห์ตามวัน/Session หรือปรับช่วงนำเข้าที่ offset ตรงกัน รุ่นนี้ยังไม่มีฐานข้อมูล timezone ย้อนหลังของแต่ละโบรก

Publisher token ป้องกัน token ที่ใช้เปิดเว็บจากการเขียนทับราคา/บัญชี/ประวัติที่เป็นข้อมูลเข้า Risk Engine การเปลี่ยนกฎและจำแนกรายการต้องใช้ Trade token อีกชั้น ไม่มี publisher token ใน browser หรือ model payload

## ตั้ง Backend Risk แยกบัญชี

เข้า **Trade → Backend Risk → ตั้งค่าบัญชีนี้** ต้องเชื่อมบัญชีจริงและมี Trade token เพื่อบันทึกกฎ กฎเป็นของบัญชี/เซิร์ฟเวอร์นี้และอยู่ใน SQLite ไม่ใช่ค่าคำนวณในหน้า Risk calculator เดิม

| ค่า | วิธีใช้ |
|---|---|
| Risk / trade | เปอร์เซ็นต์ของ equity ปัจจุบันที่อนุญาตสำหรับความเสี่ยงถึง SL ของรายการเปิดใหม่/การเพิ่มความเสี่ยง SL |
| Daily Loss | เปอร์เซ็นต์ของยอด balance ตอนต้นวันตามเวลาที่ตั้ง ตรวจทั้งผลปิดจริงรวมต้นทุนและ floating ปัจจุบัน |
| Drawdown | เปอร์เซ็นต์จาก trailing equity peak ที่ Backend สังเกตหลังตั้งจุดอ้างอิง ปรับเงินฝากถอน/เครดิต |
| เวลารีเซ็ต | ชั่วโมงและนาที UTC เช่น 17:00 UTC = 00:00 ไทย เลือกให้ตรงนโยบายบัญชีของคุณ ไม่อ้างว่าเป็นกฎ prop firm ใดโดยอัตโนมัติ |
| เผื่อต้นทุน / Lot | เงินในสกุลบัญชีสำหรับต้นทุนไป–กลับที่ต้องการเผื่อใน risk estimate ค่า 0 หมายถึงไม่เผื่อตรงส่วนนี้ |
| Slippage เพิ่ม | จำนวน points เพิ่มสำหรับราคาเข้า/stop ในการประมาณความเสี่ยง นอกเหนือจาก Deviation ที่ตรวจราคาเข้า |
| หยุดเปิดใหม่ | สวิตช์พักรายการเปิดใหม่และการเพิ่มความเสี่ยง โดยไม่สั่งปิดสถานะอัตโนมัติ |

ไม่มีตัวเลขเพดานถูกเปิดใช้แทนคุณ ถ้ายังไม่ตั้งกฎ ประวัติไม่พร้อม มีรายการคลุมเครือ หรือขาดข้อมูลคำนวณความเสี่ยง **คำสั่งเปิดใหม่จะถูกปฏิเสธที่ Backend**

- เปิดใหม่ต้องมี SL; MT5 ใช้ `order_calc_profit` คำนวณการขาดทุนถึง SL ในสกุลเงินบัญชี รวมต้นทุน/slippage reserve ที่ตั้งไว้ MT4 ใช้ tick size/value จริงจาก EA ถ้าไม่มี tick value จะไม่เปิดใหม่
- คำสั่งเพิ่มตำแหน่งฝั่งเดียวกันใน MT5 netting ตรวจความเสี่ยงรวมของตำแหน่งหลังเพิ่ม การส่งฝั่งตรงข้ามเข้า netting position เดิมให้ใช้ Close/SLTP จัดการก่อน
- ตรวจทั้งตอน Preview และ Execute ถ้ากฎเปลี่ยนหลัง Preview ต้องตรวจรายการใหม่ MT4 ตรวจอีกครั้งก่อนส่งคำสั่งออกไปให้ EA
- Daily P&L = ผล trading net ที่บันทึกวันนี้ + (equity − balance − credit) โดยแยก cash flows ออก Day-start balance ย้อนจาก balance ปัจจุบันและรายการที่กระทบ balance วันนี้
- เมื่อ Daily Loss ถึงเพดานจะ latch หยุดเปิดใหม่จนถึงวันใหม่ตามเวลาที่ตั้ง แม้ equity ฟื้นกลับในวันเดิม การบันทึกกฎไม่ล้าง latch ของวันนั้น
- Drawdown latch คงอยู่หลังรีสตาร์ต ต้องตรวจ Statement แล้วตั้ง DD reference ใหม่พร้อมเหตุผล ขณะไม่มีสถานะเปิด การ reset DD ไม่ล้าง Daily halt
- ยังคงให้ Close หรือปรับ SL ในทิศลดความเสี่ยง การถอน SL/ขยาย SL ถือว่าเพิ่มความเสี่ยงและต้องผ่านกฎ ไม่มีการบังคับปิดสถานะเดิมเมื่อแตะเพดาน

เพดานนี้ตรวจคำสั่งที่ผ่าน Bridge เท่านั้น ไม่ได้ห้ามคำสั่งจากมือถือโบรก, MT5/MT4 อื่นหรือ EA อื่น และไม่ได้รับประกันว่าขาดทุนจริงจะหยุดตรงตัวเลขเมื่อเกิด Gap, slippage หรือหลายสถานะขาดทุนพร้อมกัน รุ่นนี้ไม่ใช่ portfolio exposure reservation engine; ค่าความเสี่ยงต่อไม้กับเงื่อนไขหยุดเปิดใหม่อ้างอิง snapshot ที่ตรวจแต่ละครั้ง

Equity peak ไม่สามารถย้อนเห็น peak ที่เกิดและหายไปขณะ Backend ปิดอยู่ ข้อมูลประวัติมีขอบเขตตามช่วงที่อ่านได้และข้อมูลที่ Terminal ส่งมา ตรวจยอดกับ Statement ก่อนเปิดใช้งานเงินจริง

## ความคงทนและสำรองข้อมูล

Receipts และ request IDs เก็บใน SQLite เมื่อรีสตาร์ตจะไม่ส่งคำสั่งเดิมซ้ำ ถ้ากระบวนการหยุดระหว่างส่งแต่ยังไม่มี receipt ให้ถือว่า pending/unknown และตรวจ Positions/History ใน Terminal ไม่เดาว่าสำเร็จหรือสร้างคำสั่งซ้ำอัตโนมัติ

สำรองด้วย SQLite backup API ผ่านคำสั่งนี้ (ปลายทางต้องยังไม่มีไฟล์):

```powershell
py database.py "$env:LOCALAPPDATA\NSCapital\trading.sqlite3" "D:\NS-Backups\trading-backup.sqlite3"
```

ใช้ชื่อปลายทางใหม่ในแต่ละครั้ง หากต้องนำข้อมูลกลับ ให้หยุดทุก Bridge ที่ใช้ DB นั้นและสำรองไฟล์ปัจจุบันก่อน การแชร์ไฟล์ฐานข้อมูล/สำรองเป็นการแชร์ประวัติบัญชีของคุณ ห้าม commit DB หรือ backup ลง Git ชุด build ไม่รวมไฟล์ DB/tokens

SQLite ใช้ transaction และ synchronous FULL สำหรับ durable writes บน local disk ไม่มี PostgreSQL server, multi-VPS replication หรือระบบสมาชิกหลายคนที่ติดตั้งแล้วในรุ่นนี้

## ขอบเขตการทดสอบ

ตรวจด้วย SQLite จริงบนไฟล์ทดสอบ, เซิร์ฟเวอร์ HTTP ในเครื่อง และ Terminal/Deal fixtures ที่ระบุชัดเจน ครอบคลุมยอดสุทธิ, sync ซ้ำ/แก้ไข, หลายบัญชี, reload/backup, token roles, per-trade risk, daily reset/latch, DD latch, pause/close/SL, policy เปลี่ยนหลัง preview, MT4 batches/delivery และ UI races ยังไม่ได้ใช้บัญชีโบรกจริง คอมไพล์ EA ใน MetaEditor หรือทดสอบ browser/device จริงในสภาพแวดล้อมนี้

เอกสารหลัก:
- MT5 deals: https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py
- Account-currency profit: https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py
- Deal types/costs: https://www.mql5.com/en/docs/constants/tradingconstants/dealproperties
- MT4 loaded history: https://docs.mql4.com/trading/ordershistorytotal
- SQLite: https://docs.python.org/3/library/sqlite3.html


## Dashboard, Coaching และ Track Record

รุ่น 1.8 เพิ่มสถิติ MT5 แบบ flat-to-flat รวม Partial close และ Reverse พร้อมต้นทุน; MT4 นับ Closed tickets แยกชัด ค่าบริการรวมบัญชีที่ผูกต่อไม้ไม่ได้แสดงแยก ไม่เดา Win Rate/PF

ตั้งเกณฑ์สังเกตพฤติกรรมแยกบัญชีได้ ผลเป็นหลักฐานตามเงื่อนไข ไม่ใช่การวินิจฉัยอารมณ์ และไม่บล็อกคำสั่ง AI Coaching ใช้สถิติ Backend ไม่ส่งเลขบัญชี/Token/โน้ต และไม่มีสิทธิ์ Execute

Track Record สร้างเมื่อผู้ใช้ยินยอม เป็น Snapshot รวมที่ไม่มีข้อมูลระบุตัวบัญชี Token เก็บเฉพาะ Hash ยกเลิก/หมดอายุได้ หน้ารายงานบน GitHub Pages เป็น Public แต่ต้องมี Report capability ที่ยังใช้ได้ และไม่ใช่ Broker-verified record Leaderboard อยู่ภายใน Bridge เดียว ใช้ PF 30 วัน มีอย่างน้อย 20 เทรดปิดและผลขาดทุน Snapshot ที่ผู้ใช้กดอัปเดตหมดอายุ 24 ชั่วโมง

รายละเอียดครบและขั้นตอนอยู่ใน USER-MANUAL-TH.md ที่มากับ ZIP และ manual.html บนเว็บ
