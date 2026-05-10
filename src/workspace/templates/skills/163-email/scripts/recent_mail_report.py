from __future__ import annotations

import argparse
import email
import imaplib
import json
import os
import re
import sys
from datetime import datetime, timedelta, date
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Union

from dotenv import dotenv_values

# 修复 Windows 控制台编码问题：设置 stdout 为 UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def require_config(config: dict[str, str], name: str) -> str:
    value = (os.getenv(name) or config.get(name, "")).strip()
    if not value:
        raise RuntimeError(f"missing required config: {name}")
    return value


def mask_email(value: str) -> str:
    local, _, domain = value.partition("@")
    if not local or not domain:
        return "***"
    if len(local) <= 4:
        masked_local = local[0] + "***"
    else:
        masked_local = local[:3] + "***" + local[-2:]
    return f"{masked_local}@{domain}"


def decode_imap_items(items: list[bytes] | tuple[bytes, ...] | None) -> list[str]:
    decoded: list[str] = []
    for item in items or []:
        if isinstance(item, bytes):
            decoded.append(item.decode("utf-8", errors="replace"))
        else:
            decoded.append(str(item))
    return decoded


def decode_mime_words(value: str) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    decoded: list[str] = []
    for text, encoding in parts:
        if isinstance(text, bytes):
            decoded.append(text.decode(encoding or "utf-8", errors="replace"))
        else:
            decoded.append(str(text))
    return "".join(decoded)


def parse_mailbox_name(line: bytes | str) -> str:
    text = line.decode("utf-8", errors="replace") if isinstance(line, bytes) else str(line)
    quoted = re.findall(r'"([^"]+)"', text)
    if quoted:
        return quoted[-1]
    parts = text.split()
    return parts[-1] if parts else ""


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_text_preview(message: email.message.Message, max_chars: int = 500) -> str:
    text_candidates: list[str] = []

    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            content_disposition = (part.get("Content-Disposition") or "").lower()
            if "attachment" in content_disposition:
                continue
            if content_type not in {"text/plain", "text/html"}:
                continue
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            charset = part.get_content_charset() or "utf-8"
            text = payload.decode(charset, errors="replace")
            text_candidates.append(clean_text(text))
    else:
        payload = message.get_payload(decode=True)
        if payload is not None:
            charset = message.get_content_charset() or "utf-8"
            text_candidates.append(clean_text(payload.decode(charset, errors="replace")))

    for candidate in text_candidates:
        if candidate:
            return candidate[:max_chars]
    return ""


def send_imap_id(mail: imaplib.IMAP4_SSL) -> None:
    capability_status, capability_data = mail.capability()
    if capability_status != "OK":
        return

    capability_blob = " ".join(decode_imap_items(capability_data)).upper()
    if " ID" not in f" {capability_blob} ":
        return

    id_payload = (
        '("name" "hello-claw-mail-report" '
        '"version" "1.0" '
        '"vendor" "datawhale" '
        '"support-url" "https://github.com/datawhalechina/hello-claw")'
    )
    mail.xatom("ID", id_payload)


def select_mailbox(mail: imaplib.IMAP4_SSL, preferred_folder: str) -> str:
    list_status, mailboxes = mail.list()
    available_folders: list[str] = []
    if list_status == "OK" and mailboxes:
        available_folders = [parse_mailbox_name(item) for item in mailboxes if item]

    candidates: list[str] = []
    for item in [preferred_folder, "INBOX", "Inbox", *available_folders]:
        name = item.strip()
        if name and name not in candidates:
            candidates.append(name)

    for candidate in candidates:
        for actual in [candidate, f'"{candidate}"']:
            if actual != candidate and '"' in candidate:
                continue
            for readonly in [True, False]:
                select_status, _ = mail.select(actual, readonly=readonly)
                if select_status == "OK":
                    return actual

    raise RuntimeError("failed to select mailbox")


def format_imap_date(value: datetime.date) -> str:
    return f"{value.day:02d}-{MONTHS[value.month - 1]}-{value.year}"


def parse_date_string(date_str: str) -> date:
    """Parse date string in various formats."""
    date_str = date_str.strip()
    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%Y.%m.%d",
        "%Y-%m-%d",
        "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {date_str}")


def validate_dates(dates: list[date]) -> list[date]:
    """Validate dates are not in the future. Return valid dates only."""
    today = datetime.now().astimezone().date()
    valid = []
    for d in dates:
        if d > today:
            print(f"Warning: Date {d.isoformat()} is in the future, skipping.", file=__import__("sys").stderr)
        else:
            valid.append(d)
    return valid


def fetch_emails_by_range(
    mail: imaplib.IMAP4_SSL, folder: str, since_date: date, before_date: date
) -> tuple[str, list[dict[str, str]]]:
    """Fetch emails within a date range [since_date, before_date)."""
    selected_folder = select_mailbox(mail, folder)

    since_str = format_imap_date(since_date)
    before_str = format_imap_date(before_date)

    search_status, data = mail.search(None, "SINCE", since_str, "BEFORE", before_str)
    if search_status != "OK":
        raise RuntimeError("failed to search mailbox")

    message_ids = data[0].split()
    items: list[dict[str, str]] = []

    for message_id in reversed(message_ids):
        fetch_status, fetch_data = mail.fetch(message_id, "(RFC822)")
        if fetch_status != "OK" or not fetch_data or fetch_data[0] is None:
            continue

        raw_message = fetch_data[0][1]
        if not isinstance(raw_message, bytes):
            continue

        message = email.message_from_bytes(raw_message)
        date_value = message.get("Date", "")
        try:
            parsed_date = parsedate_to_datetime(date_value)
            date_text = parsed_date.astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
        except Exception:
            date_text = date_value

        items.append(
            {
                "subject": decode_mime_words(message.get("Subject", "")),
                "from": decode_mime_words(message.get("From", "")),
                "date": date_text,
                "preview": extract_text_preview(message),
            }
        )

    return selected_folder, items


def fetch_emails_by_dates(
    mail: imaplib.IMAP4_SSL, folder: str, dates: list[date]
) -> tuple[str, list[dict[str, str]]]:
    """Fetch emails for specific dates."""
    selected_folder = select_mailbox(mail, folder)

    all_items: list[dict[str, str]] = []
    seen_message_ids: set[bytes] = set()

    for target_date in sorted(set(dates)):
        since_str = format_imap_date(target_date)
        next_day = target_date + timedelta(days=1)
        before_str = format_imap_date(next_day)

        search_status, data = mail.search(None, "SINCE", since_str, "BEFORE", before_str)
        if search_status != "OK":
            continue

        message_ids = data[0].split()

        for message_id in reversed(message_ids):
            if message_id in seen_message_ids:
                continue
            seen_message_ids.add(message_id)

            fetch_status, fetch_data = mail.fetch(message_id, "(RFC822)")
            if fetch_status != "OK" or not fetch_data or fetch_data[0] is None:
                continue

            raw_message = fetch_data[0][1]
            if not isinstance(raw_message, bytes):
                continue

            message = email.message_from_bytes(raw_message)
            date_value = message.get("Date", "")
            try:
                parsed_date = parsedate_to_datetime(date_value)
                date_text = parsed_date.astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
            except Exception:
                date_text = date_value

            all_items.append(
                {
                    "subject": decode_mime_words(message.get("Subject", "")),
                    "from": decode_mime_words(message.get("From", "")),
                    "date": date_text,
                    "preview": extract_text_preview(message),
                }
            )

    # Sort by date descending
    all_items.sort(key=lambda x: x.get("date", ""), reverse=True)
    return selected_folder, all_items


def parse_time_args(args: argparse.Namespace) -> tuple[Union[date, None], Union[date, None], list[date]]:
    """Parse time arguments and return (since_date, before_date, specific_dates)."""
    today = datetime.now().astimezone().date()

    # Mode 1: Relative days (e.g., --days 3 for last 3 days)
    if args.days is not None:
        since = today - timedelta(days=args.days)
        return since, today, []

    # Mode 2: Date range (e.g., --since 2025-12-01 --before 2025-12-13)
    if args.since or args.before:
        since = parse_date_string(args.since) if args.since else today - timedelta(days=1)
        before = parse_date_string(args.before) if args.before else today + timedelta(days=1)
        return since, before, []

    # Mode 3: Specific dates (e.g., --dates "2025-12-01,2025-12-05,2025-12-10")
    if args.dates:
        date_strs = [d.strip() for d in args.dates.split(",") if d.strip()]
        dates = [parse_date_string(d) for d in date_strs]
        return None, None, dates

    # Default: yesterday
    yesterday = today - timedelta(days=1)
    return yesterday, today, []


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch emails from mailbox")
    parser.add_argument("--since", type=str, help="Start date (YYYY-MM-DD or YYYY/MM/DD)")
    parser.add_argument("--before", type=str, help="End date (exclusive, YYYY-MM-DD or YYYY/MM/DD)")
    parser.add_argument("--days", type=int, help="Fetch emails from last N days")
    parser.add_argument("--dates", type=str, help="Specific dates, comma-separated (e.g., '2025-12-01,2025-12-05')")
    args = parser.parse_args()

    env_path = Path(__file__).with_name(".env")
    config = {k: (v or "") for k, v in dotenv_values(env_path, encoding="utf-8-sig").items()}

    host = require_config(config, "MAIL_HOST")
    port = int((os.getenv("MAIL_PORT") or config.get("MAIL_PORT") or "993").strip())
    user = require_config(config, "MAIL_USER")
    password = require_config(config, "MAIL_PASSWORD")
    folder = (os.getenv("MAIL_FOLDER") or config.get("MAIL_FOLDER") or "INBOX").strip() or "INBOX"

    since_date, before_date, specific_dates = parse_time_args(args)

    mail = None
    try:
        mail = imaplib.IMAP4_SSL(host, port)
        mail.login(user, password)
        send_imap_id(mail)

        if specific_dates:
            valid_dates = validate_dates(specific_dates)
            if not valid_dates:
                result = {
                    "mailbox": mask_email(user),
                    "folder": folder,
                    "error": "No valid dates to query",
                    "total_messages": 0,
                    "items": [],
                }
            else:
                selected_folder, items = fetch_emails_by_dates(mail, folder, valid_dates)
                result = {
                    "mailbox": mask_email(user),
                    "folder": selected_folder,
                    "query_dates": [d.isoformat() for d in sorted(set(valid_dates))],
                    "total_messages": len(items),
                    "items": items,
                }
        else:
            # Validate range dates
            today = datetime.now().astimezone().date()
            if since_date > today:
                result = {
                    "mailbox": mask_email(user),
                    "folder": folder,
                    "error": "Start date is in the future",
                    "total_messages": 0,
                    "items": [],
                }
            else:
                # Clamp before_date to today+1 if it exceeds
                effective_before = min(before_date, today + timedelta(days=1))
                selected_folder, items = fetch_emails_by_range(mail, folder, since_date, effective_before)
                result = {
                    "mailbox": mask_email(user),
                    "folder": selected_folder,
                    "window": {
                        "since": since_date.isoformat(),
                        "before": effective_before.isoformat(),
                    },
                    "total_messages": len(items),
                    "items": items,
                }

        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        try:
            if mail is not None:
                mail.logout()
        except Exception:
            pass


if __name__ == "__main__":
    main()