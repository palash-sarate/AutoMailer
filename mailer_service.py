import csv
import io
import os
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

import markdown
from dotenv import dotenv_values, set_key

import history_manager

ENV_PATH = os.path.join(os.getcwd(), ".env")


def get_config() -> Dict[str, str]:
    """Reads current configuration from .env."""
    if not os.path.exists(ENV_PATH):
        # Create empty .env if not exists
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.write("# AutoMailer Config\n")

    values = dotenv_values(ENV_PATH)
    return {
        "display_name": values.get("display_name", "") or "",
        "sender_email": values.get("sender_email", "") or "",
        "password": values.get("password", "") or "",
        "smtp_host": values.get("smtp_host", "smtp.gmail.com") or "smtp.gmail.com",
        "smtp_port": str(values.get("smtp_port", "587") or "587"),
        "mail_compose": values.get("mail_compose", "compose.md") or "compose.md",
        "subject": values.get("subject", "") or "",
    }


def save_config(new_config: Dict[str, str]) -> Dict[str, str]:
    """Updates configuration in .env."""
    for key, value in new_config.items():
        if value is not None:
            set_key(ENV_PATH, key, str(value).strip())
    return get_config()


def create_smtp_client(config: Optional[Dict[str, str]] = None) -> smtplib.SMTP:
    """Creates an authenticated SMTP connection."""
    cfg = config or get_config()
    host = cfg.get("smtp_host", "smtp.gmail.com").strip()
    port = int(cfg.get("smtp_port", "587") or 587)
    sender = cfg.get("sender_email", "").strip()
    pwd = (cfg.get("password", "") or "").replace(" ", "").strip()

    if not sender or not pwd:
        raise ValueError("Sender email and password are required.")

    context = ssl.create_default_context()

    if port == 465:
        server = smtplib.SMTP_SSL(host=host, port=port, context=context)
        server.login(sender, pwd)
        return server
    else:
        server = smtplib.SMTP(host=host, port=port, timeout=15)
        server.connect(host=host, port=port)
        server.ehlo()
        server.starttls(context=context)
        server.ehlo()
        server.login(sender, pwd)
        return server


def test_smtp_connection(config: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """Tests the SMTP connection and credentials without sending an email."""
    try:
        cfg = config or get_config()
        server = create_smtp_client(cfg)
        server.quit()
        return {
            "success": True,
            "message": f"Successfully connected and authenticated with {cfg.get('smtp_host', 'SMTP server')}!"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Authentication failed: {str(e)}"
        }


def substitute_template(template_str: str, row_dict: Dict[str, Any]) -> str:
    """Substitutes $VARIABLE occurrences in the template with values from row_dict."""
    result = template_str
    # Case-insensitive / direct replacement for all keys
    for key, val in row_dict.items():
        result = result.replace(f"${key}", str(val) if val is not None else "")
    return result


def render_email_preview(
    template_str: str,
    row_dict: Dict[str, Any],
    default_subject: Optional[str] = None,
    is_html: bool = False
) -> Dict[str, str]:
    """Generates preview data (Subject, Plain Text, HTML) for a specific row."""
    substituted = substitute_template(template_str, row_dict)
    
    # Determine subject
    if default_subject and default_subject.strip():
        subject = substitute_template(default_subject.strip(), row_dict)
        body_text = substituted
    else:
        lines = substituted.splitlines()
        subject = lines[0] if lines else "No Subject"
        body_text = "\n".join(lines[1:]).lstrip() if len(lines) > 1 else substituted

    if is_html:
        body_html = body_text
    else:
        body_html = markdown.markdown(
            body_text,
            extensions=["extra", "nl2br", "sane_lists"]
        )

    return {
        "subject": subject,
        "body_text": body_text,
        "body_html": body_html,
        "recipient": row_dict.get("EMAIL", row_dict.get("email", "")).strip()
    }


def list_available_attachments() -> List[Dict[str, Any]]:
    """Lists files located in the ATTACH/ folder if present."""
    attach_dir = os.path.join(os.getcwd(), "ATTACH")
    if not os.path.exists(attach_dir):
        os.makedirs(attach_dir, exist_ok=True)
        return []

    files = []
    for f in os.listdir(attach_dir):
        full_path = os.path.join(attach_dir, f)
        if os.path.isfile(full_path):
            files.append({
                "name": f,
                "size": os.path.getsize(full_path),
                "path": full_path
            })
    return files


def save_attachment_file(file_storage, filename: str) -> Dict[str, Any]:
    """Saves an uploaded file into the ATTACH/ folder."""
    attach_dir = os.path.join(os.getcwd(), "ATTACH")
    os.makedirs(attach_dir, exist_ok=True)
    clean_filename = os.path.basename(filename)
    target_path = os.path.join(attach_dir, clean_filename)
    file_storage.save(target_path)
    return {
        "name": clean_filename,
        "size": os.path.getsize(target_path),
        "path": target_path
    }


def delete_attachment_file(filename: str) -> bool:
    """Deletes a file from the ATTACH/ folder."""
    attach_dir = os.path.join(os.getcwd(), "ATTACH")
    clean_filename = os.path.basename(filename)
    target_path = os.path.join(attach_dir, clean_filename)
    if os.path.exists(target_path) and os.path.isfile(target_path):
        os.remove(target_path)
        return True
    return False


def send_single_email(
    row_dict: Dict[str, Any],
    template_str: str,
    row_index: int,
    csv_filename: str = "data.csv",
    force_send: bool = False,
    is_html: Optional[bool] = None,
    selected_attachments: Optional[List[str]] = None,
    config: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Sends an email to the recipient specified in row_dict.
    Performs duplicate prevention unless force_send=True.
    """
    cfg = config or get_config()
    sender_email = cfg.get("sender_email", "").strip()
    display_name = cfg.get("display_name", "").strip() or sender_email
    default_subject = cfg.get("subject", "")

    email = row_dict.get("EMAIL", row_dict.get("email", "")).strip()
    if not email:
        return {
            "success": False,
            "error": "No 'EMAIL' column or recipient address found in this row."
        }

    # 1. Duplicate check
    is_sent, previous_record = history_manager.is_row_sent(
        csv_filename, row_index, email, row_dict
    )
    if is_sent and not force_send:
        return {
            "success": False,
            "already_sent": True,
            "message": f"Email was already sent to {email} on {previous_record.get('timestamp')}. Enable 'Force Resend' to send again.",
            "record": previous_record
        }

    # 2. Render content
    template_is_html = is_html if is_html is not None else cfg.get("mail_compose", "").endswith(".html")
    preview = render_email_preview(template_str, row_dict, default_subject, template_is_html)
    subject = preview["subject"]
    body_text = preview["body_text"]
    body_html = preview["body_html"]

    # 3. Build MIME Message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{display_name} <{sender_email}>" if display_name else sender_email
    msg["To"] = email

    part_text = MIMEText(body_text, "plain", "utf-8")
    part_html = MIMEText(body_html, "html", "utf-8")
    msg.attach(part_text)
    msg.attach(part_html)

    # 4. Attachments (Campaign selected attachments + row-specific attachments)
    attach_files = list(selected_attachments or [])
    
    # Check if row has custom ATTACHMENT or ATTACHMENTS column
    row_attach_val = row_dict.get("ATTACHMENT") or row_dict.get("attachment") or row_dict.get("ATTACHMENTS") or row_dict.get("attachments")
    if row_attach_val:
        for single_att in str(row_attach_val).split(";"):
            single_att = single_att.strip()
            if single_att:
                # Check directly or inside ATTACH/
                possible_paths = [
                    single_att,
                    os.path.join(os.getcwd(), single_att),
                    os.path.join(os.getcwd(), "ATTACH", single_att)
                ]
                for p in possible_paths:
                    if os.path.exists(p) and os.path.isfile(p) and p not in attach_files:
                        attach_files.append(p)
                        break

    for file_path in attach_files:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            filename = os.path.basename(file_path)
            try:
                with open(file_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f'attachment; filename="{filename}"'
                    )
                    msg.attach(part)
            except Exception as e:
                print(f"Failed to attach {filename}: {e}")

    # 5. Connect and send
    try:
        server = create_smtp_client(cfg)
        server.sendmail(sender_email, email, msg.as_string())
        server.quit()

        # 6. Record success in tracking history
        record = history_manager.record_send_result(
            csv_filename=csv_filename,
            row_index=row_index,
            email=email,
            subject=subject,
            status="sent",
            row_data=row_dict
        )
        return {
            "success": True,
            "message": f"Email successfully sent to {email}",
            "record": record
        }
    except Exception as e:
        error_msg = str(e)
        # Record failure
        record = history_manager.record_send_result(
            csv_filename=csv_filename,
            row_index=row_index,
            email=email,
            subject=subject,
            status="failed",
            error=error_msg,
            row_data=row_dict
        )
        return {
            "success": False,
            "error": error_msg,
            "record": record
        }


def parse_csv_content(csv_text: str) -> Tuple[List[str], List[Dict[str, Any]]]:
    """Parses raw CSV string into headers and row dictionaries."""
    f = io.StringIO(csv_text.strip())
    reader = csv.reader(f)
    try:
        headers = next(reader)
    except StopIteration:
        return [], []

    # Clean header names
    clean_headers = [h.strip() for h in headers if h.strip()]
    f.seek(0)
    dict_reader = csv.DictReader(f)
    rows = []
    for idx, row in enumerate(dict_reader):
        clean_row = {k.strip(): v.strip() for k, v in row.items() if k}
        rows.append(clean_row)

    return clean_headers, rows
