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

สำหรับ VPS ให้รัน gateway บน loopback ตามค่าเริ่มต้น ใช้ reverse proxy / tunnel ที่ตั้ง TLS ได้ ส่งต่อไป `127.0.0.1:8787` และส่ง Authorization header ผ่านตามเดิม ถ้า proxy ส่ง Host เป็นชื่อภายนอกให้ตั้ง `NS_ALLOWED_HOSTS` รวมชื่อโดเมนนั้น จำกัด CORS ด้วย `NS_ALLOWED_ORIGINS` เป็น origin ของเว็บจริง ค่าตั้งต้นอนุญาต NS Capital site เดิมกับ localhost:8080 เท่านั้น อย่าเปิด wildcard หรือใส่ token ใน URL

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

การเชื่อมนี้อ่านข้อมูลบัญชี ยอดเงิน และราคา ยังไม่มีการเปิด/ปิดหรือแก้ไขออเดอร์เงินจริง

## 4. เชื่อม MCP ให้ AI อ่านราคา

`mcp_server.py` เป็น MCP server แบบ **stdio** สำหรับ client ที่รองรับการรัน local process เช่นระบบ Local AI ที่มี MCP bridge ไม่ใช่ URL ที่นำไปกรอกในช่อง remote MCP ของ ChatGPT ได้ทันที

1. เปิด `bridge.py` ค้างไว้ตามขั้นตอนด้านบน
2. ปรับ `mcp-config.example.json` ให้เป็น path ของ Python และ `mcp_server.py` บนเครื่องจริง
3. ตั้ง `NS_BRIDGE_URL` และ token ให้เหมือน gateway ห้าม commit token ที่ใช้งานจริง
4. เพิ่ม server ใน MCP client แล้วเชื่อมต่อ มีเครื่องมือ:
   - `get_connection_status`: บริษัทโบรกจริง, MT4/MT5, สถานะ terminal และข้อมูลบัญชี (ID/server/currency/balance/equity)
   - `list_symbols`: ชื่อ symbol จริงรวม suffix เช่น `.pro`, `.cash`, tick size และสกุลเงินกำไร
   - `get_quote`: Bid/Ask และเวลา tick UTC milliseconds ต้องตรวจความสด
   - `get_candles`: OHLCV; TF `1,5,15,30,60,240,D,W` สูงสุด 10,000 แท่ง แท่งท้ายอาจยังไม่ปิด

ตัวอย่างคำขอ: “ตรวจว่าเชื่อมโบรกอะไร จากนั้นดึง XAUUSD M15 กับ M1 และรายงานเวลา tick ล่าสุด” ต้องเลือกชื่อที่ `list_symbols` คืนมาจริง

### MCP ผ่าน HTTP / VPS

`bridge.py` เปิด MCP แบบ Streamable HTTP ที่ `http://127.0.0.1:8787/mcp` ด้วย JSON responses (ไม่มี SSE stream และไม่มี session ฝั่งเซิร์ฟเวอร์) ใช้เครื่องมืออ่านข้อมูลสี่รายการเดียวกัน รับ `Authorization: Bearer <bridge token>` ทุกคำขอ และตรวจ Host/Origin ตาม allowlist ตั้งค่า client ตาม `mcp-http.example.json` โดยปรับรูปแบบให้ตรงกับ client นั้น

ใช้ได้กับ MCP client ที่รองรับ HTTP + custom Bearer header เมื่อเปิดผ่าน reverse proxy HTTPS จะใช้ `https://your-bridge.example/mcp` จากเครื่องอื่นได้ แต่ต้องทำ HTTPS / การเข้าถึง VPS ของคุณให้เรียบร้อยก่อน ตัวเชื่อมไม่ได้เปิด tunnel หรือเผยแพร่พอร์ตจากคอมให้อัตโนมัติ

การให้ ChatGPT บนคลาวด์เรียก gateway นี้ยังต้องตั้ง remote HTTPS พร้อมระบบยืนยันตัวตนที่ client รองรับ (เช่น OAuth เมื่อจำเป็น) และลงทะเบียนการเชื่อมต่อแยกต่างหาก ชุดนี้ยังไม่ได้เชื่อมบัญชีโบรกใน ChatGPT และไม่มี OAuth client ของ Axi ให้โดยอัตโนมัติ

## ขอบเขตข้อมูล

- อ่านข้อมูลบัญชี ยอดเงิน ราคา และแท่งเทียน ไม่มีส่งออเดอร์ ถอนเงิน หรือแก้ไขบัญชี
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
- MCP transport: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
