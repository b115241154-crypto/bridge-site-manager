# 公共工程工務所｜材料進出貨與行政管理系統

## 系統特色
- 專案背景：高屏溪橋梁改建工程 (標案 KH-BR-2026-08)
- 介面設計：左側深色工業風固定導覽列 + 頂部 4 項 KPI 統計儀表板 + 存量進度條水位監控
- 資料庫：SQLite (`bridge_project.db`)，包含 `vendors`、`materials_log`、`petty_cash`、`equipment_rentals` 四張關聯資料表

## 本機執行方式
```bash
pip install -r requirements.txt
python app.py
```
啟動後開啟瀏覽器前往 `http://127.0.0.1:5000`。
