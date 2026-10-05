# BMS Drug Machine — ตรวจข้อมูลเข้า Gateway เครื่องนับเม็ดยา

Dashboard อ่านอย่างเดียวผ่าน BMS Session (`/api/sql`) เทียบ `opitemrece` กับ `opd_presc_machine` ด้วย `hos_guid`

## เปิดใช้ (คัดลอกทั้งโฟลเดอร์ไปรันเครื่องไหนก็ได้)
1. คัดลอกโฟลเดอร์นี้ไปเครื่องที่จะเป็นเครื่องหลัก (ไม่ต้องติดตั้งอะไร มี Python ใช้ serve.py ไม่มีใช้ serve.ps1)
2. ครั้งแรกของเครื่องนั้น: คลิกขวา `Enable-LAN.bat` → Run as administrator (เปิด firewall + จองพอร์ต 8797)
3. ดับเบิลคลิก `start.bat` → หน้าต่างแสดง **MAIN URL** = IP ของเครื่องนั้น เช่น `http://10.10.44.162:8797/index.html` และเปิดเบราว์เซอร์ที่ที่อยู่นี้ให้
4. เครื่องอื่นเปิด MAIN URL นั้น แล้ววาง BMS Session ID หรือส่งมาทาง URL `...:8797/?bms-session-id=XXXX&date=2026-10-05`

- IP หลักหาให้อัตโนมัติ (การ์ดเครือข่ายที่ Windows ใช้ออกเน็ต) ถ้าเครื่องมีหลายวงแล้วเลือกผิด แก้ `set HOST_IP=` ใน start.bat เช่น `set HOST_IP=192.168.1.20`
- เปลี่ยนพอร์ต: แก้ `set PORT=` ใน start.bat แล้วรัน Enable-LAN.bat ใหม่
- เครื่องที่ไม่มี Python ถ้ายังไม่รัน Enable-LAN.bat จะเปิดได้เฉพาะ `http://localhost:8797/` บนเครื่องตัวเอง
- ห้ามเปิด index.html ตรงจากดิสก์ (file://) เพราะ tunnel ไม่รับ
- Session ID จำแยกตามที่อยู่ที่เปิด (localhost กับ IP นับเป็นคนละที่) — เปิดด้วยที่อยู่ใหม่ครั้งแรกต้องวางใหม่

## ข้อมูลที่ใช้
| ส่วน | เงื่อนไข |
|---|---|
| ต้นทาง | `opd_presc_machine WHERE modify_datetime::date = วันที่` |
| เทียบกับ | `opitemrece WHERE vstdate = วันที่ AND icode IN (ยาเข้าเครื่อง)` (ติ๊ก "เฉพาะ OPD" = `an IS NULL`) |
| ยาเข้าเครื่อง | `drugitems WHERE medication_machine_flag='Y' AND medication_machine_id IS NULL AND istatus='Y'` (ใช้เป็น subquery เพราะ ~1,400 รหัสใส่ IN ตรง ๆ แล้ว URL ยาวเกิน) |

## สถานะ
| สถานะ | เงื่อนไข |
|---|---|
| ① ไม่ได้ติ๊กส่งเครื่องนับเม็ดยา | มีใน opitemrece แต่ไม่มีใน opd_presc_machine (หมายเหตุบอกว่า qty 0 / ทั้ง VN ไม่เข้า / VN มีรายการอื่นเข้าแล้ว) |
| ② gateway ไม่ส่ง | `opd_presc_machine.dispensstatus <> 999` (ค่าที่เจอจริง: 0, 888) |
| จำนวนไม่ตรง | qty ใน opitemrece ≠ qty ในเครื่อง (ส่วนใหญ่แก้ opitemrece หลังส่ง) |
| ไม่พบใน opitemrece | มีในเครื่อง แต่ไม่มี hos_guid นี้ใน opitemrece (ถูกลบหลังส่ง) |
| ตรงกัน | hos_guid + qty ตรง และ dispensstatus = 999 |
| เข้าเครื่อง (นอกเงื่อนไข) | อยู่ในเครื่อง แต่ opitemrece คนละวัน / IPD / ยาไม่อยู่ในรายการ |

`opd_presc_machine.depcode` คือห้องจ่ายยา (B01, 246) ส่วน `opitemrece.dep_code` คือแผนกที่สั่ง จึงใช้ "VN เข้าเครื่องแล้วหรือยัง" แยกรายการตกหล่นจริงออกจาก visit ที่ไม่ได้ส่งเครื่อง

เวลารอ gateway = `gateway_flag_datetime − modify_datetime`

## แก้ปัญหา: "เครื่องหลัก ... ต่อ HOSxP ไม่ได้" / HTTP 502
หน้าเว็บเรียก HOSxP ผ่านเครื่องที่รัน start.bat — 502 แปลว่า **เครื่องนั้น** ออก hosxp.net ไม่ได้
หน้าต่าง start.bat มีบรรทัด `hosxp.net: OK` หรือ `CANNOT CONNECT - <สาเหตุ>` ตอนเปิด

| สาเหตุที่แสดง | ทางแก้ |
|---|---|
| DNS / remote name could not be resolved | เครื่องนั้นไม่มีอินเทอร์เน็ต หรือ DNS ถูกบล็อก |
| certificate | firewall ของ รพ. ตรวจ HTTPS — ติดตั้งใบรับรองของ firewall ลงเครื่อง หรือขอ IT ยกเว้น hosxp.net |
| proxy / 407 | proxy ต้อง login Windows → ตั้ง `set SERVER=powershell` ใน start.bat |
| timeout | เน็ตถูกบล็อกหรือช้ามาก — ขอ IT เปิด `*.hosxp.net` พอร์ต 443 |

ข้อมูลเกิน 500 แถว แยกดึงเป็นหน้า ๆ ละ 500 แถว (keyset) — แถบสถานะแสดง "หน้า N"
