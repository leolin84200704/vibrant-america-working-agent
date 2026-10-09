"""Per-code lookup against the pricing catalog, routed by prefix the way
emr-v2 obr-parser.service.ts / order-mapping-cache.service.ts do it.

2026-07-10 lesson: querying bundle mapping for every code misdiagnosed
VATEST codes as missing. Each prefix has its own map, and a code that exists
with isOrderable=false fails exactly like a missing one, so both the
existence and the orderable flag are reported as evidence.
"""
from __future__ import annotations

import re
from typing import Any

import requests

from .config import BUNDLE_URL, PACKAGE_PRICE_URL

# order-legacy-code-mapper.service.ts: applied before the lookup.
TEST_GROUP_ALIASES = {
    "VAREQUISTION240": "VARequisition332",
    "VAREQUISTION241": "VARequisition326",
    "VAREQUISTION242": "VARequisition327",
    "VAREQUISTION252": "VAREQUISTION330",
    "VAREQUISTION277": "VAREQUISTION331",
    "VAREQUISTION271": "VAREQUISTION260",
    "VAREQUISTION288": "VAREQUISTION302",
}
TEST_ID_ALIASES = {
    "VATEST1529": "VATEST2270",
    "VATEST1538": "VATEST2279",
}


class Catalog:
    def __init__(self, package_prices: list[dict[str, Any]], bundles: list[dict[str, Any]]):
        self.package_prices = package_prices
        self.bundles = bundles
        self.emr_code_map: dict[str, dict[str, Any]] = {}
        self.test_order_type_map: dict[int, dict[str, Any]] = {}
        self.group_order_type_map: dict[int, dict[str, Any]] = {}
        self.official_bundles: dict[int, dict[str, Any]] = {}
        self.custom_bundles: dict[int, list[dict[str, Any]]] = {}
        for pp in package_prices:
            if pp.get("type") is None:
                continue
            code = pp.get("uniqueemrcode")
            if code:
                self.emr_code_map[code.lower()] = pp
            oti = pp.get("orderTypeId")
            if pp.get("type") == "TEST" and oti is not None:
                self.test_order_type_map[int(oti)] = pp
            elif pp.get("type") == "GROUP" and oti is not None:
                self.group_order_type_map[int(oti)] = pp
        for b in bundles:
            oti = b.get("oldOrderTypeId")
            if oti is None:
                continue
            if b.get("bundleType") == "official":
                self.official_bundles[int(oti)] = b
            else:
                self.custom_bundles.setdefault(int(oti), []).append(b)

    @property
    def summary(self) -> str:
        return (f"package prices: {len(self.package_prices)}, bundles: {len(self.bundles)} "
                f"(official {len(self.official_bundles)}, custom keys {len(self.custom_bundles)})")


def _as_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [p for p in payload if isinstance(p, dict)]
    if isinstance(payload, dict):
        inner = payload.get("data") if isinstance(payload.get("data"), (list, dict)) else payload
        if isinstance(inner, list):
            return [p for p in inner if isinstance(p, dict)]
        return [v for v in inner.values() if isinstance(v, dict)]
    return []


def load_catalog(token: str, timeout: int = 30) -> Catalog:
    headers = {"Authorization": token}
    pp = requests.get(PACKAGE_PRICE_URL, headers=headers, timeout=timeout)
    pp.raise_for_status()
    bundles = requests.get(BUNDLE_URL, headers=headers, timeout=timeout)
    bundles.raise_for_status()
    return Catalog(_as_list(pp.json()), _as_list(bundles.json()))


def _pp_fields(pp: dict[str, Any]) -> dict[str, Any]:
    return {
        "pkg_id": pp.get("id"),
        "order_type_id": pp.get("orderTypeId"),
        "name": pp.get("name"),
        "pkg_type": pp.get("type"),
        "is_orderable": pp.get("isOrderable"),
        "price_va": pp.get("priceVa"),
        "price_vw": pp.get("priceVw"),
        "unique_emr_code": pp.get("uniqueemrcode"),
    }


def _bundle_fields(b: dict[str, Any]) -> dict[str, Any]:
    return {
        "bundle_id": b.get("bundleId"),
        "bundle_type": b.get("bundleType"),
        "name": b.get("bundleName"),
        "old_order_type_id": b.get("oldOrderTypeId"),
        "customer_id": b.get("customerId"),
        "clinic_id": b.get("clinicId"),
        "order_price": b.get("orderPrice"),
        "expire_time": b.get("expireTime"),
    }


def lookup_code(catalog: Catalog, code: str,
                customer_id: str | int | None, clinic_id: str | int | None) -> dict[str, Any]:
    raw = code.strip()
    out: dict[str, Any] = {"code": raw, "effective_code": raw, "kind": None,
                           "found": False, "diagnosis": None, "detail": "", "evidence": {}}
    upper = raw.upper()
    lower = raw.lower()

    if lower.startswith("discountpanel"):
        out["kind"] = "discountpanel"
        num = _int_suffix(raw[13:])
        b = catalog.official_bundles.get(num) if num is not None else None
        if b:
            out.update(found=True, diagnosis="ok", evidence=_bundle_fields(b))
        else:
            out.update(diagnosis="code_missing", detail=f"no official bundle with oldOrderTypeId={num}")
        return out

    if upper.startswith("VACP"):
        out["kind"] = "VACP"
        num = _int_suffix(raw[4:])
        official = catalog.official_bundles.get(num) if num is not None else None
        customs = catalog.custom_bundles.get(num, []) if num is not None else []
        if official:
            out.update(found=True, diagnosis="ok", evidence=_bundle_fields(official))
            return out
        if customs:
            mine = [b for b in customs
                    if _same(b.get("customerId"), customer_id) or _same(b.get("clinicId"), clinic_id)]
            if mine:
                out.update(found=True, diagnosis="ok", evidence=_bundle_fields(mine[0]))
            else:
                owners = sorted({f"customer {b.get('customerId')}/clinic {b.get('clinicId')}" for b in customs})
                out.update(found=True, diagnosis="not_assigned",
                           detail=f"custom bundle exists but is bound to {', '.join(owners)}; "
                                  f"order resolves to customer {customer_id}/clinic {clinic_id}",
                           evidence={"bound_to": [_bundle_fields(b) for b in customs[:5]]})
            return out
        out.update(diagnosis="code_missing", detail=f"no bundle with oldOrderTypeId={num} in bundle mapping")
        return out

    if len(upper) >= 6 and upper[2:6] == "REQU":
        out["kind"] = "VAREQUISTION"
        effective = TEST_GROUP_ALIASES.get(upper, raw)
        out["effective_code"] = effective
        pp = catalog.emr_code_map.get(effective.lower())
        return _finish_pp(out, pp, f"no package price with uniqueemrcode={effective}")

    if len(upper) >= 6 and upper[2:6] == "TEST":
        out["kind"] = "VATEST"
        effective = TEST_ID_ALIASES.get(upper, upper)
        out["effective_code"] = effective
        num = _int_suffix(re.sub(r"[A-Za-z]", "", effective))
        pp = catalog.test_order_type_map.get(num) if num is not None else None
        return _finish_pp(out, pp, f"no TEST package price with orderTypeId={num}")

    out["kind"] = "unknown_prefix"
    pp = catalog.emr_code_map.get(lower)
    if pp:
        return _finish_pp(out, pp, "")
    out.update(diagnosis="unknown_prefix", detail="prefix is none of VACP/VATEST/VAREQUISTION/discountpanel and no uniqueemrcode matches")
    return out


def _finish_pp(out: dict[str, Any], pp: dict[str, Any] | None, missing_detail: str) -> dict[str, Any]:
    if not pp:
        out.update(diagnosis="code_missing", detail=missing_detail)
        return out
    out["found"] = True
    out["evidence"] = _pp_fields(pp)
    if str(pp.get("isOrderable")).lower() == "true":
        out["diagnosis"] = "ok"
    else:
        out["diagnosis"] = "not_orderable"
        out["detail"] = (f"exists (id {pp.get('id')}, {pp.get('name')}) but isOrderable={pp.get('isOrderable')}, "
                         f"priceVa={pp.get('priceVa')}: catalog configuration gap, not a missing code")
    return out


def _int_suffix(text: str) -> int | None:
    m = re.match(r"\s*(\d+)", text or "")
    return int(m.group(1)) if m else None


def _same(a: Any, b: Any) -> bool:
    return a is not None and b is not None and str(a) == str(b)


def split_codes(value: str | None) -> list[str]:
    if not value:
        return []
    return [c.strip() for c in re.split(r"[,;\s]+", value) if c.strip()]
