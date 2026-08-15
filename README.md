# 📬 AutoMailer Pro - Bulk Email Sender

> A modern, full-featured Bulk Email Sender with an interactive Web Dashboard, live Markdown/HTML templating, CSV data manager, row-by-row email preview, duplicate prevention tracking, drag-and-drop attachments, and portable executable packaging.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-green.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#)

---

## ✨ Key Features

| Feature | Description |
| :--- | :--- |
| 🎨 **Interactive Web Dashboard** | Sleek glassmorphic dark/light UI with real-time feedback and tabbed navigation. |
| 📝 **Live Template Editor** | Edit Markdown (`compose.md`) or HTML templates with split-view live rendered preview and click-to-insert variable tokens. |
| 📊 **CSV Data Manager** | Full interactive grid to view, search, and inline-edit recipient records, with options to add/delete rows and columns. |
| 👁️ **Row-by-Row Preview** | Inspect the exact rendered email (`From`, `To`, `Cc`, `Bcc`, `Subject`, `Body`) for each recipient before sending. |
| 👥 **Flexible CC & BCC Support** | Configure **Global CC/BCC** (for all campaign emails) or per-recipient **Row CC/BCC** directly in CSV columns (`CC` and `BCC`), with quick override buttons in Preview. |
| 🛡️ **Duplicate Send Protection** | Built-in tracking (`sent_history.json`) records sent timestamps. Accidental resends are locked unless "Force Resend" is explicitly enabled. |
| 📎 **Attachments Manager** | Drag & drop file uploads directly into the `ATTACH/` folder, select which files to include, and support per-row dynamic attachments via an `ATTACHMENT` column in CSV. |
| ⚡ **1-Click SMTP Verification** | Test your Gmail / SMTP connection and credentials directly in the Settings tab before launching a campaign. |
| 🚀 **Batch & Single Dispatch** | Send individual emails row-by-row or run batch campaigns with customizable delays and live progress bars. |
| 📦 **Portable Standalone Executable** | 1-click builder to bundle the app into a portable Windows `.exe` that runs on double-click with zero installation required. |
| 💻 **CLI Compatibility** | Full backward compatibility for terminal-only execution via `python send.py`. |

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/palash-sarate/AutoMailer.git
cd AutoMailer
```

### 2. Set Up Virtual Environment & Dependencies
```bash
# Create and activate virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On macOS/Linux:
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 3. Launch the Web Dashboard
```bash
python app.py
```
> The dashboard will start and automatically open your default browser at **`http://localhost:5000`**.  
> *(On Windows, you can also simply double-click **`Start_AutoMailer.bat`**)*

---

## ⚙️ Configuration (`.env`)

You can configure credentials directly from the **Settings** tab in the Web Dashboard, or by creating a `.env` file in the project root:

```ini
display_name="Your Name"
sender_email="your_email@gmail.com"
password="xxxx xxxx xxxx xxxx"
smtp_host="smtp.gmail.com"
smtp_port="587"
mail_compose="compose.md"
subject=""
```

### 🔑 Generating a Google App Password (for Gmail)
1. Go to your **Google Account** > **Security**.
2. Enable **2-Step Verification** (if not already enabled).
3. Generate a 16-character App Password at:  
   🔗 **[https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)**
4. Paste the 16-character password into the **Password** field in Settings.

---

## 📖 How to Use

### 1. Draft Your Template (`compose.md`)
- Go to the **Template** tab in the dashboard.
- Write your email in **Markdown** or **HTML**.
- Use variable placeholders prefixed with `$` corresponding to your CSV column headers (e.g., `$NAME`, `$DATE`, `$AMOUNT`, `$INVOICE_NO`).
- Click any column chip in the variable bar to automatically insert it at your cursor.
- The **first line** of your template serves as the email Subject (unless a custom Subject is set in Settings).

```markdown
Invoice Reminder for $NAME - $DATE

Dear $NAME,

This is a reminder that invoice **#$INVOICE_NO** of **$AMOUNT** is due on **$DATE**.

Best regards,  
**Finance Team**
```

### 2. Prepare Recipient Data (`data.csv`)
- Go to the **CSV Data** tab.
- Add or import your contact list. Ensure there is an **`EMAIL`** column header.
- You can edit any cell directly in the table, add new custom columns, or search across rows.

```csv
NAME,DATE,AMOUNT,INVOICE_NO,EMAIL
John Doe,2026-08-20,$250.00,INV-1001,john@example.com
Jane Smith,2026-08-22,$450.00,INV-1002,jane@example.com
```

### 3. Add Attachments
- Go to the **Attachments** tab or the Preview sidebar.
- Drag & drop files (PDFs, images, documents) into the upload area or click **"Upload New Files"**.
- Check the box next to files you wish to attach to all outgoing emails.
- **Dynamic Row Attachments:** Add an `ATTACHMENT` column in `data.csv` (e.g. `invoice_1001.pdf`) to send unique personalized files to specific recipients.

### 4. Preview & Dispatch
- Go to the **Preview & Send** tab.
- Cycle through recipients to verify that all variables and formatting render correctly.
- Click **"Send This Email"** to send to the current recipient.
- Or click **"Batch Send All Pending"** to send to all recipients sequentially with a progress bar and duplicate prevention.

---

## 📦 Building a Portable Standalone App (`.exe`)

To package AutoMailer into a portable executable that can be shared with anyone (no Python installation required):

```bash
python build_exe.py
```

This generates a standalone folder at:
```
dist/AutoMailer_Portable/
├── AutoMailer.exe      <-- Double-click to launch the dashboard!
├── .env
├── compose.md
├── data.csv
└── ATTACH/
```
You can zip the `AutoMailer_Portable` folder and share it with anyone.

---

## 🤖 Automated GitHub Actions Releases

The repository includes a GitHub Action workflow ([`.github/workflows/release.yml`](file:///.github/workflows/release.yml)) that automatically tests, builds, and publishes `AutoMailer_Portable_Windows.zip` to **GitHub Releases**.

### How to Trigger an Automated Release:

1. **Option A: Push a Version Tag (Standard)**:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
2. **Option B: Push a commit with `[release]` in the message**:
   ```bash
   git commit -m "New features ready [release]"
   git push origin main
   ```
3. **Option C: Manual Trigger on GitHub**:
   - Go to your repository's **Actions** tab on GitHub.
   - Select **Build & Release Portable Executable**.
   - Click **Run workflow** and specify a tag version (e.g. `v1.0.0`).

---

## 📂 Project Structure

```
bulk-email-sender/
├── app.py                  # Flask Web Server & REST API backend
├── mailer_service.py       # SMTP authentication, rendering & sending engine
├── history_manager.py      # Tracking and duplicate-prevention store
├── build_exe.py            # PyInstaller standalone portable packager
├── send.py                 # CLI sender script
├── settings.py             # CLI settings loader
├── Start_AutoMailer.bat    # Windows 1-click double-click launcher
├── test_app.py             # Automated unit tests
├── requirements.txt        # Python package dependencies
├── compose.md              # Default email template
├── data.csv                # Default recipient dataset
├── ATTACH/                 # Directory for email attachments
└── static/                 # Web Dashboard Frontend
    ├── index.html          # Dashboard HTML UI
    ├── style.css           # Modern Dark/Light design system
    └── app.js              # Client-side logic, Markdown preview, batch engine
```

---

## 🧪 Running Tests

Run the test suite to verify endpoints, template rendering, and duplicate prevention:

```bash
python test_app.py
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
