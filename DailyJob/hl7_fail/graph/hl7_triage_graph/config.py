"""Runtime configuration.

Secrets come from the agent root's .env (never committed) or, for the pricing
API token, from EMR-Backend's orderApi.yaml. Nothing here is exported into
os.environ: the LLM node spawns `claude -p` with a scrubbed environment and
.env carries ANTHROPIC_* values for a different proxy that must not leak into
that process (ticket_watch trial run 2026-09-30).
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
# graph/ -> hl7_fail/ -> DailyJob/ -> agent root
AGENT_ROOT = PACKAGE_DIR.parents[3]
MAIN_CHECKOUT = Path("/Users/hung.l/src/vibrant-america-working-agent")
ORDER_API_YAML = Path("/Users/hung.l/src/EMR-Backend/src/main/resources/dependencies/orderApi.yaml")

PACKAGE_PRICE_URL = "https://api.vibrant-wellness.com/v1/pricing/item/price/getLegacyPackagePriceMapping?currency=usd"
BUNDLE_URL = "https://api.vibrant-wellness.com/v1/pricing/item/promotion/getLegacyBundleMapping?currency=usd"

DEFAULT_LOOKBACK_HOURS = 72
DEFAULT_MODEL = "fable"


def load_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def find_env_file() -> Path:
    override = os.environ.get("HL7_TRIAGE_ENV_FILE")
    if override:
        return Path(override)
    for candidate in (AGENT_ROOT / ".env", MAIN_CHECKOUT / ".env"):
        if candidate.exists():
            return candidate
    return AGENT_ROOT / ".env"


def pricing_token_from_yaml(path: Path = ORDER_API_YAML) -> str | None:
    if not path.exists():
        return None
    text = path.read_text()
    m = re.search(r"orderApiToken:\s*\n(?:.*\n)*?\s*prod:\s*(Bearer \S+)", text)
    return m.group(1) if m else None


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_user: str
    db_password: str
    db_name: str
    pricing_token: str | None
    model: str
    out_dir: Path
    env_file: Path

    @property
    def db_configured(self) -> bool:
        return bool(self.db_password)


def load_settings(out_dir: Path | None = None) -> Settings:
    env_file = find_env_file()
    env = load_env_file(env_file)
    token = env.get("PRICING_API_TOKEN") or pricing_token_from_yaml()
    return Settings(
        db_host=env.get("LIS_EMR_DB_HOST", "lisportalprod2.mysql.database.azure.com"),
        db_port=int(env.get("LIS_EMR_DB_PORT", "3306")),
        db_user=env.get("LIS_EMR_DB_USER", "lis_core_emr"),
        db_password=env.get("LIS_EMR_DB_PASSWORD", ""),
        db_name=env.get("LIS_EMR_DB_NAME", "lis_emr"),
        pricing_token=token,
        model=os.environ.get("HL7_TRIAGE_MODEL") or env.get("HL7_TRIAGE_MODEL") or DEFAULT_MODEL,
        out_dir=out_dir or AGENT_ROOT / "DailyJob" / "hl7_fail",
        env_file=env_file,
    )
