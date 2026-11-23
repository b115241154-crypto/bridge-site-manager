from flask import Flask, render_template, request, jsonify
import os
from database import get_db_connection, init_db

app = Flask(__name__)
init_db()

@app.route("/")
def index():
    return render_template("index.html")

# ==================== 總覽指標 KPI API ====================
@app.route("/api/dashboard", methods=["GET"])
def get_dashboard():
    conn = get_db_connection()
    inv = conn.execute("""
        SELECT
            material_name,
            MAX(spec) AS spec,
            MAX(unit) AS unit,
            MAX(safety_stock) AS safety_stock,
            SUM(CASE WHEN log_type = '進貨' THEN quantity ELSE 0 END) AS total_in,
            SUM(CASE WHEN log_type = '領料' THEN quantity ELSE 0 END) AS total_out,
            SUM(CASE WHEN log_type = '進貨' THEN quantity ELSE -quantity END) AS current_stock
        FROM materials_log
        GROUP BY material_name
        ORDER BY current_stock ASC
    """).fetchall()

    purchase_sum = conn.execute("""
        SELECT COALESCE(SUM(quantity * unit_price), 0)
        FROM materials_log WHERE log_type = '進貨'
    """).fetchone()[0]

    unbilled_sum = conn.execute("""
        SELECT COALESCE(SUM(quantity * unit_price), 0)
        FROM materials_log WHERE log_type = '進貨' AND payment_status != '已請款'
    """).fetchone()[0]

    active_equip = conn.execute("""
        SELECT COUNT(*) FROM equipment_rentals WHERE status = '借出中'
    """).fetchone()[0]

    conn.close()

    inventory_list = []
    for r in inv:
        item = dict(r)
        item["is_low"] = item["current_stock"] < item["safety_stock"]
        item["ratio"] = min(100, round((item["current_stock"] / item["safety_stock"]) * 100, 1)) if item["safety_stock"] > 0 else 100
        inventory_list.append(item)

    low_count = sum(1 for x in inventory_list if x["is_low"])
    return jsonify({
        "kpi": {
            "low_count": low_count,
            "purchase_sum": purchase_sum,
            "unbilled_sum": unbilled_sum,
            "active_equip": active_equip
        },
        "inventory": inventory_list
    })

# ==================== 材料進出貨 CRUD API ====================
@app.route("/api/materials", methods=["GET"])
def get_materials():
    search = request.args.get("q", "").strip()
    conn = get_db_connection()
    query = """
        SELECT m.*, v.name AS vendor_name, v.category AS vendor_category,
               v.contact_person AS vendor_contact, v.phone AS vendor_phone,
               v.tax_id AS vendor_tax_id, v.rating AS vendor_rating
        FROM materials_log m
        LEFT JOIN vendors v ON m.vendor_id = v.id
    """
    params = []
    if search:
        query += " WHERE m.material_name LIKE ? OR v.name LIKE ? OR m.notes LIKE ?"
        like_q = f"%{search}%"
        params = [like_q, like_q, like_q]
    query += " ORDER BY m.log_date DESC, m.id DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/materials", methods=["POST"])
def add_material():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    vendor_id = data.get("vendor_id") or None
    cur.execute("""
        INSERT INTO materials_log
        (log_date, material_name, spec, unit, log_type, quantity, unit_price, vendor_id, payment_status, safety_stock, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["log_date"], data["material_name"], data.get("spec", ""), data["unit"],
        data["log_type"], float(data["quantity"]), float(data.get("unit_price") or 0),
        vendor_id, data.get("payment_status", "未請款"), float(data.get("safety_stock") or 50),
        data.get("notes", "")
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"id": new_id, "message": "新增成功"}), 201

@app.route("/api/materials/<int:item_id>", methods=["PUT"])
def update_material(item_id):
    data = request.json
    conn = get_db_connection()
    vendor_id = data.get("vendor_id") or None
    conn.execute("""
        UPDATE materials_log
        SET log_date=?, material_name=?, spec=?, unit=?, log_type=?, quantity=?,
            unit_price=?, vendor_id=?, payment_status=?, safety_stock=?, notes=?
        WHERE id=?
    """, (
        data["log_date"], data["material_name"], data.get("spec", ""), data["unit"],
        data["log_type"], float(data["quantity"]), float(data.get("unit_price") or 0),
        vendor_id, data.get("payment_status", "未請款"), float(data.get("safety_stock") or 50),
        data.get("notes", ""), item_id
    ))
    conn.commit()
    conn.close()
    return jsonify({"message": "更新成功"})

@app.route("/api/materials/<int:item_id>", methods=["DELETE"])
def delete_material(item_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM materials_log WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "已刪除"})

# ==================== 協力廠商名錄 CRUD API ====================
@app.route("/api/vendors", methods=["GET"])
def get_vendors():
    search = request.args.get("q", "").strip()
    conn = get_db_connection()
    if search:
        like_q = f"%{search}%"
        rows = conn.execute("""
            SELECT * FROM vendors
            WHERE name LIKE ? OR category LIKE ? OR contact_person LIKE ? OR tax_id LIKE ?
            ORDER BY id DESC
        """, (like_q, like_q, like_q, like_q)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM vendors ORDER BY id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/vendors", methods=["POST"])
def add_vendor():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO vendors (name, category, contact_person, phone, tax_id, rating, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["name"], data["category"], data["contact_person"],
        data["phone"], data["tax_id"], int(data.get("rating", 5)), data.get("notes", "")
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"id": new_id, "message": "廠商新增成功"}), 201

@app.route("/api/vendors/<int:vendor_id>", methods=["PUT"])
def update_vendor(vendor_id):
    data = request.json
    conn = get_db_connection()
    conn.execute("""
        UPDATE vendors
        SET name=?, category=?, contact_person=?, phone=?, tax_id=?, rating=?, notes=?
        WHERE id=?
    """, (
        data["name"], data["category"], data["contact_person"],
        data["phone"], data["tax_id"], int(data.get("rating", 5)), data.get("notes", ""), vendor_id
    ))
    conn.commit()
    conn.close()
    return jsonify({"message": "廠商更新成功"})

@app.route("/api/vendors/<int:vendor_id>", methods=["DELETE"])
def delete_vendor(vendor_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM vendors WHERE id=?", (vendor_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "廠商已刪除"})

# ==================== 零用金 CRUD API ====================
@app.route("/api/petty_cash", methods=["GET"])
def get_petty_cash():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM petty_cash ORDER BY expense_date DESC, id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/petty_cash", methods=["POST"])
def add_petty_cash():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO petty_cash (expense_date, category, item_name, amount, handler, receipt_no, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["expense_date"], data["category"], data["item_name"],
        float(data["amount"]), data["handler"], data.get("receipt_no", ""), data.get("notes", "")
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"id": new_id, "message": "新增成功"}), 201

@app.route("/api/petty_cash/<int:item_id>", methods=["DELETE"])
def delete_petty_cash(item_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM petty_cash WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "已刪除"})

# ==================== 機具租借 CRUD API ====================
@app.route("/api/equipment", methods=["GET"])
def get_equipment():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM equipment_rentals ORDER BY borrow_date DESC, id DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route("/api/equipment", methods=["POST"])
def add_equipment():
    data = request.json
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO equipment_rentals
        (equipment_name, serial_no, borrower, borrow_date, expected_return, actual_return, status, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["equipment_name"], data.get("serial_no", ""), data["borrower"],
        data["borrow_date"], data.get("expected_return", ""), data.get("actual_return", ""),
        data.get("status", "借出中"), data.get("notes", "")
    ))
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({"id": new_id, "message": "新增成功"}), 201

@app.route("/api/equipment/<int:item_id>", methods=["PUT"])
def update_equipment(item_id):
    data = request.json
    conn = get_db_connection()
    conn.execute("UPDATE equipment_rentals SET status=?, actual_return=? WHERE id=?",
                 (data["status"], data.get("actual_return", ""), item_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "更新成功"})

@app.route("/api/equipment/<int:item_id>", methods=["DELETE"])
def delete_equipment(item_id):
    conn = get_db_connection()
    conn.execute("DELETE FROM equipment_rentals WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "已刪除"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
