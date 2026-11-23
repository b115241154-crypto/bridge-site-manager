import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bridge_project.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. 協力廠商資料庫 (vendors)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            contact_person TEXT NOT NULL,
            phone TEXT NOT NULL,
            tax_id TEXT NOT NULL,
            rating INTEGER DEFAULT 5,
            notes TEXT
        );
    """)

    # 2. 材料進出貨與庫存異動表 (materials_log) - 關聯 vendors.id
    cur.execute("""
        CREATE TABLE IF NOT EXISTS materials_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT NOT NULL,
            material_name TEXT NOT NULL,
            spec TEXT,
            unit TEXT NOT NULL,
            log_type TEXT NOT NULL CHECK(log_type IN ('進貨', '領料')),
            quantity REAL NOT NULL,
            unit_price REAL DEFAULT 0,
            vendor_id INTEGER,
            payment_status TEXT DEFAULT '未請款' CHECK(payment_status IN ('已請款', '對帳中', '未請款', '不適用')),
            safety_stock REAL DEFAULT 50,
            notes TEXT,
            FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE SET NULL
        );
    """)

    # 3. 工務所日常零用金表 (petty_cash)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS petty_cash (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_date TEXT NOT NULL,
            category TEXT NOT NULL,
            item_name TEXT NOT NULL,
            amount REAL NOT NULL,
            handler TEXT NOT NULL,
            receipt_no TEXT,
            notes TEXT
        );
    """)

    # 4. 工程機具借還登記表 (equipment_rentals)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS equipment_rentals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_name TEXT NOT NULL,
            serial_no TEXT,
            borrower TEXT NOT NULL,
            borrow_date TEXT NOT NULL,
            expected_return TEXT,
            actual_return TEXT,
            status TEXT NOT NULL DEFAULT '借出中' CHECK(status IN ('借出中', '已歸還', '維修中')),
            notes TEXT
        );
    """)

    cur.execute("SELECT COUNT(*) FROM vendors")
    if cur.fetchone()[0] == 0:
        seed_vendors = [
            ("國產建材實業仁武廠", "預拌/混凝土", "黃明輝", "07-371-8890", "24060203", 5, "高強度橋梁混凝土主力供應商"),
            ("中鋼結構工程股份有限公司", "鋼構/鋼筋", "蔡政翰", "07-802-3433", "75966829", 5, "箱型梁鋼構與預力鋼材認證齊全"),
            ("豐興鋼鐵南區配銷中心", "鋼構/鋼筋", "許家豪", "07-622-5108", "55391024", 4, "竹節鋼筋進料準時，需提前兩日叫料"),
            ("宏華級配砂石企業社", "砂石/級配", "劉文龍", "07-661-9420", "89312045", 4, "路基級配粒料與河砂供應"),
            ("順發機電與防水材料行", "防水/機電", "周志偉", "07-746-1129", "42819037", 5, "橋面防水塗層與臨時照明耗材")
        ]
        cur.executemany("""
            INSERT INTO vendors (name, category, contact_person, phone, tax_id, rating, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, seed_vendors)

        seed_materials = [
            ("2026-11-17", "高強度無收縮水泥", "50kg/袋 (6000psi)", "袋", "進貨", 180, 260, 1, "已請款", 70, "P3橋墩帽梁支承墊灌漿"),
            ("2026-11-18", "高強度無收縮水泥", "50kg/袋 (6000psi)", "袋", "領料", 135, 0, None, "不適用", 70, "P3橋墩施工領用"),
            ("2026-11-18", "預力鋼絞線", "15.2mm 7線式", "噸", "進貨", 30, 32500, 2, "對帳中", 12, "第一跨箱型梁預力施拉"),
            ("2026-11-19", "預力鋼絞線", "15.2mm 7線式", "噸", "領料", 22, 0, None, "不適用", 12, "預力套管穿線作業"),
            ("2026-11-20", "路基級配粒料", "M-30碎石級配", "立方米", "進貨", 120, 880, 4, "未請款", 40, "引道填築壓實備料"),
            ("2026-11-21", "路基級配粒料", "M-30碎石級配", "立方米", "領料", 45, 0, None, "不適用", 40, "北側引道第一層鋪築"),
            ("2026-11-21", "橋面聚氨酯防水塗料", "20kg/桶", "桶", "進貨", 40, 2450, 5, "未請款", 18, "橋面板防水層施工"),
            ("2026-11-22", "橋面聚氨酯防水塗料", "20kg/桶", "桶", "領料", 28, 0, None, "不適用", 18, "跨河段橋面底塗作業")
        ]
        cur.executemany("""
            INSERT INTO materials_log
            (log_date, material_name, spec, unit, log_type, quantity, unit_price, vendor_id, payment_status, safety_stock, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, seed_materials)

        seed_petty = [
            ("2026-11-19", "餐費/加班", "夜間連續灌漿宵夜便當 (18份)", 2160, "林工務", "REC-111901", "P3帽梁連續澆置"),
            ("2026-11-20", "測量耗材", "棱鏡反光貼片、噴漆、木樁", 950, "吳測量", "REC-112003", "橋墩中心線放樣"),
            ("2026-11-21", "職安防護", "反光背心 5 件與安全帽下巴帶", 1250, "陳安衛", "REC-112102", "新進工班職安補給"),
            ("2026-11-22", "事務耗材", "防水施工日誌本與影印紙", 680, "張行政", "REC-112205", "工務所文書採購")
        ]
        cur.executemany("""
            INSERT INTO petty_cash (expense_date, category, item_name, amount, handler, receipt_no, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, seed_petty)

        seed_equip = [
            ("振動式平板夯實機", "BR-COMP-04", "劉班長 (路基班)", "2026-11-20", "2026-11-25", "", "借出中", "北側引道級配夯實"),
            ("高頻混凝土振動棒", "BR-VIB-09", "黃師傅 (模板灌漿班)", "2026-11-21", "2026-11-24", "", "借出中", "胸牆混凝土搗實"),
            ("靜音型柴油發電機 6kW", "BR-GEN-02", "周志偉 (機電班)", "2026-11-18", "2026-11-20", "2026-11-20", "已歸還", "已完成機油檢查入庫"),
            ("全站儀雙稜鏡組", "BR-SURV-01", "測量組", "2026-11-22", "2026-11-23", "", "借出中", "橋面高程水準測量")
        ]
        cur.executemany("""
            INSERT INTO equipment_rentals
            (equipment_name, serial_no, borrower, borrow_date, expected_return, actual_return, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, seed_equip)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"工務所資料庫初始化完成：{DB_PATH}")
