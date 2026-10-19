# NS Capital — Backend AI และแอปติดตั้งได้

## สถานะปัจจุบัน (1.7)

- หน้าเว็บเป็นแอป JavaScript ที่โฮสต์กับ Sites และเพิ่ม PWA manifest, launcher icons, service worker และเมนูติดตั้งแล้ว
- Broker Backend ปัจจุบันคือ Python HTTP gateway (`broker-bridge/bridge.py`) บน Windows / Windows VPS เชื่อมบัญชี MT4/MT5 จริง ไม่ใช่ FastAPI
- AI adapter ปัจจุบันเรียก Ollama, LM Studio หรือ OpenAI-compatible API ผ่าน `ai_advisor.py` เพื่อวิเคราะห์บริบทและเสนอร่างคำสั่ง มี MCP สำหรับอ่านข้อมูล/ขอข้อเสนอ
- ยังไม่มี Training pipeline, โมเดลซื้อขายที่ฝึกจากข้อมูลของคุณ, ระบบเรียนรู้อัตโนมัติจากผลเทรด, FastAPI server หรือระบบ Auto-trading ที่เปิดเองต่อเนื่อง
- การติดตั้ง PWA ไม่ได้ติดตั้ง Python, MT5, GPU runtime หรือโมเดล AI ลงมือถือ

## Ollama ที่เพิ่มในรุ่น 1.7

- ตั้ง `NS_AI_PROVIDER=ollama` และ `NS_AI_MODEL` เป็นชื่อเต็มจาก `ollama list` บนเครื่อง Bridge ค่าเริ่มต้น API คือ `http://127.0.0.1:11434/v1`
- provider อื่นมี `lm-studio` (ค่าเริ่มต้นพอร์ต 1234) และ `openai-compatible` (กำหนด NS_AI_BASE_URL เอง) การตั้ง BASE_URL/MODEL แบบเดิมยังใช้ได้
- ใน Trade → วิธีเชื่อม Ollama / LM Studio มีตัวอย่าง PowerShell และคู่มือ กดตรวจ AI เพื่อตรวจเซิร์ฟเวอร์/รายชื่อโมเดลจริง ไม่ใช่แค่ตรวจว่ากรอกค่าไว้แล้ว
- ทั้งสาม provider เสนอ draft/pass เท่านั้น ทุกการส่งคำสั่งยังต้องผ่านบัญชี สิทธิ์ สเปก และการตรวจยืนยันเดิม
- Ollama และ LM Studio เป็นทางเรียกใช้โมเดล ไม่ใช่ training pipeline ของแพลตฟอร์ม ยังไม่มีการเทรนจาก Journal หรือปรับน้ำหนักจากคำติชมโดยอัตโนมัติ
- อัปเดตชุด Broker Bridge ที่ดาวน์โหลดจากเว็บก่อนใช้ฟังก์ชันตรวจรุ่นใหม่ ยังไม่ได้รัน Ollama/โมเดลจริงบนเครื่องผู้ใช้ การทดสอบใช้เซิร์ฟเวอร์ HTTP จำลองที่ระบุชัดเจน

## สิ่งที่ควรเพิ่มสำหรับแพลตฟอร์มครบวงจร

ตารางนี้คือแผนพัฒนาต่อจากซอร์สรุ่น 1.7 ไม่ใช่ฟังก์ชันที่เปิดใช้งานแล้ว ความสำคัญเรียงตามการทำข้อมูลและการตรวจผลให้พร้อมก่อนเพิ่ม Auto-trading

| ลำดับ | ส่วนที่ควรเพิ่ม | สิ่งที่มีตอนนี้ / สิ่งที่จะได้ |
|---|---|---|
| 1 | ฐานข้อมูลกลางและสำรองข้อมูล | ตอนนี้บัญชีที่บันทึก/Journal อยู่ในเบราว์เซอร์; เพิ่ม PostgreSQL หรือเริ่ม SQLite ที่ Backend, แยก account ID/server, migrations, backup/restore และ audit log ถาวร |
| 2 | Auto Journal จากประวัติโบรกเกอร์ | ตอนนี้เป็นบันทึกข้อความพร้อม symbol/setup; เพิ่มนำเข้า deals/fills พร้อม ticket/position ID, เวลา UTC, commission, swap, fee, ยอดฝากถอน แยกบัญชีจริง/Paper/Backtest และป้องกันนำเข้าซ้ำ |
| 3 | Risk Engine ฝั่ง Backend | ตอนนี้มีตรวจบัญชี/tick/volume/SLTP/สิทธิ์; เพิ่มเพดาน risk/trade, daily loss, equity drawdown, exposure รวม, จำนวนออเดอร์ และสวิตช์หยุดรับคำสั่งเปิดใหม่ การปิด/ลดความเสี่ยงต้องยังจัดการได้ตามนโยบายที่กำหนด |
| 4 | Backtesting สำหรับ CFD/Futures จริง | ตอนนี้วิจัยบน OHLC/asset units และ fee/slippage ที่ตั้งเอง; เพิ่ม contract/tick value, account currency, bid/ask spread, commission/swap/funding ตามประเภทสินทรัพย์, margin, tick/intrabar และ expiry/rollover สำหรับ Futures |
| 5 | Walk-forward / Out-of-sample | แบ่งเทรน/ทดสอบตามเวลา, ไม่มีข้อมูลอนาคต, มี gap/purge เมื่อ labels ทับช่วงเวลา, ทดสอบต้นทุน/หลายสภาวะ, Monte Carlo ตามสมมติฐานที่เปิดเผย และเก็บ dataset/code/config version |
| 6 | AI Training และ Model Registry | กำหนดเป้าหมายทำนาย/feature/labels, jobs ที่รันแยก, บันทึก dataset/model/prompt version, ผลทดสอบและต้นทุน, มี rollback; เริ่ม Shadow/Paper แล้วค่อยกำหนดเงื่อนไขอนุญาตส่งจริง |
| 7 | Trading และการกู้คืนเมื่อระบบสะดุด | เพิ่ม durable command/receipt store, ตรวจผลค้างหลังรีสตาร์ต, heartbeat, stale-data guard ระดับระบบ, alert และ manual review; เพิ่ม pending orders/partial close/adapter ตามโบรกที่ต้องใช้ |
| 8 | Journal Analytics | เชื่อม notes กับ deals จริง แท็ก BTR/DCE, รูปก่อน–หลังเทรด, แผน/เหตุผลเข้าออก/อารมณ์/ความผิดพลาด, R-multiple, MAE/MFE, Expectancy, Profit Factor, Drawdown, วิเคราะห์แยก setup/session/account และช่วงเวลาไทย/NY |

ข้อกำหนดสำคัญของ Auto Journal: หนึ่งออเดอร์อาจมีหลาย deals และ partial fills; อย่านับหนึ่ง deal เป็นหนึ่งเทรดเสมอ ใช้ข้อมูลจริงจากโบรกและตรวจ reconciliation กับ Statement ก่อนนำไปเป็นผลการเทรน การฝากถอนต้องแยกจากกำไรเทรด คำติชม/บทเรียนใน Journal เป็นข้อมูลประกอบ ไม่เปลี่ยนกลยุทธ์ที่รันจริงทันที

การเพิ่ม risk limits หรือสวิตช์หยุดส่งคำสั่งควรตรวจที่ Backend ไม่พึ่งเพียงหน้าเว็บ ค่า risk/day/DD ต้องตั้งตามบัญชีและนโยบายผู้ใช้ ไม่เปิดใช้ค่าที่เดาให้ การอนุญาต Auto-trading ต้องมีขอบเขตบัญชี สินทรัพย์ risk และเงื่อนไขหยุดที่กำหนดชัดเจน

Binance ตอนนี้เป็นข้อมูล **Spot**; การส่งคำสั่ง Binance และข้อมูล/คำสั่ง Binance Futures ยังต้องทำ private execution/data adapters แยกต่างหาก ส่วน Futures ใน Bridge มีเฉพาะสัญญาที่บัญชี MT5 เสนอจริง ไม่ได้เชื่อมทุก Futures broker โดยอัตโนมัติ

แผนที่แนะนำ: **Data + Auto Journal → Backend Risk → CFD/Futures Backtest + Walk-forward → Model versioning + Shadow/Paper → Auto-trading ตามขอบเขตที่อนุญาต** โดยพัฒนา Dashboard จากผลจริง ไม่ใส่ตัวเลขตัวอย่างแทนข้อมูลบัญชี

## Backend ที่แนะนำสำหรับระยะเทรนโมเดล

ใช้ **Python + FastAPI เป็น API กลาง** และแยกงานฝึกโมเดลเป็น worker คนละ process / เครื่องจาก API และตัวส่งคำสั่ง

| ส่วน | เทคโนโลยี/หน้าที่ | สถานะ |
|---|---|---|
| Web app | PWA สำหรับกราฟ บัญชี ผลวิเคราะห์ และตรวจคำสั่ง | มีแล้ว |
| API กลาง | FastAPI รับชุดข้อมูล สร้างงานเทรน อ่านสถานะงาน เรียกโมเดล | แผนพัฒนาถัดไป |
| Training worker | Python + PyTorch สำหรับโมเดลที่ออกแบบเอง หรือ scikit-learn สำหรับโมเดลตารางข้อมูลระยะแรก | ยังไม่ได้สร้าง/เทรน |
| Inference | โหลดโมเดลรุ่นที่ผ่านการทดสอบมาทำนาย; Ollama / LM Studio ใช้เป็นตัวช่วยภาษาหรืออธิบายแผนได้ | มี adapter เรียกโมเดลภาษาแล้ว แต่ยังไม่มีโมเดลซื้อขายของคุณ |
| Data / model storage | เก็บ OHLCV, spread, trade log, feature version, น้ำหนักโมเดลและผลทดสอบ; เริ่มไฟล์/SQLite และค่อยขยายเป็น PostgreSQL ตามขนาดงาน | ยังไม่ทำระบบข้อมูลกลาง |
| Execution | Broker Bridge ตรวจบัญชี สเปกสัญญา ราคาสด และสิทธิ์ก่อนส่งคำสั่ง | มีแล้ว ต้องตั้งบนเครื่องผู้ใช้ |

ลำดับข้อมูลที่เสนอ: ข้อมูลตลาด/ผลเทรด → จัดชุดข้อมูล → worker เทรน → ทดสอบข้อมูลที่ไม่ใช้ฝึก → เลือก model version → inference → ตรวจความเสี่ยง/บัญชี → ผู้ใช้ยืนยัน → Broker Bridge

FastAPI เป็นตัวประสาน API ไม่ใช่ตัวเทรนเอง MCP เป็นรูปแบบเชื่อมเครื่องมือ ไม่ใช่ระบบฝึกโมเดล การคุยกับ AI หรือส่งเอกสารให้โมเดลอ่านไม่ได้หมายความว่าน้ำหนักโมเดลถูกเทรนใหม่โดยอัตโนมัติ

ควรเริ่มจากข้อมูลตลาดและ trade log ที่ระบุเวลา/symbol/สเปกบัญชีชัดเจน กำหนดสิ่งที่ต้องการทำนายและเกณฑ์ประเมินก่อนฝึก แบ่งข้อมูลตามเวลาและตรวจบนข้อมูลภายหลังโดยไม่ปะปนข้อมูลอนาคตเข้าชุดฝึก บันทึก dataset/model version เพื่อย้อนตรวจผลได้ การต่อเข้าคำสั่งจริงยังต้องผ่านการทดสอบและตั้งค่าความเสี่ยงให้ตรงกับบัญชี

## วางระบบที่ไหน

- **เครื่องส่วนตัว:** ใช้สำหรับพัฒนา เทรนขนาดที่เครื่องรองรับ และรัน Ollama / LM Studio; ตัวเชื่อม MT5 ใช้ Windows
- **Windows VPS:** รัน MT4/MT5 + Broker Bridge สำหรับการเชื่อมบัญชีที่ต้องเปิดต่อเนื่อง
- **เครื่อง CPU/GPU แยก:** ใช้ worker สำหรับงานฝึกหนัก และ model-serving ตามทรัพยากรที่ต้องใช้
- หน้า Sites/PWA แสดงผลและเรียก API ผ่าน HTTPS ไม่ใช่เครื่องฝึก GPU หรือ Python backend; ไม่เก็บ broker token/API key ลงโค้ดเว็บ
- Backend ต้องเปิดและเข้าถึงได้จึงจะรับราคา/เรียก AI/ส่งคำสั่งได้ การปิด PWA ไม่ได้สั่งให้มีงานเทรนหรือเทรดเบื้องหลังโดยอัตโนมัติ

## ติดตั้งแอป

1. เปิด URL เว็บ NS Capital ใน Chrome/Edge หรือ Safari หากเปิดในแอป ChatGPT ให้คัดลอก URL ไปเปิดในเบราว์เซอร์ก่อน
2. เลือกเมนูเพิ่มเติม → ติดตั้งแอป ถ้าเบราว์เซอร์ส่ง install prompt มา จะมีปุ่มติดตั้งในกล่องนี้
3. Android/คอมพิวเตอร์ใช้เมนูเบราว์เซอร์ → Install app / Add to Home screen ส่วน iPhone/iPad ใช้ Safari → Share → Add to Home Screen
4. เปิดจากไอคอน NS Capital; การแสดงผลและการเสนอปุ่มติดตั้งขึ้นกับเบราว์เซอร์/ระบบปฏิบัติการ
5. โหมดออฟไลน์เปิดได้เมื่อหน้าแอปถูกบันทึกครบจากการใช้งานออนไลน์ครั้งก่อน ดู Journal/ข้อมูลในเครื่องได้ แต่ราคา/AI/การซื้อขายต้องเชื่อมต่อ

PWA เก็บเฉพาะไฟล์หน้าแอป ไม่เก็บ API responses, ข้อมูลบัญชี, tokens, quotes หรือ POST orders ใน service-worker cache ไม่มีคิวคำสั่งซื้อขายและไม่ส่งซ้ำเมื่อกลับมาออนไลน์ ต้องเชื่อมต่อและตรวจคำสั่งใหม่

ระบบรอให้ปิดทุกแท็บ/หน้าต่าง NS Capital ก่อนใช้ service worker รุ่นใหม่ ไม่บังคับรีโหลดระหว่างคำสั่ง หากมี pending/unknown ให้ตรวจผลคำสั่งก่อนปิดแอป ข้อมูลและบัญชีที่เก็บในเบราว์เซอร์อาจแยกจากแอปที่ติดตั้งบนบางระบบ ให้ Backup ก่อนเปลี่ยนอุปกรณ์และเชื่อมบัญชีใหม่ตามต้องการ

ยังไม่ได้ทดสอบการติดตั้งจริงบน Chrome/Safari/โทรศัพท์ หรือการแสดงผลด้วยเบราว์เซอร์ในสภาพแวดล้อมนี้ การตรวจปัจจุบันครอบคลุมโค้ด การทำงานของเมนู install prompt/cache และเส้นทางออฟไลน์ผ่านแบบจำลอง

## เอกสารหลัก

- FastAPI และงาน Machine Learning: https://fastapi.tiangolo.com/async/
- แยก process/หน่วยความจำของ API: https://fastapi.tiangolo.com/deployment/concepts/
- PyTorch บันทึกและเรียกใช้โมเดลที่ฝึก: https://docs.pytorch.org/tutorials/beginner/basics/saveloadrun_tutorial.html
- LM Studio OpenAI-compatible API: https://lmstudio.ai/docs/developer/openai-compat
- PWA installation: https://web.dev/learn/pwa/installation
- คู่มือต่อบัญชีและ AI ปัจจุบัน: README-TH.md

- Ollama compatible API: https://docs.ollama.com/api/openai-compatibility
- Ollama structured output: https://docs.ollama.com/capabilities/structured-outputs
- แบ่งข้อมูลตามเวลา: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
- MT5 deal history สำหรับ Auto Journal: https://www.mql5.com/en/docs/python_metatrader5/mt5historydealsget_py
