# 🛡️ SecureShield Pro | Enterprise Cloud File Manager & Security Hub

> **Web-Based File Operations • In-Browser Editor & Previews • Deep Content Inspection • Trojan Anti-Spoofing • SHA-256 Integrity Guardian**

SecureShield Pro is a full-featured, web-based file manager and security suite built with **Streamlit**, **Pandas**, and **Altair**. It empowers users to upload, manage, edit, preview, organize, extract, and compress files through a modern, responsive browser interface—backed by deep binary magic-byte inspection and cryptographic integrity monitoring.

---

## 🌟 Web File Operations Suite

SecureShield Pro was engineered so users never feel a lack of core file operations after uploading:

### 1. 📁 Explorer & Ingestion
- **Drag-and-Drop Uploader**: Upload any combination of documents, images, code, media, or archives simultaneously.
- **Persistent Workspace**: Files remain active in your workspace across actions and tabs.
- **✨ 1-Click Demo Loader**: Instant button in the sidebar to populate the workspace with test files (including a disguised Trojan payload to demonstrate security features).
- **Dual View Modes**:
  - **List View**: Dense, informative tabular view with sortable columns, security status badges, sizes, and timestamps.
  - **Grid View**: Card tiles featuring category icons, quick info, and 1-click Download & Delete buttons.
- **➕ In-Browser File Creation**: Create and initialize new text, code, or markdown files directly from the web interface.

### 2. ⚡ In-Browser File Operations & Editor
- **👁️ Rich Previews**:
  - **Images**: Direct rendering for `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`, `.bmp` with file dimensions.
  - **Audio & Video**: Native web players for `.mp3`, `.wav`, `.ogg`, `.flac`, `.mp4`, `.mov`.
  - **Text & Code**: Formatted code view for Python, JSON, Markdown, CSV, and plain text.
- **✏️ In-Browser Text & Code Editor**: Edit scripts, config files, notes, or data files in a full-height editor and save modifications with 1 click.
- **🏷️ Rename & Duplicate**: Rename files safely with extension checks or generate duplicates (`_copy`).
- **📦 ZIP Extractor**: Unpack `.zip` archives directly into workspace folders with 1 click.
- **📥 Individual & Batch Download**: Download any individual file or click **"Download All as ZIP"**.

### 3. 🚨 Deep Security & Anti-Spoofing Defense
- **Magic-Byte Inspection**: Reads raw binary headers to determine true file types independently of filenames.
- **Trojan & Malware Disguise Alerts**: Flags dangerous extension mismatches (e.g., an executable `.exe` disguised as an `.png` invoice image) with high-visibility advisory banners.
- **🔬 Forensic Hex & Hash Inspector**: Interactive forensic hex dump with selectable byte buffer (16 to 256 bytes) and cryptographic SHA-256 digest computation.

### 4. 🗂️ Smart Content-Aware Organizer
- Automatically categorizes files into verified taxonomy groups:
  - `Images/`
  - `Documents/`
  - `Archives/`
  - `Audio/` & `Videos/`
  - `Executables/`
  - `Code_and_Data/`
  - `Review_Mismatches/` (quarantine for spoofed or suspicious files)
- **⚡ 1-Click Organized ZIP Archive**: Generates and downloads a single `.zip` file with all files arranged into their respective category folders.

### 5. 🔐 Cryptographic Integrity Guardian (SHA-256)
- **Immutable Baselines**: Capture a cryptographic snapshot manifest (`baseline.json`).
- **Differential Tamper Detection**:
  - `✔ Intact`: Hash verified against baseline.
  - `🚨 Tampered (Modified)`: Real-time alert with side-by-side hash comparison showing exact modifications.
  - `➕ Added`: Identifies files introduced after snapshot.
  - `➖ Deleted`: Identifies files missing from workspace.
- **Export Baseline**: Download baseline JSON for offline audit trails.

### 6. 📊 Visual Telemetry & Storage Analytics
- **Format Distribution**: Interactive Altair bar chart of detected binary signatures.
- **Security Verdicts**: Donut chart visualizing safe vs spoofed vs unknown files.
- **Storage Consumption**: Breakdown of disk usage (in KB/MB) by category.

---

## 🚀 Running the Web Application

### Prerequisites
Make sure Python 3.10+ is installed on your computer.

### Installation
Open your terminal in the project directory:
```bash
cd "D:\Python Coding\python file manager"
pip install -r requirements.txt
```

### Start Web Server
```bash
streamlit run app.py
```
Your default browser will automatically open to `http://localhost:8501`.

---

## 📁 Project Structure

```
python file manager/
├── app.py                 # Streamlit cloud-native file manager & web dashboard
├── main.py                # ANSI colorized interactive terminal CLI
├── file_identifier.py     # Binary signature & magic byte inspection engine
├── integrity_checker.py   # SHA-256 baseline creation & cryptographic diff engine
├── organizer.py           # Intelligent categorization & ZIP bundling engine
├── requirements.txt       # Project dependencies (streamlit, pandas, altair)
└── README.md              # Project documentation
```
