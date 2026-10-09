#!/usr/bin/env python3
"""Headless reply assistant (Phase 1, drafts only).

Deterministic shell around one optional LLM call:
  1. poll Slack (user token) and Outlook (Graph, delegated token) for new items
  2. nothing new -> exit 0 without touching the model (zero LLM cost)
  3. otherwise hand the candidates, with thread/mail context, to ONE `claude -p`
     worker constrained by --json-schema, then perform the only two outbound
     actions allowed in this phase: a Slack DM to Leo and an Outlook *draft*.

The claude.ai Slack / Microsoft 365 connectors are session-bound and do not
exist here, so this script talks to the Slack Web API and Microsoft Graph
directly with tokens from the agent root .env (never committed).
"""
from __future__ import annotations

import datetime as dt
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

ASSIST_DIR = Path(__file__).resolve().parent
AGENT_ROOT = ASSIST_DIR.parents[1]
MAIN_CHECKOUT = Path("/Users/hung.l/src/vibrant-america-working-agent")
LEO_SLACK_ID = "U08FFVDEMNK"
BOT_SENDERS = {"jira", "bug_incident_bot", "assist", "github", "datadog"}
MAIL_SKIP_SENDERS = ("noreply", "no-reply", "notifications@", "jira@", "github.com", "datadoghq.com", "sentry.io")
GRAPH = "https://graph.microsoft.com/v1.0"
GRAPH_CLIENT_ID = "14d82eec-204b-4c2f-b7e8-296a70dab67e"  # Microsoft Graph Command Line Tools (public client)
GRAPH_SCOPES = ["Mail.Read", "Mail.ReadWrite"]


# --- env / ledger -------------------------------------------------------------

def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for candidate in (AGENT_ROOT / ".env", MAIN_CHECKOUT / ".env"):
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            break
    return env


def ledger_path() -> Path:
    return ASSIST_DIR / "ledger.json"


def load_ledger() -> dict:
    p = ledger_path()
    if p.exists():
        return json.loads(p.read_text())
    now = dt.datetime.now(dt.timezone.utc)
    return {"last_slack_ts": f"{int(now.timestamp())}.000000", "last_mail_check": now.isoformat(timespec="seconds"),
            "summary_sent_date": None, "handled": {}}


def save_ledger(d: dict) -> None:
    ledger_path().write_text(json.dumps(d, ensure_ascii=False, indent=1))


def log(line: str) -> None:
    today = dt.date.today().isoformat()
    stamp = dt.datetime.now().strftime("%H:%M")
    with open(ASSIST_DIR / f"log_{today}.md", "a") as f:
        f.write(f"[{stamp}] {line}\n")
    print(f"[{stamp}] {line}")


# --- Slack (user token: acts as Leo, same reach as the connector) --------------

def slack_api(token: str, method: str, params: dict | None = None, post: dict | None = None) -> dict:
    url = f"https://slack.com/api/{method}"
    if post is not None:
        req = urllib.request.Request(url, data=json.dumps(post).encode(), method="POST",
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"})
    else:
        req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params or {}),
                                     headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if not data.get("ok"):
        raise RuntimeError(f"slack {method}: {data.get('error')}")
    return data


def slack_new_items(token: str, last_ts: str, handled: dict) -> list[dict]:
    since = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    queries = [f"<@{LEO_SLACK_ID}> after:{since}", f"is:dm after:{since}", f"is:mpim after:{since}"]
    seen: dict[str, dict] = {}
    for q in queries:
        try:
            data = slack_api(token, "search.messages", {"query": q, "sort": "timestamp", "sort_dir": "desc", "count": 20})
        except RuntimeError as exc:
            log(f"slack search failed: {exc}")
            continue
        for m in data.get("messages", {}).get("matches", []):
            ts = m.get("ts", "0")
            ch = (m.get("channel") or {}).get("id", "")
            key = f"slack:{ch}:{ts}"
            user = m.get("user") or ""
            uname = (m.get("username") or "").lower()
            if float(ts) <= float(last_ts) or key in handled or user == LEO_SLACK_ID or uname in BOT_SENDERS or m.get("subtype") == "bot_message":
                continue
            seen[key] = {"key": key, "source": "slack", "channel": ch, "ts": ts, "thread_ts": m.get("thread_ts") or ts,
                         "author": m.get("username") or user, "text": m.get("text", ""), "permalink": m.get("permalink", "")}
    items = list(seen.values())
    for it in items:  # thread or recent DM context, newest last
        try:
            if it["thread_ts"] != it["ts"] or True:
                hist = slack_api(token, "conversations.replies", {"channel": it["channel"], "ts": it["thread_ts"], "limit": 15})
                it["context"] = [{"user": x.get("user"), "text": x.get("text", "")} for x in hist.get("messages", [])][-15:]
        except RuntimeError:
            try:
                hist = slack_api(token, "conversations.history", {"channel": it["channel"], "limit": 12})
                it["context"] = [{"user": x.get("user"), "text": x.get("text", "")} for x in reversed(hist.get("messages", []))]
            except RuntimeError as exc:
                it["context"] = [{"user": None, "text": f"(context unavailable: {exc})"}]
    return items


def slack_dm_leo(token: str, text: str) -> str:
    data = slack_api(token, "chat.postMessage", post={"channel": LEO_SLACK_ID, "text": text})
    return data.get("ts", "")


# --- Outlook (Graph, delegated token via msal cache) ---------------------------

def graph_token(env: dict) -> str | None:
    cache_file = Path(env.get("MS_GRAPH_TOKEN_CACHE", str(Path.home() / ".config/support-assist/msal_cache.json")))
    if not cache_file.exists():
        return None
    try:
        import msal  # type: ignore
    except ImportError:
        log("msal not installed in the venv; Outlook skipped")
        return None
    cache = msal.SerializableTokenCache()
    cache.deserialize(cache_file.read_text())
    app = msal.PublicClientApplication(GRAPH_CLIENT_ID, authority="https://login.microsoftonline.com/organizations", token_cache=cache)
    accounts = app.get_accounts()
    if not accounts:
        return None
    result = app.acquire_token_silent(GRAPH_SCOPES, account=accounts[0])
    if cache.has_state_changed:
        cache_file.write_text(cache.serialize())
    return (result or {}).get("access_token")


def graph_get(token: str, path: str) -> dict:
    req = urllib.request.Request(GRAPH + path, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def graph_post(token: str, path: str, body: dict | None, method: str = "POST") -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(GRAPH + path, data=data, method=method,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
    return json.loads(raw) if raw else {}


def strip_html(s: str) -> str:
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", s, flags=re.S | re.I)
    t = re.sub(r"<br\s*/?>|</p>|</div>|</tr>|</li>", "\n", t, flags=re.I)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    t = re.sub(r"[ \t\xa0]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()


def mail_new_items(token: str, since_iso: str, handled: dict, me: str) -> list[dict]:
    q = urllib.parse.urlencode({"$filter": f"receivedDateTime ge {since_iso}", "$orderby": "receivedDateTime desc", "$top": "25",
                                "$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,bodyPreview,conversationId,webLink"})
    data = graph_get(token, f"/me/mailFolders/inbox/messages?{q}")
    items = []
    for m in data.get("value", []):
        key = f"mail:{m['id']}"
        sender = ((m.get("from") or {}).get("emailAddress") or {}).get("address", "").lower()
        if key in handled or sender == me.lower() or any(s in sender for s in MAIL_SKIP_SENDERS):
            continue
        full = graph_get(token, f"/me/messages/{m['id']}?$select=body")
        body = strip_html((full.get("body") or {}).get("content", ""))
        items.append({"key": key, "source": "mail", "message_id": m["id"], "subject": m.get("subject", ""), "sender": sender,
                      "received": m.get("receivedDateTime"), "web_link": m.get("webLink"),
                      "to": [x["emailAddress"]["address"] for x in m.get("toRecipients", [])],
                      "cc": [x["emailAddress"]["address"] for x in m.get("ccRecipients", [])],
                      "body": body[:6000]})
    return items


def mail_create_reply_draft(token: str, message_id: str, html_body: str) -> str:
    draft = graph_post(token, f"/me/messages/{message_id}/createReply", {})
    draft_id = draft["id"]
    existing = (draft.get("body") or {}).get("content", "")
    graph_post(token, f"/me/messages/{draft_id}", {"body": {"contentType": "html", "content": html_body + existing}}, method="PATCH")
    return draft_id


# --- worker --------------------------------------------------------------------

WORKER_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "class": {"type": "string", "enum": ["A", "B", "skip"]},
                "skip_reason": {"type": "string"},
                "diagnosis": {"type": "string"},
                "evidence": {"type": "string"},
                "draft": {"type": "string"},
                "draft_html": {"type": "string"},
                "needs_decision": {"type": "string"},
            },
            "required": ["key", "class", "skip_reason", "diagnosis", "evidence", "draft", "draft_html", "needs_decision"],
            "additionalProperties": False,
        }}
    },
    "required": ["items"],
    "additionalProperties": False,
}

ALLOWED_TOOLS = "Read,Grep,Glob,Bash,mcp__vibrant__lookup_sample_id,mcp__vibrant__lookup_accession_id,mcp__vibrant__lisportal_mysql_query,mcp__vibrant__search_jira_issues,mcp__vibrant__get_jira_issue"


def run_worker(candidates: list[dict], env: dict) -> dict:
    prompt = (ASSIST_DIR / "worker_prompt.md").read_text() + "\n\nCANDIDATES (JSON):\n" + json.dumps(candidates, ensure_ascii=False, indent=1)
    model = env.get("ASSIST_MODEL") or os.environ.get("ASSIST_MODEL") or "fable"
    penv = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC_")}
    penv["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    penv["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + penv.get("PATH", "")
    cmd = ["claude", "-p", "--model", model, "--output-format", "json", "--json-schema", json.dumps(WORKER_SCHEMA),
           "--allowedTools", ALLOWED_TOOLS, "--max-turns", str(int(env.get("ASSIST_MAX_TURNS", "25")))]
    proc = subprocess.run(cmd, input=prompt, cwd=str(AGENT_ROOT), env=penv, capture_output=True, text=True, timeout=1500)
    if proc.returncode != 0:
        raise RuntimeError(f"claude -p exit {proc.returncode}: {proc.stderr[:400] or proc.stdout[:400]}")
    envelope = json.loads(proc.stdout)
    cost = envelope.get("total_cost_usd")
    out = envelope.get("structured_output") or {}
    out["_cost_list_usd"] = cost
    out["_turns"] = envelope.get("num_turns")
    return out


# --- main ----------------------------------------------------------------------

def in_window(now: dt.datetime) -> bool:
    return now.weekday() < 5 and 9 <= now.hour < 18


def main() -> int:
    env = load_env()
    now = dt.datetime.now()
    if not in_window(now) and "--force" not in sys.argv:
        print("outside Mon-Fri 09:00-18:00 window; nothing to do")
        return 0
    slack_token = env.get("SLACK_USER_TOKEN")
    gtoken = graph_token(env)
    if not slack_token and not gtoken:
        log("no SLACK_USER_TOKEN and no Graph token cache; see README (exit 2)")
        return 2
    ledger = load_ledger()
    handled = ledger["handled"]
    candidates: list[dict] = []
    newest_slack_ts = ledger["last_slack_ts"]
    if slack_token:
        try:
            items = slack_new_items(slack_token, ledger["last_slack_ts"], handled)
            candidates += items
            for it in items:
                newest_slack_ts = max(newest_slack_ts, it["ts"], key=float)
        except Exception as exc:  # noqa: BLE001
            log(f"slack intake failed: {exc!r}")
    me = env.get("ASSIST_MAIL_ME", "hung.l@zymebalanz.com")
    mail_check = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    if gtoken:
        try:
            candidates += mail_new_items(gtoken, ledger["last_mail_check"], handled, me)
        except Exception as exc:  # noqa: BLE001
            log(f"mail intake failed: {exc!r}")
    if not candidates:
        ledger["last_slack_ts"] = newest_slack_ts
        ledger["last_mail_check"] = mail_check
        save_ledger(ledger)
        log("slack:0/0 mail:0/0 (no LLM call)")
        return 0
    try:
        result = run_worker(candidates, env)
    except Exception as exc:  # noqa: BLE001
        log(f"worker failed: {exc!r}; {len(candidates)} candidates left unhandled for next run")
        return 3
    drafted = 0
    by_key = {c["key"]: c for c in candidates}
    for it in result.get("items", []):
        c = by_key.get(it["key"])
        if not c:
            continue
        entry = {"status": "skipped", "class": it["class"], "created": mail_check, "source": c["source"]}
        if it["class"] == "skip":
            entry["skip_reason"] = it["skip_reason"]
        else:
            where = c.get("permalink") or c.get("web_link") or c.get("subject", "")
            dm = (f"[assist] {it['class']} {c.get('author') or c.get('sender')} — {where}\n"
                  f"Diagnosis: {it['diagnosis']}\nEvidence: {it['evidence']}\n"
                  + (f"Needs your decision: {it['needs_decision']}\n" if it["needs_decision"] else "")
                  + f"Draft:\n> {it['draft']}")
            if c["source"] == "mail" and gtoken and it.get("draft_html"):
                try:
                    entry["outlook_draft_id"] = mail_create_reply_draft(gtoken, c["message_id"], it["draft_html"])
                    dm += "\nOutlook draft created in Drafts"
                except Exception as exc:  # noqa: BLE001
                    dm += f"\n(Outlook draft failed: {exc!r})"
            if slack_token:
                try:
                    entry["dm_ts"] = slack_dm_leo(slack_token, dm)
                except Exception as exc:  # noqa: BLE001
                    log(f"DM to Leo failed: {exc!r}")
            entry.update(status="drafted", draft=it["draft"], diagnosis=it["diagnosis"])
            drafted += 1
        handled[c["key"]] = entry
    ledger["last_slack_ts"] = newest_slack_ts
    ledger["last_mail_check"] = mail_check
    save_ledger(ledger)
    log(f"slack:{sum(c['source']=='slack' for c in candidates)}/{drafted} mail:{sum(c['source']=='mail' for c in candidates)} "
        f"worker turns={result.get('_turns')} list-cost=${result.get('_cost_list_usd')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
