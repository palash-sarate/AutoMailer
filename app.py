import csv
import io
import json
import os
import sys
import threading
import time
import webbrowser
from typing import Any, Dict

from flask import Flask, Response, jsonify, render_template_string, request, send_from_directory

import history_manager
import mailer_service
import updater_service
from logger_config import get_logger

logger = get_logger("app")

# Base directory determination for portable executable or regular script
def get_base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.getcwd()

def get_static_dir():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "static")
    return os.path.join(os.getcwd(), "static")

# Ensure working directory is next to executable or script
os.chdir(get_base_dir())
logger.info("AutoMailer backend initialized (v%s). Base Dir: %s", updater_service.APP_VERSION, get_base_dir())

app = Flask(__name__, static_folder=get_static_dir(), static_url_path="")


@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/")
def index():
    return send_from_directory(get_static_dir(), "index.html")


# ==========================================
# VERSION & OTA UPDATER ENDPOINTS
# ==========================================

@app.route("/api/version/status", methods=["GET"])
def get_version_status():
    """Returns application version and environment mode."""
    return jsonify({
        "version": updater_service.APP_VERSION,
        "is_frozen": updater_service.IS_FROZEN,
        "repo": updater_service.GITHUB_REPO
    })


@app.route("/api/version/check", methods=["GET"])
def check_version():
    """Queries GitHub Releases API for updates."""
    return jsonify(updater_service.check_for_updates())


@app.route("/api/version/apply", methods=["POST"])
def apply_version():
    """Downloads new release asset and triggers detached Windows swap."""
    data = request.json or {}
    download_url = data.get("download_url", "")
    return jsonify(updater_service.apply_update_and_restart(download_url))


# ==========================================
# CONFIG & SMTP ENDPOINTS
# ==========================================

@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify(mailer_service.get_config())


@app.route("/api/config", methods=["POST"])
def update_config():
    data = request.json or {}
    updated = mailer_service.save_config(data)
    return jsonify({"success": True, "config": updated})


@app.route("/api/config/test-smtp", methods=["POST"])
def test_smtp():
    data = request.json or {}
    # Use provided test credentials if any, otherwise active .env
    result = mailer_service.test_smtp_connection(data if data else None)
    return jsonify(result)


# ==========================================
# FILE DISCOVERY & MANAGEMENT
# ==========================================

@app.route("/api/files", methods=["GET"])
def list_files():
    root = os.getcwd()
    templates = []
    csv_files = []

    for f in os.listdir(root):
        full = os.path.join(root, f)
        if os.path.isfile(full):
            if f.endswith((".md", ".html", ".txt")):
                templates.append(f)
            elif f.endswith(".csv"):
                csv_files.append(f)

    # Sort files putting defaults first
    if "compose.md" in templates:
        templates.remove("compose.md")
        templates.insert(0, "compose.md")
    if "data.csv" in csv_files:
        csv_files.remove("data.csv")
        csv_files.insert(0, "data.csv")

    attachments = mailer_service.list_available_attachments()

    return jsonify({
        "templates": templates,
        "csv_files": csv_files,
        "attachments": attachments
    })


@app.route("/api/attachments/upload", methods=["POST"])
def upload_attachment():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    saved = mailer_service.save_attachment_file(file, file.filename)
    return jsonify({"success": True, "attachment": saved})


@app.route("/api/attachments/delete", methods=["POST"])
def delete_attachment():
    data = request.json or {}
    filename = data.get("filename", "")
    if not filename:
        return jsonify({"error": "No filename provided"}), 400

    deleted = mailer_service.delete_attachment_file(filename)
    return jsonify({"success": deleted})


# ==========================================
# TEMPLATE ENDPOINTS
# ==========================================

@app.route("/api/template", methods=["GET"])
def load_template():
    filename = request.args.get("file", "compose.md")
    path = os.path.join(os.getcwd(), os.path.basename(filename))
    if not os.path.exists(path):
        if filename == "compose.md":
            default_template = "Invoice Reminder for $NAME - $DATE\n\nDear $NAME,\n\nThis is a friendly reminder regarding your invoice **#$INVOICE_NO**.\n\nBest regards,\n**Operations Team**\n"
            with open(path, "w", encoding="utf-8") as f:
                f.write(default_template)
            return jsonify({"file": filename, "content": default_template})
        return jsonify({"error": f"File '{filename}' not found.", "content": ""}), 404

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    return jsonify({"file": filename, "content": content})


@app.route("/api/template", methods=["POST"])
def save_template():
    data = request.json or {}
    filename = os.path.basename(data.get("file", "compose.md") or "compose.md")
    content = data.get("content", "")
    path = os.path.join(os.getcwd(), filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

    return jsonify({"success": True, "file": filename, "message": f"Saved {filename} successfully."})


@app.route("/api/template/upload", methods=["POST"])
def upload_template():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    filename = os.path.basename(file.filename)
    path = os.path.join(os.getcwd(), filename)
    file.save(path)

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    return jsonify({"success": True, "file": filename, "content": content, "message": f"Uploaded {filename} successfully."})


# ==========================================
# CSV DATA ENDPOINTS
# ==========================================

@app.route("/api/csv/upload", methods=["POST"])
def upload_csv():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if not file or not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    filename = os.path.basename(file.filename)
    path = os.path.join(os.getcwd(), filename)
    file.save(path)

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    headers, rows = mailer_service.parse_csv_content(content)
    annotated_rows = []
    for idx, row in enumerate(rows):
        email = row.get("EMAIL", row.get("email", "")).strip()
        is_sent, record = history_manager.is_row_sent(filename, idx, email, row)
        annotated_rows.append({
            "index": idx,
            "data": row,
            "is_sent": is_sent,
            "sent_record": record
        })

    return jsonify({
        "success": True,
        "file": filename,
        "headers": headers,
        "rows": annotated_rows,
        "total": len(rows),
        "sent_count": sum(1 for r in annotated_rows if r["is_sent"]),
        "message": f"Uploaded and loaded {filename} successfully."
    })

@app.route("/api/csv", methods=["GET"])
def load_csv():
    filename = request.args.get("file", "data.csv")
    path = os.path.join(os.getcwd(), os.path.basename(filename))
    if not os.path.exists(path):
        if filename == "data.csv":
            default_csv = "NAME,DATE,AMOUNT,INVOICE_NO,EMAIL\nJohn Doe,2026-08-20,$250.00,INV-1001,recipient@example.com\n"
            with open(path, "w", encoding="utf-8") as f:
                f.write(default_csv)
        else:
            return jsonify({"error": f"File '{filename}' not found.", "headers": [], "rows": []}), 404

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    headers, rows = mailer_service.parse_csv_content(content)

    # Attach send status to each row
    annotated_rows = []
    for idx, row in enumerate(rows):
        email = row.get("EMAIL", row.get("email", "")).strip()
        is_sent, record = history_manager.is_row_sent(filename, idx, email, row)
        annotated_rows.append({
            "index": idx,
            "data": row,
            "is_sent": is_sent,
            "sent_record": record
        })

    return jsonify({
        "file": filename,
        "headers": headers,
        "rows": annotated_rows,
        "total": len(rows),
        "sent_count": sum(1 for r in annotated_rows if r["is_sent"])
    })


@app.route("/api/csv", methods=["POST"])
def save_csv():
    data = request.json or {}
    filename = os.path.basename(data.get("file", "data.csv") or "data.csv")
    headers = data.get("headers", [])
    rows = data.get("rows", [])
    path = os.path.join(os.getcwd(), filename)

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        row_dict = r.get("data", r)
        writer.writerow({k: row_dict.get(k, "") for k in headers})

    with open(path, "w", encoding="utf-8") as f:
        f.write(output.getvalue())

    return jsonify({"success": True, "file": filename, "message": f"Saved {filename} with {len(rows)} rows."})


# ==========================================
# PREVIEW & SENDING ENDPOINTS
# ==========================================

@app.route("/api/preview", methods=["POST"])
def preview_email():
    data = request.json or {}
    template_str = data.get("template", "")
    row_dict = data.get("row", {})
    subject_override = data.get("subject", None)
    is_html = data.get("is_html", False)
    override_cc = data.get("cc", None)
    override_bcc = data.get("bcc", None)

    preview = mailer_service.render_email_preview(
        template_str=template_str,
        row_dict=row_dict,
        default_subject=subject_override,
        is_html=is_html,
        override_cc=override_cc,
        override_bcc=override_bcc
    )
    return jsonify(preview)


@app.route("/api/send/single", methods=["POST"])
def send_single():
    data = request.json or {}
    row_dict = data.get("row", {})
    template_str = data.get("template", "")
    row_index = int(data.get("row_index", 0))
    csv_filename = data.get("csv_filename", "data.csv")
    force_send = bool(data.get("force_send", False))
    is_html = data.get("is_html", False)
    attachments = data.get("attachments", [])
    override_cc = data.get("cc", None)
    override_bcc = data.get("bcc", None)

    result = mailer_service.send_single_email(
        row_dict=row_dict,
        template_str=template_str,
        row_index=row_index,
        csv_filename=csv_filename,
        force_send=force_send,
        is_html=is_html,
        selected_attachments=attachments,
        override_cc=override_cc,
        override_bcc=override_bcc
    )
    return jsonify(result)


ACTIVE_BATCH_CANCELLATIONS = set()


@app.route("/api/send/batch-stop", methods=["POST"])
def stop_batch():
    """Signals an ongoing batch campaign to halt immediately."""
    data = request.json or {}
    batch_id = str(data.get("batch_id", "")).strip()
    logger.warning("Batch stop signal received for batch_id=%s", batch_id or "ALL")
    if batch_id:
        ACTIVE_BATCH_CANCELLATIONS.add(batch_id)
    ACTIVE_BATCH_CANCELLATIONS.add("__ALL__")
    return jsonify({"success": True, "message": "Batch cancellation signal recorded."})


@app.route("/api/send/batch-stream", methods=["POST"])
def send_batch_stream():
    """Server-Sent Events stream for batch email sending with live progress and cancel support."""
    req_data = request.json or {}
    template_str = req_data.get("template", "")
    rows = req_data.get("rows", [])
    csv_filename = req_data.get("csv_filename", "data.csv")
    force_all = bool(req_data.get("force_all", False))
    is_html = bool(req_data.get("is_html", False))
    attachments = req_data.get("attachments", [])
    delay = float(req_data.get("delay_seconds", 1.0))
    global_cc = req_data.get("global_cc", None)
    global_bcc = req_data.get("global_bcc", None)
    batch_id = str(req_data.get("batch_id", "")).strip()

    logger.info("Batch stream initialized: %d rows from %s (force_all=%s, delay=%.1fs, batch_id=%s)",
                len(rows), csv_filename, force_all, delay, batch_id)

    # Clear any previous cancellation for this batch_id
    if batch_id:
        ACTIVE_BATCH_CANCELLATIONS.discard(batch_id)
    ACTIVE_BATCH_CANCELLATIONS.discard("__ALL__")

    def generate_events():
        total = len(rows)
        sent_count = 0
        skipped_count = 0
        failed_count = 0
        was_stopped = False
        smtp_client = None

        yield f"data: {json.dumps({'type': 'start', 'total': total, 'batch_id': batch_id})}\n\n"

        # Pre-connect SMTP client if there are rows to send
        try:
            logger.debug("Pre-authenticating persistent SMTP connection for batch campaign...")
            smtp_client = mailer_service.create_smtp_client()
        except Exception as e:
            logger.warning("Initial batch SMTP pre-connect failed: %s (Will fallback per-row)", e)
            smtp_client = None

        try:
            for idx, item in enumerate(rows):
                # Check for cancellation before processing this row
                if (batch_id and batch_id in ACTIVE_BATCH_CANCELLATIONS) or "__ALL__" in ACTIVE_BATCH_CANCELLATIONS:
                    if batch_id:
                        ACTIVE_BATCH_CANCELLATIONS.discard(batch_id)
                    ACTIVE_BATCH_CANCELLATIONS.discard("__ALL__")
                    was_stopped = True
                    logger.info("Batch campaign %s cancelled by user at row %d/%d", batch_id, idx + 1, total)
                    yield f"data: {json.dumps({'type': 'stopped', 'total': total, 'sent': sent_count, 'skipped': skipped_count, 'failed': failed_count, 'stopped_at': idx, 'message': 'Campaign stopped by user.'})}\n\n"
                    break

                row_idx = item.get("index", idx)
                row_dict = item.get("data", item)
                email = row_dict.get("EMAIL", row_dict.get("email", "")).strip()

                # Duplicate check
                is_sent, prev = history_manager.is_row_sent(csv_filename, row_idx, email, row_dict)
                if is_sent and not force_all:
                    skipped_count += 1
                    logger.info("[Batch %d/%d] Skipped %s (Already sent on %s)", idx + 1, total, email, prev.get("timestamp") if prev else "earlier")
                    yield f"data: {json.dumps({'type': 'progress', 'current': idx + 1, 'total': total, 'status': 'skipped', 'email': email, 'index': row_idx, 'message': 'Skipped (Already sent)'})}\n\n"
                    continue

                # If smtp_client was not created or was dropped, try to create it
                if smtp_client is None:
                    try:
                        smtp_client = mailer_service.create_smtp_client()
                    except Exception:
                        smtp_client = None

                result = mailer_service.send_single_email(
                    row_dict=row_dict,
                    template_str=template_str,
                    row_index=row_idx,
                    csv_filename=csv_filename,
                    force_send=force_all,
                    is_html=is_html,
                    selected_attachments=attachments,
                    override_cc=global_cc,
                    override_bcc=global_bcc,
                    smtp_client=smtp_client
                )

                if result.get("success"):
                    sent_count += 1
                    logger.info("[Batch %d/%d] Sent to %s", idx + 1, total, email)
                    yield f"data: {json.dumps({'type': 'progress', 'current': idx + 1, 'total': total, 'status': 'sent', 'email': email, 'index': row_idx, 'record': result.get('record'), 'cc': result.get('cc', []), 'bcc': result.get('bcc', [])})}\n\n"
                else:
                    # If failed, drop the cached client so next row recreates a fresh connection
                    if smtp_client:
                        try:
                            smtp_client.quit()
                        except Exception:
                            pass
                        smtp_client = None
                    failed_count += 1
                    logger.warning("[Batch %d/%d] Failed sending to %s: %s", idx + 1, total, email, result.get('error'))
                    yield f"data: {json.dumps({'type': 'progress', 'current': idx + 1, 'total': total, 'status': 'failed', 'email': email, 'index': row_idx, 'error': result.get('error')})}\n\n"

                if idx < total - 1 and delay > 0:
                    # Responsive interval sleep to catch cancellation immediately
                    sleep_start = time.time()
                    while time.time() - sleep_start < delay:
                        if (batch_id and batch_id in ACTIVE_BATCH_CANCELLATIONS) or "__ALL__" in ACTIVE_BATCH_CANCELLATIONS:
                            break
                        time.sleep(0.08)

            if not was_stopped:
                logger.info("Batch campaign %s completed: Sent=%d, Skipped=%d, Failed=%d", batch_id, sent_count, skipped_count, failed_count)
                yield f"data: {json.dumps({'type': 'complete', 'total': total, 'sent': sent_count, 'skipped': skipped_count, 'failed': failed_count})}\n\n"
        finally:
            if smtp_client:
                try:
                    smtp_client.quit()
                except Exception:
                    pass

    return Response(generate_events(), mimetype="text/event-stream")


# ==========================================
# HISTORY & LOGS ENDPOINTS
# ==========================================

@app.route("/api/history", methods=["GET"])
def get_history():
    records = history_manager.get_all_records()
    return jsonify({"records": records, "total": len(records)})


@app.route("/api/history/reset", methods=["POST"])
def reset_history():
    data = request.json or {}
    csv_file = data.get("csv_file", None)
    cleared = history_manager.reset_history(csv_file)
    return jsonify({"success": True, "cleared_count": cleared, "message": f"Cleared {cleared} tracking records."})


# ==========================================
# MAIN RUNNER
# ==========================================

def open_browser():
    time.sleep(1.2)
    webbrowser.open("http://localhost:5000")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"\n=======================================================")
    print(f"  Bulk Email Sender Dashboard running at:")
    print(f"  👉 http://localhost:{port}")
    print(f"=======================================================\n")
    if not os.getenv("NO_AUTO_OPEN"):
        threading.Thread(target=open_browser, daemon=True).start()
    app.run(host="0.0.0.0", port=port, debug=False)
