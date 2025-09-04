# 停車場管理系統 (Parking Lot Management System)

一個現代化的多停車場後台管理系統，支援角色權限控制、即時監控、智能計費、優惠券系統和報表功能。

## ✨ 主要功能

### 🏢 多停車場管理

- 支援多個停車場統一管理
- 獨立的費率設定 (時薪、日最高費用)
- 停車位數量管理和監控

### 👥 角色權限系統

- **超級管理員 (SuperAdmin)**: 系統最高權限，管理所有停車場和用戶
- **停車場管理員 (LotManager)**: 僅能管理指派的停車場

### 🚗 車輛進出場管理

- 即時車輛狀態追蹤
- 自動計費系統 (首 15 分鐘免費)
- 多日停車費用計算
- 手動車輛管理功能

### 💳 智能計費系統

- **免費時段**: 首次停車前 15 分鐘免費
- **時薪計算**: 超時後採用 CEILING(小時數) × 時薪
- **日上限**: 支援設定每日最高收費
- **多次繳費**: 支援分次付款機制

### 🎟️ 優惠券系統

- 12 位隨機代碼生成
- 2 小時有效期限
- 停車場綁定驗證
- 自動折抵停車費用

### 💻 雙介面設計

- **管理後台**: 響應式管理介面，支援桌面和行動裝置
- **繳費機**: 觸控螢幕最佳化介面，無滾動設計

## 🖥️ 產品演示
### kiosk(繳費機台)
<img width="900" height="637" alt="截圖 2025-09-04 上午10 58 49" src="https://github.com/user-attachments/assets/173edd9e-f8f8-46a7-b136-4e07593ceba4" />

### admin(管理員平台)
<img width="1489" height="845" alt="截圖 2025-09-04 上午10 59 13" src="https://github.com/user-attachments/assets/9187a8ee-605e-40b9-93b2-e1b368862d4f" />

## 🛠️ 技術架構

### 後端技術

- **框架**: Python Flask 2.3+
- **資料庫**: Microsoft SQL Server (Docker)
- **API**: RESTful API 設計
- **認證**: Session-based 身份驗證

### 前端技術

- **框架**: HTML5 + CSS3 + JavaScript (ES6+)
- **UI 框架**: Bootstrap 5.3
- **圖標**: Bootstrap Icons
- **模板引擎**: Jinja2

### 架構模式

- **Flask 應用程式工廠模式**: 模組化應用創建
- **三層架構**: 展示層 → 業務邏輯層 → 資料存取層
- **服務層模式**: 業務邏輯抽象化
- **整合式前後端**: Flask 同時服務 API 和靜態資源

## 📦 安裝與設置

### 系統需求

- Python 3.8+
- Docker (用於 SQL Server)
- Git

### 1. 克隆專案

```bash
git clone <repository-url>
cd parking-lot-system
```

### 2. 設置資料庫

```bash
# 啟動 SQL Server Docker 容器
docker run \
    -e "ACCEPT_EULA=Y" \
    -e "MSSQL_SA_PASSWORD=P@ssw0rd" \
    -e "TZ=Asia/Taipei" \
    -e "MSSQL_COLLATION=Chinese_Taiwan_Stroke_90_CI_AI" \
    -p 1433:1433 \
    --name sql_server \
    --platform linux/amd64 \
    -d mcr.microsoft.com/mssql/server:2022-latest

# 初始化資料庫架構
sqlcmd -S localhost -U sa -P 'P@ssw0rd' -i database/create_tables.sql

# 或者如果沒有安裝 sqlcmd，可以使用 Docker 執行
docker exec -i sql_server /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P 'P@ssw0rd' -Q "$(cat database/create_tables.sql)"
```

### 3. 後端設置

```bash
# 進入後端目錄
cd backend

# 創建虛擬環境
python -m venv venv

# 啟動虛擬環境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安裝依賴
pip install -r requirements.txt

# 配置環境變數
# 複製範例檔案並建立 .env 設定檔
cp .env.example .env

# 編輯 .env 檔案，確認以下設定：
cat .env
```

#### 📝 環境變數配置說明

請檢查並根據需要修改 `backend/.env` 檔案中的設定：

```bash
# 資料庫連接設定 (須與 Docker 設定一致)
DB_SERVER=localhost
DB_DATABASE=ParkingLot
DB_USERNAME=sa
DB_PASSWORD=P@ssw0rd    # 請改為安全的密碼
DB_PORT=1433

# Flask 應用設定
SECRET_KEY=dev-key-change-in-production    # 生產環境請更改為隨機密鑰
FLASK_ENV=development    # 生產環境改為 'production'
```

#### 🔒 安全提醒

**開發環境**：
- 可以使用預設的 `P@ssw0rd` 密碼
- `SECRET_KEY` 使用預設值即可

**生產環境**：
- 務必更改 `DB_PASSWORD` 為強密碼
- 生成安全的 `SECRET_KEY`：
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```
- 將 `FLASK_ENV` 改為 `production`

### 4. 啟動應用程式

```bash
# 在 backend 目錄下執行
python run.py

# 服務將在 http://localhost:5000 啟動
```

### 5. 存取應用程式

- **管理後台**: http://localhost:5000/admin/
- **繳費機介面**: http://localhost:5000/kiosk/
- **API 端點**: http://localhost:5000/api/
- **健康檢查**: http://localhost:5000/health

## 🚀 快速開始

### 預設管理員帳號

```
用戶名: superadmin
密碼: admin123
```

### 開發模式啟動

```bash
# 單行命令快速啟動
cd backend && source venv/bin/activate && python run.py

# 驗證服務狀態
curl http://localhost:5000/health
```

## 📊 資料庫架構

### 主要資料表

- `PARKING_LOT`: 停車場基本資訊
- `ADMINS`: 管理員帳戶資訊
- `ADMIN_LOT_ASSIGNMENTS`: 管理員權限分配
- `PARKING_RECORD`: 車輛停車紀錄
- `PAYMENT_RECORD`: 付款交易紀錄
- `DISCOUNT`: 優惠券系統

### 關鍵業務邏輯

- **計費邏輯**: 首次 15 分鐘免費 → 時薪制 → 日上限制
- **多次付款**: 從 `PaidUntilTime` 開始計算後續費用
- **優惠券**: 綁定停車場，每張折抵 1 小時

## 🔧 開發說明

### 專案結構

```
parking-lot-system/
├── backend/                 # Flask 後端應用
│   ├── app/
│   │   ├── api/            # API 路由
│   │   ├── services/       # 業務邏輯
│   │   ├── utils/          # 工具模組
│   │   ├── static/         # 前端資源
│   │   └── templates/      # HTML 模板
│   ├── run.py              # 應用入口點
│   ├── config.py           # 配置檔案
│   └── requirements.txt    # 依賴列表
├── database/               # 資料庫架構
└── context/               # 專案文件
```

### 調試端點

- `/health` - 資料庫連接測試
- `/debug/admins` - 檢查管理員記錄
- `/debug/fix-passwords` - 重置管理員密碼
- `/debug/add-test-vehicle` - 新增測試車輛

### 重要開發注意事項

- 使用 `pymssql` 驅動程式連接 Docker SQL Server
- 前端使用相對路徑載入靜態資源
- API 呼叫使用 `window.location.origin` 動態處理端口
- 觸控介面按鈕最小 64px 高度

## 🧪 測試

### 功能測試項目

- **計費邏輯**: 測試多日停車情境 (69+ 小時)
- **身份認證**: 驗證角色權限控制
- **繳費機 UI**: 確保觸控螢幕無滾動操作
- **API 整合**: 測試所有 CRUD 操作

## 📋 核心依賴

```
Flask>=2.3.0              # Web 框架
Flask-RESTful>=0.3.9      # REST API 支援
Flask-CORS>=4.0.0         # 跨域請求
python-dotenv>=1.0.0      # 環境變數管理
pymssql>=2.2.0           # SQL Server 驅動程式
werkzeug>=2.3.0          # WSGI 工具
```

## 🔒 安全考量

- Session-based 身份認證
- 角色權限驗證
- SQL 注入防護 (參數化查詢)
- 跨域請求控制
- 密碼雜湊處理

## 🤝 貢獻

歡迎提交 Issue 和 Pull Request 來改善此專案。

## 📄 授權

此專案採用 MIT 授權條款。

---

**開發成員**: 鄭子翰
**最後更新**: 2024 年 8 月  
**專案狀態**: 開發完成，核心功能穩定運行
