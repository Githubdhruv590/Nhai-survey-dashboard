# NHAI Executive Survey Monitoring Dashboard

A production-quality web dashboard designed for the **National Highways Authority of India (NHAI)**. The system automatically lists and processes survey schedules, reports submissions, and defect precisions directly from Google Sheets worksheets, presenting interactive metrics and charts for executive monitoring.

---

## 🚀 Features

* **Dynamic Worksheet Discovery**: Reads the `Project Details` metadata and dynamically discovers all remaining regional office worksheets (`RO Delhi`, `RO Bengaluru`, etc.).
* **Monday-to-Sunday Weeks**: Auto-groups survey runs into chronological calendar weeks (e.g., `23 Jun - 29 Jun`).
* **Progressive Drilldowns**: Drill down from the **National Dashboard ➔ Zones Comparison ➔ Regional Offices (ROs) ➔ Projects List ➔ Survey Runs**.
* **Settings & Connectivity Page**: Configure spreadsheet URLs and API credentials directly in the app. Includes connection status tests.
* **Google API Retries**: Resilient connection retries (3 times) with exponential backoff on all Google Sheets API calls.
* **Responsive Visual Analytics**: Pie charts for completion status, bar charts for zone comparisons, trend graphs, delay histograms, and provider scorecard charts.
* **PDF & Data Exports**: Export views to Excel, CSV, or high-fidelity print-optimized PDF reports.

---

## ⚡ Setup & Installation

### 1. Backend Setup
1. **Navigate to the backend folder**:
   ```bash
   cd backend
   ```
2. **Create a Python Virtual Environment**:
   * **Windows**:
     ```bash
     python -m venv venv
     venv\Scripts\activate
     ```
   * **macOS/Linux**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
3. **Install Requirements**:
   ```bash
   pip install -r requirements.txt
   ```
4. **Configure environment variables** in the `.env` file (see [Configuration](#-configuration) section).

### 2. Frontend Setup
1. **Navigate to the frontend folder**:
   ```bash
   cd ../frontend
   ```
2. **Install Node dependencies**:
   ```bash
   npm install
   ```
3. **Build the static production bundle**:
   ```bash
   npm run build
   ```
   *Note: This builds the app into `frontend/dist`. The FastAPI backend is configured to automatically serve this folder on `/` if it is present.*

---

## ⚙️ Configuration

Create a file named `.env` in the `backend/` directory. Do not use quotes around values:

```env
GOOGLE_SHEET_URL=https://docs.google.com/spreadsheets/d/your-spreadsheet-id/edit
GOOGLE_CREDENTIALS_FILE=credentials.json
CACHE_EXPIRY_SECONDS=300
GOOGLE_API_KEY=
```

### Google API Credentials Setup:
1. Go to the **[Google Cloud Console](https://console.cloud.google.com/)**.
2. Create a project, enable the **Google Sheets API**, and create a **Service Account**.
3. Create and download a **JSON credentials key** for the Service Account.
4. Rename this file to `credentials.json` and place it in the `backend/` directory.
5. Share your Google Sheet (Viewer permissions) with the service account email (e.g. `service-account@project.iam.gserviceaccount.com`).

---

## 🏃 Running the Application

### Production Single-Server Mode (Vite Bundle Served by FastAPI)
Build the frontend, then start the FastAPI application:
```bash
# In the backend directory
python main.py
```
Access the application at **[http://localhost:8000](http://localhost:8000)**.

### Separate Port Development Mode
Run the servers concurrently for hot-reloading:
1. **Start Backend**:
   ```bash
   # Under backend folder
   uvicorn main:app --reload --port 8000
   ```
2. **Start Frontend Dev Server**:
   ```bash
   # Under frontend folder
   npm run dev
   ```
   Access the dashboard at **[http://localhost:5173](http://localhost:5173)**.

---

## 🛠️ Troubleshooting

If the dashboard displays a connection alert, check the settings:

1. **"Credentials file missing"**:
   - Ensure the JSON file is placed in the `backend/` directory.
   - Verify the path matching `GOOGLE_CREDENTIALS_FILE` in your settings.

2. **"Spreadsheet permission denied"**:
   - Make sure you have shared the Google Spreadsheet with the exact service account email address.

3. **"Invalid Spreadsheet URL or ID"**:
   - Check if the URL is copied correctly.
   - Ensure the spreadsheet ID is valid and the file has not been deleted.

4. **"Project Details worksheet missing"**:
   - Verify that the spreadsheet has a worksheet named exactly `Project Details` (case-insensitive) containing highway metadata.
