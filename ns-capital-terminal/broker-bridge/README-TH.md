> **รุ่น 1.9:** เว็บหลักย้าย GitHub Pages รองรับ Google Login ที่ Backend ตรวจจริง ติดตั้ง requirements-google.txt และตั้ง NS_GOOGLE_CLIENT_ID/Allowlist ตาม USER-MANUAL-TH.md ก่อนใช้ Google Sign-in; ช่อง Bridge URL ใช้ URL หลัก ไม่ใส่ /mcp

> **รุ่น 1.8:** ใช้ไฟล์ทั้งชุดรวม database.py, journal.py, analytics.py และ risk.py ต้องตั้ง Backend Risk ก่อนเปิดใหม่ MT4 ต้องอัปเดต EA/Publish token/All History อ่านคู่มือฉบับเต็ม USER-MANUAL-TH.md ใน ZIP หรือหน้า manual.html ของเว็บก่อนเริ่ม

# NS Capital · ราคาโบรกเกอร์ + MCP

ชุดนี้ดึงราคา Bid/Ask และ OHLCV จากบัญชี **MT4 หรือ MT5 ที่ล็อกอินอยู่แล้วบน Windows / Windows VPS** มาแสดงบน NS Capital Terminal และให้ AI อ่านผ่าน MCP ได้ ตัวเชื่อมสร้างขึ้นสำหรับ NS Capital ใช้กับ Axi หรือบัญชี MetaTrader ของโบรกเกอร์อื่นได้ตามสินทรัพย์และสิทธิ์ข้อมูลของบัญชีนั้น ไม่ใช่ MCP ทางการของ Axi และยังไม่ถือว่าเชื่อมบัญชีสำเร็จจนกว่าเว็บจะแสดงชื่อโบรกจริงและได้รับ tick สด

กราฟตลาดโลกจาก TradingView เปิดดูได้โดยไม่ติดตั้งชุดนี้ แต่ราคานั้นเป็นแหล่งที่ระบุบนกราฟ (เช่น OANDA CFD) อาจต่างจาก Axi กราฟดัชนีในรายการใช้ CFD อ้างอิง ไม่ใช่ Cash index จากตลาดหลักทรัพย์ ข้อมูลบางตลาดอาจล่าช้าหรือไม่อนุญาตให้ฝัง Widget ให้ดูสถานะที่ TradingView แสดง ไม่มีการดึงข้อมูลออกจาก Widget ไปทำ Backtest

## 1. เลือก MT5 (แนะนำถ้าบัญชีมี MT5)

1. ติดตั้ง Python 3.11+ แบบ 64-bit บน Windows และ MT5 ของโบรก ล็อกอินบัญชีใน MT5 ให้เรียบร้อย เปิด Market Watch
2. แตก ZIP ไปที่ `C:\NS-Capital-Bridge` เปิด PowerShell ในโฟลเดอร์นี้
3. ติดตั้งแพ็กเกจ Python ของ MetaQuotes:

```powershell
py -m pip install MetaTrader5
```

4. เริ่มตัวเชื่อม:

```powershell
py bridge.py --mode mt5
```

ตัวเชื่อมจะสร้าง token ชั่วคราวและแสดงบนเครื่องคุณ ให้คัดลอกไปใส่ในเว็บ ห้ามใช้รหัสผ่านบัญชีเทรดเป็น token ถ้าต้องการใช้ token เดิมทุกครั้ง ให้สร้างสตริงสุ่มอย่างน้อย 32 ตัวแล้วตั้งตัวแปรก่อนเริ่ม:

```powershell
$env:NS_BRIDGE_TOKEN = "YOUR_RANDOM_PRIVATE_TOKEN_AT_LEAST_32_CHARACTERS"
py bridge.py --mode mt5
```

ถ้ามี MT5 หลายโบรก/หลายตัวติดตั้ง ให้ระบุไฟล์ terminal ที่ต้องการก่อนเริ่ม ไม่เช่นนั้น MetaQuotes อาจเลือก terminal อื่น:

```powershell
$env:NS_MT5_PATH = "C:\Program Files\Your Broker MT5\terminal64.exe"
py bridge.py --mode mt5
```

เว็บจะแสดง **ชื่อบริษัทของบัญชีที่เชื่อมจริง** ตรวจชื่อนี้ก่อนเลือกกราฟ ตัวเชื่อมไม่เปลี่ยนโบรกให้เอง ต้องเลือก terminal / path ให้ตรงกับบัญชี MetaTrader5 สำหรับ Python ใช้กับ MT5 เท่านั้น ไม่สามารถล็อกอินบัญชี MT4 ผ่านแพ็กเกจนี้ได้

## 2. ถ้าใช้บัญชี Axi MT4

1. เริ่ม `py bridge.py --mode mt4` แล้วคัดลอก token ที่แสดง
2. ใน MT4 ไปที่ File → Open Data Folder → `MQL4\Experts` วาง `NS_Market_Bridge.mq4` เปิดใน MetaEditor แล้ว Compile
3. ไปที่ Tools → Options → Expert Advisors → Allow WebRequest for listed URL เพิ่ม `http://127.0.0.1:8787`
4. นำ EA ไปติด **หนึ่งกราฟเท่านั้นต่อ gateway** ใส่ BridgeToken เดียวกับ Python และตั้ง `ServerUTCOffsetHours` ให้ตรงกับเวลาเซิร์ฟเวอร์โบรก เช่น UTC+2 ใส่ 2 หรือ UTC+3 ใส่ 3 อย่าสมมติว่าทุกโบรกใช้ +3
5. เปิด EA/AutoTrading เพื่อให้ Timer ของตัวส่งข้อมูลทำงาน EA นี้ไม่มีฟังก์ชันเปิด/ปิดหรือแก้ไขออเดอร์ และไม่ต้องเปิด DLL
6. เพิ่มสินทรัพย์ที่ต้องการใน Market Watch (หรือคลิกขวา → Show All) ค่า `MarketWatchOnly=true` จะส่งรายชื่อกลุ่มนี้ รอสถานะเชื่อมต่อ แล้วเลือกสินทรัพย์จากเว็บ EA จะรับคำขอชื่อสินทรัพย์/TF จาก gateway และส่งแท่งกับ quote กลับให้อัตโนมัติ ถ้าข้อมูลยังไม่พร้อม ให้เปิดกราฟ symbol/TF นั้นใน MT4 เพื่อโหลด history และดูแท็บ Experts

เวลา MT4 ใช้ offset ที่ตั้งไว้แปลงเป็น UTC รวมถึงข้อมูลย้อนหลังด้วย หากย้อนหลังคร่อมวันเปลี่ยน DST การใช้ offset เดียวอาจทำให้เวลาช่วงเก่าต่างหนึ่งชั่วโมง ใช้ MT5 สำหรับข้อมูล UTC โดยตรง หรือเตรียมข้อมูลประวัติที่แก้ DST แล้วก่อนวิจัยเรื่อง session

ไฟล์ MQL4 จัดเตรียมเป็นซอร์ส ยังไม่ได้ Compile หรือทดสอบกับบัญชี Axi จริงจากสภาพแวดล้อมนี้

## 3. เชื่อมเว็บกับ gateway

เปิด https://ns-capital-terminal.biw-modify004.chatgpt.site → **เชื่อมโบรก / MCP**

- ใช้กับ Axi, Pepperstone, IC Markets หรือบัญชี MT4/MT5 อื่น โดยชื่อบริษัทจะอ่านจาก terminal โดยอัตโนมัติ
- URL: `http://127.0.0.1:8787` เมื่อรัน Python และเปิดเว็บบนคอมเครื่องเดียวกัน
- Token: token ของ gateway (ไม่ใช่รหัสผ่าน Axi)
- กดทดสอบและเชื่อมต่อ รอให้ชื่อบริษัทจริงกับจำนวนสินทรัพย์ขึ้น แล้วเลือกกราฟ

Browser อาจขอสิทธิ์ Local network access หรือบล็อกเว็บ HTTPS ที่เรียก HTTP ในเครื่อง หากเชื่อมไม่ได้ ให้ใช้ HTTPS endpoint ของ gateway บน VPS หรือเปิด Terminal แบบ local จากซอร์ส `npm ci`, `npm run build`, `npm start` แล้วเข้า `http://127.0.0.1:8080` แทน

สำหรับ VPS ให้รัน gateway บน loopback ตามค่าเริ่มต้น ใช้ reverse proxy / tunnel ที่ตั้ง TLS ได้ ส่งต่อไป `127.0.0.1:8787` และส่ง Authorization และ X-Trade-Token header ผ่านตามเดิม ถ้า proxy ส่ง Host เป็นชื่อภายนอกให้ตั้ง `NS_ALLOWED_HOSTS` รวมชื่อโดเมนนั้น จำกัด CORS ด้วย `NS_ALLOWED_ORIGINS` เป็น origin ของเว็บจริง ค่าตั้งต้นอนุญาต NS Capital site เดิมกับ localhost:8080 เท่านั้น อย่าเปิด wildcard หรือใส่ token ใน URL

Token อยู่ในหน่วยความจำของเว็บสำหรับ session ที่เชื่อม ไม่บันทึกใน Backup/localStorage และต้องใส่ใหม่เมื่อรีเฟรชเว็บ MT4/MT5 ยังคงต้องเปิดและล็อกอินอยู่ ถ้ารันหลายโบรกให้รัน gateway แยก process / port / token / MT5 path และเพิ่มหลายโปรไฟล์ในเว็บแล้วสลับบัญชีที่ใช้งานได้ โดยมี gateway ที่ active ครั้งละหนึ่งบัญชี

## เพิ่มและสลับบัญชี CFD / Futures

1. อัปเดต `bridge.py` และ EA จาก ZIP รุ่นปัจจุบัน แล้วเปิด Terminal ที่ล็อกอินบัญชีจริงหรือ Demo ของคุณ
2. ในเว็บเปิด **บัญชีเทรด → เพิ่มบัญชี** ตั้งชื่อและเลือก All / CFD / Futures ใส่ Bridge URL กับ token แล้วกด **ตรวจสอบและเพิ่มบัญชี**
3. ตรวจชื่อโบรก เลขบัญชีแบบปิดบางส่วน และเซิร์ฟเวอร์ที่อ่านจาก Terminal ยอด Balance / Equity มาจากบัญชีที่เชื่อม ไม่ใช่ยอด Paper Trading; กดอัปเดตรายการเพื่อโหลด snapshot ใหม่
4. บัญชีที่สองต้องใช้ Terminal/path และ gateway แยกกัน เช่นพอร์ต 8788 พร้อม token ของบัญชีนั้น แล้วเพิ่มเป็นอีกโปรไฟล์ สลับจากปุ่มเชื่อมต่อข้างบัญชีได้ เว็บแยกข้อมูลกราฟและ watchlist ตามโปรไฟล์
5. Token อยู่เฉพาะหน่วยความจำระหว่างเปิดหน้าเว็บ รีเฟรชแล้วต้องใส่ใหม่ การตั้งค่าโปรไฟล์เก็บในเบราว์เซอร์นี้ เลขบัญชีแสดงแบบปิดบางส่วน ไม่มีการส่งรหัสผ่านโบรกเข้าเว็บ

ตัวอย่าง gateway สำหรับ Terminal MT5 อีกชุด (ต้องติดตั้ง Terminal และล็อกอินบัญชีแยกจริงก่อน):

```powershell
$env:NS_MT5_PATH = "C:\Program Files\Your Futures Broker MT5\terminal64.exe"
py bridge.py --mode mt5 --port 8788
```

**CFD / Forex:** ใช้กับ MT4/MT5 ตามบัญชีโบรก **Futures:** รองรับสัญญาที่บัญชี MT5 นั้นมีจริง โดยอ่านชนิดการคำนวณสัญญา (`trade_calc_mode`), ตลาด และวันหมดอายุจาก Terminal ตัวกรอง Futures ไม่ได้เปลี่ยน Index CFD เป็น Futures ถ้าบัญชีไม่มีสัญญา เว็บจะแสดงว่าไม่พบรายการ MT4 แสดงเป็น CFD / Forex ส่วน IBKR, Tradovate, Rithmic และแพลตฟอร์มที่ไม่มี MetaTrader ต้องพัฒนา adapter แยก

ถ้าเปลี่ยนบัญชีหรือเซิร์ฟเวอร์ใน Terminal โดยใช้ URL เดิม ระบบจะหยุดรับราคาและให้เชื่อมใหม่ เพิ่มเป็นโปรไฟล์ใหม่เพื่อยืนยันตัวตนบัญชีใหม่ คำขอ HTTP ราคาและแท่งถูกตรวจเทียบกับบัญชีที่เชื่อมอยู่

ค่าเริ่มต้นอ่านข้อมูลบัญชี ยอดเงิน และราคา ส่วนการส่งคำสั่งจริงต้องเปิดสิทธิ์เพิ่มตามขั้นตอนด้านล่าง

## ซื้อขายจากเว็บ (รุ่น 1.5)

1. ดาวน์โหลด ZIP รุ่นนี้และอัปเดตไฟล์ `bridge.py`, `trading.py`, `ai_advisor.py`, `mcp_server.py` รวมถึง EA ถ้าใช้ MT4
2. เริ่มด้วยคำสั่งต่อไปนี้ (แยก process / port / terminal ต่อบัญชี):

```powershell
py bridge.py --mode mt5 --enable-trading
# MT4 ใช้: py bridge.py --mode mt4 --enable-trading
```

3. คัดลอก **Bridge token** และ **Trade token** ที่ตัวเชื่อมสร้างแยกกันไปใส่ในหน้าบัญชีของเว็บ ไม่ใช้ token ดูราคาแทน token ส่งคำสั่ง ตั้งค่าคงที่ได้ด้วย `NS_BRIDGE_TOKEN` และ `NS_TRADE_TOKEN` ที่สุ่มคนละค่า ความยาวอย่างน้อย 32 ตัว ไม่มี token ถูกบันทึกใน GitHub / Backup / localStorage
4. MT5 ต้องเปิด Algo Trading และอนุญาตการเทรดผ่าน external Python API ใน Terminal รวมถึงสิทธิ์ของบัญชี ส่วน MT4 ต้องอัปเดตและ Compile EA ใส่ `EnableTrading=true`, `TradeToken` ให้ตรงกับตัวเชื่อม และเปิด Allow live trading
5. ในเว็บเลือกบัญชีแล้วเปิดแท็บ **ซื้อขาย** ตั้ง Buy / Sell, Lot, SL/TP และ Deviation กด **ตรวจสอบคำสั่ง** ตรวจบัญชีปลายทาง แล้วกดยืนยันจึงส่งจริง
6. สถานะเปิดเป็นข้อมูลของบัญชีที่เลือก กด SL/TP เพื่อปรับระดับ หรือ Close เพื่อปิดเต็มสถานะตาม ticket รายการ ทั้งสองอย่างต้องตรวจและยืนยัน ไม่มีการส่งข้ามทุกบัญชีหรือ Copy trade อัตโนมัติ

Preview มีอายุ 30 วินาที ตรวจบัญชี/เซิร์ฟเวอร์ ความสด tick ขนาด Lot และสเปกสัญญาก่อนส่ง คำสั่งหนึ่งรายการใช้ preview ได้ครั้งเดียว ป้องกันการกดซ้ำ หากขึ้น pending / unknown อย่ากดสร้างคำสั่งใหม่ซ้ำ ให้ตรวจ Receipt และ Positions / History ใน Terminal ก่อน ระบบไม่ส่งคำสั่งเดิมซ้ำอัตโนมัติ หลังรีสตาร์ตตัวเชื่อม preview เดิมใช้ไม่ได้และต้องตรวจ Terminal เพื่อยืนยันผลค้าง

MT5 ใช้การจับคู่แบบบัญชีจริงของโบรก บัญชี Netting อาจลดหรือกลับด้านสถานะเดิมแทนการเปิด hedge การส่ง Market ใช้ราคา ณ เวลาประมวลผล ไม่รับประกันว่าจะได้ราคาใน preview คำสั่งที่โบกรับไว้หรือจับคู่บางส่วนจะแสดงตามผลจริง ไม่ถือว่า filled ทั้งหมด

## เชื่อม Local AI / API และ MCP

### Ollama

1. ติดตั้ง Ollama จาก https://ollama.com/download และเปิดเซิร์ฟเวอร์บนเครื่องเดียวกับ Bridge
2. ดาวน์โหลดโมเดลที่ต้องการด้วย `ollama pull <ชื่อโมเดล>` แล้วใช้ชื่อเต็มที่ `ollama list` แสดง ไม่เดาชื่อหรือเลือกโมเดลให้อัตโนมัติ
3. ตั้ง PowerShell ก่อนเริ่ม Bridge ตัวอย่างเริ่มในโหมดดูข้อมูล:

```powershell
$env:NS_AI_PROVIDER = "ollama"
$env:NS_AI_BASE_URL = "http://127.0.0.1:11434/v1"
$env:NS_AI_MODEL = "YOUR_MODEL_ID_FROM_OLLAMA_LIST"
py bridge.py --mode mt5
```

ค่าเริ่มต้นของ provider `ollama` คือ `http://127.0.0.1:11434/v1` ถ้าไม่ได้ตั้ง NS_AI_BASE_URL การเรียก Local Ollama ปกติไม่ต้องมี API key ถ้าเคยตั้ง NS_AI_API_KEY ของผู้ให้บริการอื่น ให้ลบด้วย `Remove-Item Env:NS_AI_API_KEY -ErrorAction SilentlyContinue` ในหน้าต่าง PowerShell นี้ก่อนรัน เมื่อใช้ API/proxy ที่ต้องยืนยันตัวตน ให้ตั้ง key ของปลายทางนั้นบนเครื่อง Bridge เท่านั้น

หากต้องการซื้อขายด้วยตนเอง ให้ใช้ `--enable-trading` และตั้ง Trade token/สิทธิ์ Terminal ตามหัวข้อซื้อขายด้านบน การเพิ่ม provider ไม่เปิดสิทธิ์ซื้อขายให้เอง MT4 ใช้ `--mode mt4` กับ EA ที่ตั้งไว้ตามคู่มือ

### LM Studio

เปิดเซิร์ฟเวอร์ LM Studio พร้อมโมเดลที่เลือก แล้วตั้งค่าบนเครื่อง Bridge ก่อนเริ่ม Python ตัวอย่าง PowerShell:

```powershell
$env:NS_AI_PROVIDER = "lm-studio"
$env:NS_AI_BASE_URL = "http://127.0.0.1:1234/v1"
$env:NS_AI_MODEL = "YOUR_LOADED_MODEL_ID"
py bridge.py --mode mt5 --enable-trading
```

สำหรับผู้ให้บริการอื่น ตั้ง `NS_AI_PROVIDER=openai-compatible` API ที่รองรับรูปแบบ OpenAI-compatible ใช้ HTTPS base URL และตั้ง `NS_AI_API_KEY` บนเครื่อง Bridge ตามบริการนั้น เว็บไม่รับหรือเก็บ API key ของโมเดล เมื่อเลือกผู้ให้บริการบนคลาวด์ ข้อมูลราคา สัญญา ยอดเงิน และสถานะที่เกี่ยวข้องจะถูกส่งไปยังผู้ให้บริการนั้น โดยไม่ส่งเลขล็อกอิน เซิร์ฟเวอร์บัญชี หรือ token ของ gateway

### ตรวจว่าเชื่อมต่อสำเร็จหรือไม่

ในแท็บซื้อขาย กด **วิธีเชื่อม Ollama / LM Studio** เพื่ออ่านคู่มือในเว็บ และ **ตรวจ AI** เพื่อให้ Bridge เรียก `/v1/models` ตรวจการเข้าถึงเซิร์ฟเวอร์กับชื่อโมเดลที่ตั้งไว้จริง สถานะแยกเป็นยังไม่ตั้งค่า / ติดต่อเซิร์ฟเวอร์ไม่ได้ / ไม่พบโมเดล / พบโมเดล การพบชื่อโมเดลยังไม่ยืนยันว่ารัน inference สำเร็จ ปุ่มตรวจนี้ไม่สร้างข้อเสนอหรือคำสั่งซื้อขาย บริการที่ไม่รองรับ `/models` อาจตรวจรายชื่อไม่ผ่าน แม้จะมี chat endpoint; ตรวจคู่มือบริการและทดสอบ Analyze แยกต่างหาก

Bridge ใช้ OpenAI-compatible `/v1/chat/completions` แบบไม่สตรีม สำหรับ Ollama จะขอ JSON mode แล้วตรวจ schema, symbol, volume, SL/TP ซ้ำที่ Bridge หากโมเดลตอบไม่ตรงจะคืนข้อผิดพลาด ไม่แปลงเป็นคำสั่งจริง ไม่ดาวน์โหลดโมเดล ไม่เปลี่ยนโมเดล และไม่เทรนให้อัตโนมัติ Local Ollama/LM Studio ต้องรันค้างบนเครื่อง Bridge มือถือ/PWA ติดต่อ Bridge ผ่าน URL ของคุณ ไม่เรียก localhost ของคอมโดยตรง ไม่มีการเปิดพอร์ต Ollama สู่สาธารณะโดยอัตโนมัติ

หลังเชื่อมต่อแล้ว ใส่โจทย์แล้วกด Analyze AI จะอ่าน quote, สเปกสัญญา, แท่งล่าสุดไม่เกิน 120 แท่ง และสถานะของสินทรัพย์ในบัญชีที่เลือก ตอบเป็นข้อเสนอหรือไม่เทรด ถ้าต้องการใช้ข้อเสนอให้กด Review draft แล้วตรวจและยืนยันด้วยตนเอง **AI ไม่ส่งคำสั่งอัตโนมัติ**

หากโมเดลช้าหรือหมดเวลา ให้ตรวจทรัพยากร/ความยาว context และทดสอบโมเดลที่เล็กลง การทดสอบในโครงการใช้ HTTP/model fixtures ยังไม่ได้ดาวน์โหลดหรือรัน Ollama จริงบนเครื่องของคุณ

MCP ใช้ได้กับ AI client ที่รองรับ โดยเพิ่ม `get_trading_state` เพื่ออ่านบัญชีและสถานะจริง และ `suggest_trade` เพื่อขอข้อเสนอจากโมเดลที่ตั้งไว้ เครื่องมือ MCP ไม่มีคำสั่งเปิด/ปิด/แก้ไขออเดอร์จริง

## 4. เชื่อม MCP ให้ AI อ่านราคา

`mcp_server.py` เป็น MCP server แบบ **stdio** สำหรับ client ที่รองรับการรัน local process เช่นระบบ Local AI ที่มี MCP bridge ไม่ใช่ URL ที่นำไปกรอกในช่อง remote MCP ของ ChatGPT ได้ทันที

1. เปิด `bridge.py` ค้างไว้ตามขั้นตอนด้านบน
2. ปรับ `mcp-config.example.json` ให้เป็น path ของ Python และ `mcp_server.py` บนเครื่องจริง
3. ตั้ง `NS_BRIDGE_URL` และ token ให้เหมือน gateway ห้าม commit token ที่ใช้งานจริง
4. เพิ่ม server ใน MCP client แล้วเชื่อมต่อ มีเครื่องมือ:
   - `get_trading_state`: ข้อมูลบัญชี สถานะเปิด และสิทธิ์ซื้อขายของ Terminal
   - `suggest_trade`: ข้อเสนอจาก AI ที่ตั้งไว้ตาม symbol/TF/โจทย์ ไม่ส่งคำสั่ง
   - `get_connection_status`: บริษัทโบรกจริง, MT4/MT5, สถานะ terminal และข้อมูลบัญชี (ID/server/currency/balance/equity)
   - `list_symbols`: ชื่อ symbol จริงรวม suffix เช่น `.pro`, `.cash`, tick size และสกุลเงินกำไร
   - `get_quote`: Bid/Ask และเวลา tick UTC milliseconds ต้องตรวจความสด
   - `get_candles`: OHLCV; TF `1,5,15,30,60,240,D,W` สูงสุด 10,000 แท่ง แท่งท้ายอาจยังไม่ปิด

ตัวอย่างคำขอ: “ตรวจว่าเชื่อมโบรกอะไร จากนั้นดึง XAUUSD M15 กับ M1 และรายงานเวลา tick ล่าสุด” ต้องเลือกชื่อที่ `list_symbols` คืนมาจริง

### MCP ผ่าน HTTP / VPS

`bridge.py` เปิด MCP แบบ Streamable HTTP ที่ `http://127.0.0.1:8787/mcp` ด้วย JSON responses (ไม่มี SSE stream และไม่มี session ฝั่งเซิร์ฟเวอร์) ใช้เครื่องมือหกรายการเดียวกันที่ไม่ส่งคำสั่งซื้อขาย รับ `Authorization: Bearer <bridge token>` ทุกคำขอ และตรวจ Host/Origin ตาม allowlist ตั้งค่า client ตาม `mcp-http.example.json` โดยปรับรูปแบบให้ตรงกับ client นั้น

ใช้ได้กับ MCP client ที่รองรับ HTTP + custom Bearer header เมื่อเปิดผ่าน reverse proxy HTTPS จะใช้ `https://your-bridge.example/mcp` จากเครื่องอื่นได้ แต่ต้องทำ HTTPS / การเข้าถึง VPS ของคุณให้เรียบร้อยก่อน ตัวเชื่อมไม่ได้เปิด tunnel หรือเผยแพร่พอร์ตจากคอมให้อัตโนมัติ

การให้ ChatGPT บนคลาวด์เรียก gateway นี้ยังต้องตั้ง remote HTTPS พร้อมระบบยืนยันตัวตนที่ client รองรับ (เช่น OAuth เมื่อจำเป็น) และลงทะเบียนการเชื่อมต่อแยกต่างหาก ชุดนี้ยังไม่ได้เชื่อมบัญชีโบรกใน ChatGPT และไม่มี OAuth client ของ Axi ให้โดยอัตโนมัติ

## ขอบเขตข้อมูล

- ค่าเริ่มต้นอ่านข้อมูล ส่วนคำสั่งซื้อขาย Market/SLTP/Close เปิดเฉพาะเมื่อผู้ใช้ตั้งสิทธิ์และใช้ Trade token แยก ไม่มีฟังก์ชันถอนเงิน
- เว็บ polling ประมาณ 2 วินาที จึงไม่ใช่ tick-by-tick streaming หรือระบบความถี่สูง
- ป้าย BROKER · LIVE แสดงเมื่อได้รับ quote ที่มีอายุไม่เกิน 30 วินาที พร้อมแท่งที่ถูกต้องเท่านั้น ไม่มี tick ใหม่จะแสดง STALE / WAIT และไม่เติมข้อมูลสุ่ม
- รายการ symbol และชื่อ suffix มาจาก terminal จริง ไม่เดาว่า US30/USTEC หรือ GOLD ใช้ชื่อเหมือนกันทุกโบรก สิทธิ์และสินทรัพย์ขึ้นกับบัญชี/ภูมิภาค
- Backtest และ Paper ใช้ **หน่วยสินทรัพย์และสกุลเงิน quote** ตามแบบจำลองเดิม ไม่ได้จำลองสัญญา CFD, lot, leverage, swap, margin หรือ spread Bid/Ask ครบถ้วน Calculator ต้องตรวจ tick value และสกุลเงินบัญชีให้ตรงก่อนใช้
- ปิดแท่งที่ยัง forming ก่อน Backtest สำหรับ broker feed แต่การปิดแท่งช่วงหยุดตลาด/TF รายสัปดาห์ยังขึ้นกับเวลาเปิดแท่งที่โบรกให้มา
- เป็นการเชื่อมข้อมูลเพื่อใช้ส่วนตัวตามสิทธิ์บัญชี ข้อตกลงการนำข้อมูลโบรกไปเผยแพร่ต้องตรวจแยกต่างหาก

## เอกสารต้นทาง

- Axi platforms: https://help.axi.com/en-US/axiv2--axicorp-prod/article/UXVsGgzY-what-trading-platforms-can-i-use-to-trade
- Axi MT5 TH: https://www.axi.com/th/trading-platforms/metatrader-5
- Axi metals: https://help.axi.com/en-US/axiv2--axicorp-prod/article/nNC8Nal6-what-precious-metals-can-i-trade
- MetaQuotes Python: https://www.mql5.com/en/docs/python_metatrader5
- Account info: https://www.mql5.com/en/docs/python_metatrader5/mt5accountinfo_py
- Futures / CFD contract modes: https://www.mql5.com/en/docs/constants/environment_state/marketinfoconstants
- MQL4 WebRequest: https://docs.mql4.com/common/webrequest
- TradingView data FAQ: https://www.tradingview.com/widget-docs/faq/data/
- LM Studio OpenAI-compatible: https://lmstudio.ai/docs/developer/openai-compat
- MT5 order_send: https://www.mql5.com/en/docs/python_metatrader5/mt5ordersend_py
- MT4 OrderSend: https://docs.mql4.com/trading/ordersend
- MCP transport: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports


เอกสาร Ollama หลัก: https://docs.ollama.com/api/openai-compatibility และ https://docs.ollama.com/capabilities/structured-outputs


## ฐานข้อมูลกลาง + Auto Journal + Backend Risk (1.8)

อัปเดตทุกไฟล์ใน ZIP รวมถึง `database.py`, `journal.py`, `risk.py` และ EA หากใช้ MT4 เปิด [JOURNAL-RISK-TH.md](JOURNAL-RISK-TH.md) สำหรับการตั้ง NS_DB_PATH, ซิงก์ประวัติ, สูตร Daily Loss/Drawdown, สิทธิ์ Publisher token และการสำรองฐานข้อมูล

Production CLI สร้าง SQLite จริงที่เครื่อง Bridge/VPS และซิงก์ประวัติขณะ Bridge ทำงาน เว็บเปิด Journal เพื่ออ่านข้อมูลแยกบัญชีและบันทึกโน้ตที่ Backend ได้ ค่า Risk ต่อไม้/Daily Loss/Drawdown ยังต้องตั้งใน Trade → Backend Risk ของแต่ละบัญชี ถ้ายังไม่ตั้งจะไม่อนุญาตเปิดใหม่ ส่วน Close/การลดความเสี่ยงยังใช้ได้ตามสิทธิ์ Terminal

MT4 รุ่นนี้ต้องตั้ง PublishToken แยกจาก token ที่ใส่เว็บ เลือก All History แล้วเปิด HistoryReady=true ประวัติที่มีรายการ Balance คลุมเครือต้องตรวจ Statement และจำแนกก่อนใช้คำนวณความเสี่ยง
