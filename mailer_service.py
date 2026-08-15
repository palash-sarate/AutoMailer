import csv
import io
import mimetypes
import os
import smtplib
import ssl
from email import encoders
from email.header import Header
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

import markdown
from dotenv import dotenv_values, set_key

import history_manager

ENV_PATH = os.path.join(os.getcwd(), ".env")
MAX_RAW_ATTACHMENT_BYTES = 19 * 1024 * 1024  # 19 MB raw ~= 25.3 MB base64 encoded
DEFAULT_SMTP_TIMEOUT = 180  # 3 minutes for large multi-MB uploads


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
        "global_cc": values.get("global_cc", "") or "",
        "global_bcc": values.get("global_bcc", "") or "",
    }


def save_config(new_config: Dict[str, str]) -> Dict[str, str]:
    """Updates configuration in .env."""
    for key, value in new_config.items():
        if value is not None:
            set_key(ENV_PATH, key, str(value).strip())
    return get_config()


def create_smtp_client(config: Optional[Dict[str, str]] = None, timeout: int = DEFAULT_SMTP_TIMEOUT) -> smtplib.SMTP:
    """Creates an authenticated SMTP connection with generous timeout for large attachments."""
    cfg = config or get_config()
    host = cfg.get("smtp_host", "smtp.gmail.com").strip()
    port = int(cfg.get("smtp_port", "587") or 587)
    sender = cfg.get("sender_email", "").strip()
    pwd = (cfg.get("password", "") or "").replace(" ", "").strip()

    if not sender or not pwd:
        raise ValueError("Sender email and password are required.")

    context = ssl.create_default_context()

    if port == 465:
        server = smtplib.SMTP_SSL(host=host, port=port, context=context, timeout=timeout)
        server.login(sender, pwd)
        return server
    else:
        server = smtplib.SMTP(host=host, port=port, timeout=timeout)
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


def parse_email_list(raw_input: Any, row_dict: Optional[Dict[str, Any]] = None) -> List[str]:
    """Parses and deduplicates a comma/semicolon-separated string or list of emails."""
    if not raw_input:
        return []
    items = []
    if isinstance(raw_input, list):
        for elem in raw_input:
            items.extend(str(elem).replace(";", ",").split(","))
    else:
        items = str(raw_input).replace(";", ",").split(",")

    emails: List[str] = []
    for item in items:
        if row_dict:
            item = substitute_template(item, row_dict)
        item = item.strip().strip("<>\"' ")
        if item and "@" in item and item not in emails:
            emails.append(item)
    return emails


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
    is_html: bool = False,
    override_cc: Optional[Any] = None,
    override_bcc: Optional[Any] = None,
    config: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Generates preview data (Subject, Plain Text, HTML, CC, BCC) for a specific row."""
    cfg = config or get_config()
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

    # CC breakdown
    global_cc_list = parse_email_list(cfg.get("global_cc", ""))
    row_cc_raw = row_dict.get("CC") or row_dict.get("cc") or row_dict.get("Cc") or ""
    row_cc_list = parse_email_list(row_cc_raw, row_dict)
    if override_cc is not None:
        final_cc_list = parse_email_list(override_cc, row_dict)
    else:
        final_cc_list = []
        for e in global_cc_list + row_cc_list:
            if e not in final_cc_list:
                final_cc_list.append(e)

    # BCC breakdown
    global_bcc_list = parse_email_list(cfg.get("global_bcc", ""))
    row_bcc_raw = row_dict.get("BCC") or row_dict.get("bcc") or row_dict.get("Bcc") or ""
    row_bcc_list = parse_email_list(row_bcc_raw, row_dict)
    if override_bcc is not None:
        final_bcc_list = parse_email_list(override_bcc, row_dict)
    else:
        final_bcc_list = []
        for e in global_bcc_list + row_bcc_list:
            if e not in final_bcc_list:
                final_bcc_list.append(e)

    return {
        "subject": subject,
        "body_text": body_text,
        "body_html": body_html,
        "recipient": row_dict.get("EMAIL", row_dict.get("email", "")).strip(),
        "global_cc": global_cc_list,
        "row_cc": row_cc_list,
        "cc": final_cc_list,
        "global_bcc": global_bcc_list,
        "row_bcc": row_bcc_list,
        "bcc": final_bcc_list
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
    override_cc: Optional[Any] = None,
    override_bcc: Optional[Any] = None,
    config: Optional[Dict[str, str]] = None,
    smtp_client: Optional[smtplib.SMTP] = None
) -> Dict[str, Any]:
    """
    Sends an email to the recipient specified in row_dict, along with any CC and BCC recipients.
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

    # 2. Render content & compute CC/BCC
    template_is_html = is_html if is_html is not None else cfg.get("mail_compose", "").endswith(".html")
    preview = render_email_preview(
        template_str=template_str,
        row_dict=row_dict,
        default_subject=default_subject,
        is_html=template_is_html,
        override_cc=override_cc,
        override_bcc=override_bcc,
        config=cfg
    )
    subject = preview["subject"]
    body_text = preview["body_text"]
    body_html = preview["body_html"]
    cc_list = preview["cc"]
    bcc_list = preview["bcc"]

    # 3. Collect & Validate Attachments
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

    valid_attachments = []
    total_attach_size = 0
    for file_path in attach_files:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            size = os.path.getsize(file_path)
            total_attach_size += size
            valid_attachments.append((file_path, size))

    if total_attach_size > MAX_RAW_ATTACHMENT_BYTES:
        size_mb = round(total_attach_size / (1024 * 1024), 2)
        return {
            "success": False,
            "error": f"Total attachment size ({size_mb} MB) exceeds Gmail's 25 MB limit (approx 19 MB unencoded)."
        }

    # 4. Build RFC-Compliant MIME Structure
    # Root container: multipart/mixed if attachments exist, else multipart/alternative
    body_container = MIMEMultipart("alternative")
    part_text = MIMEText(body_text, "plain", "utf-8")
    part_html = MIMEText(body_html, "html", "utf-8")
    body_container.attach(part_text)
    body_container.attach(part_html)

    if valid_attachments:
        msg = MIMEMultipart("mixed")
        msg.attach(body_container)

        for file_path, file_size in valid_attachments:
            filename = os.path.basename(file_path)
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type and "/" in mime_type:
                main_type, sub_type = mime_type.split("/", 1)
            else:
                main_type, sub_type = "application", "octet-stream"

            try:
                part = MIMEBase(main_type, sub_type)
                with open(file_path, "rb") as f:
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=filename
                )
                msg.attach(part)
            except Exception as e:
                print(f"Failed to attach {filename}: {e}")
    else:
        msg = body_container

    # Header metadata
    msg["Subject"] = subject
    msg["From"] = f"{display_name} <{sender_email}>" if display_name else sender_email
    msg["To"] = email

    if cc_list:
        msg["Cc"] = ", ".join(cc_list)
    # Note: BCC header is deliberately omitted from msg for privacy, but included in envelope dispatch

    # 5. Build envelope recipient list (To + CC + BCC)
    envelope_recipients = [email]
    for c in cc_list:
        if c not in envelope_recipients:
            envelope_recipients.append(c)
    for b in bcc_list:
        if b not in envelope_recipients:
            envelope_recipients.append(b)

    # 6. Connect and send
    server = smtp_client
    should_quit = False

    try:
        if server is None:
            server = create_smtp_client(cfg)
            should_quit = True

        try:
            server.sendmail(sender_email, envelope_recipients, msg.as_string())
        except (smtplib.SMTPServerDisconnected, smtplib.SMTPConnectError, smtplib.SMTPException) as conn_err:
            # If a connection error occurs on a persistent connection, try reconnecting once
            if not should_quit:
                try:
                    server = create_smtp_client(cfg)
                    server.sendmail(sender_email, envelope_recipients, msg.as_string())
                except Exception:
                    raise conn_err
            else:
                raise conn_err

        if should_quit:
            try:
                server.quit()
            except Exception:
                pass

        # 7. Record success in tracking history
        record = history_manager.record_send_result(
            csv_filename=csv_filename,
            row_index=row_index,
            email=email,
            subject=subject,
            status="sent",
            row_data={
                **row_dict,
                "_cc": cc_list,
                "_bcc": bcc_list
            }
        )
        return {
            "success": True,
            "message": f"Email successfully sent to {email}" + (f" (CC: {', '.join(cc_list)})" if cc_list else "") + (f" (BCC: {len(bcc_list)} recipients)" if bcc_list else ""),
            "record": record,
            "cc": cc_list,
            "bcc": bcc_list
        }
    except Exception as e:
        if should_quit and server is not None:
            try:
                server.quit()
            except Exception:
                pass
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
