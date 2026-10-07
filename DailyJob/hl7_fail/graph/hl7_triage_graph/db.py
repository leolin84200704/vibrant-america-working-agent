"""Read-only access to prod lis_emr. The graph never writes to the database."""
from __future__ import annotations

import re
import socket
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pymysql
import pymysql.cursors

from .config import Settings

INTEGRATION_COLUMNS = (
    "id, customer_id, clinic_id, customer_npi, effective_npi, clinic_name, "
    "integration_type, status, ordering_enabled, legacy_emr_service, "
    "sftp_ordering_path, sftp_result_path, updated_at"
)


def db_reachable(settings: Settings, timeout: float = 5.0) -> bool:
    try:
        with socket.create_connection((settings.db_host, settings.db_port), timeout=timeout):
            return True
    except OSError:
        return False


def connect(settings: Settings):
    return pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        ssl={"ssl_mode": "REQUIRED"},
        connect_timeout=30,
        read_timeout=120,
        cursorclass=pymysql.cursors.DictCursor,
    )


def _plain(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ")
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return value


def query(conn, sql: str, args: tuple | list | None = None) -> list[dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(sql, args or ())
        return [{k: _plain(v) for k, v in row.items()} for row in cur.fetchall()]


def fetch_failed_rows(conn, lookback_hours: int) -> list[dict[str, Any]]:
    sql = """
        SELECT id, file_name, emr_code_not_found, customer_not_found, sftpDir,
               emr_service, retry_num, parse_finished, received_time,
               last_error, LEFT(error_detail, 500) AS error_detail,
               last_update_pod_name,
               (order_input IS NOT NULL) AS has_order_input,
               LEFT(order_input, 2000) AS order_input
        FROM hl7_file_input
        WHERE parse_finished = 0
          AND retry_num = 0
          AND received_time >= NOW() - INTERVAL %s HOUR
        ORDER BY received_time DESC
    """
    return query(conn, sql, (lookback_hours,))


OBR_RE = re.compile(r"^OBR\|", re.MULTILINE)


def obr_codes(raw_hl7: str | None) -> list[str]:
    """OBR-4 component 1 for every OBR segment, in message order."""
    if not raw_hl7:
        return []
    codes: list[str] = []
    for segment in re.split(r"[\r\n]+", raw_hl7):
        if not segment.startswith("OBR|"):
            continue
        fields = segment.split("|")
        if len(fields) > 4 and fields[4]:
            codes.append(fields[4].split("^")[0])
    return codes


def fetch_quarantine(conn, hl7_ids: list[int]) -> dict[int, dict[str, Any]]:
    if not hl7_ids:
        return {}
    placeholders = ",".join(["%s"] * len(hl7_ids))
    sql = f"""
        SELECT id, hl7_file_input_id, provider_npi, provider_name, patient_name,
               order_id, matched_integration_id, quarantine_reason, failure_class,
               failure_detail, status, expires_at, raw_hl7_message
        FROM quarantined_orders
        WHERE hl7_file_input_id IN ({placeholders})
        ORDER BY id
    """
    out: dict[int, dict[str, Any]] = {}
    for row in query(conn, sql, hl7_ids):
        raw = row.pop("raw_hl7_message", None)
        row["obr_codes"] = obr_codes(raw)
        row["raw_hl7_length"] = len(raw) if raw else 0
        out[int(row["hl7_file_input_id"])] = row
    return out


def integrations_by_npi(conn, npi: str) -> list[dict[str, Any]]:
    sql = f"SELECT {INTEGRATION_COLUMNS} FROM ehr_integrations WHERE customer_npi = %s OR effective_npi = %s"
    return query(conn, sql, (npi, npi))


def integrations_by_customer_id(conn, customer_id: str) -> list[dict[str, Any]]:
    sql = f"SELECT {INTEGRATION_COLUMNS} FROM ehr_integrations WHERE customer_id = %s"
    return query(conn, sql, (customer_id,))


def sftp_practice_prefix(sftp_dir: str | None) -> str | None:
    """'/plessenhealthcareemr/orders/' -> '/plessenhealthcareemr/'. The last
    path component is the orders/results leaf; the rest identifies the practice."""
    if not sftp_dir:
        return None
    parts = [p for p in sftp_dir.strip("/").split("/") if p]
    if len(parts) <= 1:
        return "/" + "/".join(parts) + "/" if parts else None
    return "/" + "/".join(parts[:-1]) + "/"


def integrations_by_sftp_dir(conn, sftp_dir: str | None) -> list[dict[str, Any]]:
    prefix = sftp_practice_prefix(sftp_dir)
    if not prefix:
        return []
    like = prefix + "%"
    sql = (
        f"SELECT {INTEGRATION_COLUMNS} FROM ehr_integrations "
        "WHERE sftp_ordering_path LIKE %s OR sftp_result_path LIKE %s"
    )
    return query(conn, sql, (like, like))
