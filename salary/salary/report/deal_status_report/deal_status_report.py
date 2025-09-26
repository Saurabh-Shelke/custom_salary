# -*- coding: utf-8 -*-
# Deal Status Report - fetch order_lost_reason from CRM (Opportunity/Lead) by crm id; robust service_category fetch
from __future__ import annotations
import frappe
from frappe.utils import flt
from typing import Any, Dict, List, Optional, Tuple

# Forced field names (highest priority)
FORCED_CRM_FIELD = "custom_crm_id_details"
FORCED_PROJECT_FIELD = "custom_project_id_55"
FORCED_DATE_FIELD = "custom_approved_date2"

# Forced monetary fields (prefer these if present)
FORCED_REVENUE_FIELD = "custom_total_inr"
FORCED_PARTNER_COST_FIELD = "custom_total_inr_1"
FORCED_TOTAL_COST_FIELD = "custom_total_cost_by_company"


def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if filters is None:
        filters = {}

    columns = get_columns()

    # fetch quotation table columns once
    try:
        qcols = frappe.db.get_table_columns("tabQuotation") or []
    except Exception:
        qcols = []

    # candidate names for friendly fields
    service_candidates = [
        "custom_service_category", "service_category", "service", "custom_service_category1", "service_category1"
    ]
    reason_candidates = ["order_lost_reason", "custom_reason", "reason", "loss_reason", "remarks"]

    def sel(colname: Optional[str], alias: str) -> str:
        return f"q.`{colname}` AS `{alias}`" if colname and colname in qcols else f"NULL AS `{alias}`"

    def pick(col_list: List[str]) -> Optional[str]:
        for c in col_list:
            if c in qcols:
                return c
        return None

    select_parts = [
        "q.name AS _qname",
        sel(FORCED_CRM_FIELD if FORCED_CRM_FIELD in qcols else None, "crm_id_sql"),
        sel(FORCED_PROJECT_FIELD if FORCED_PROJECT_FIELD in qcols else None, "project_id_sql"),
        sel(FORCED_DATE_FIELD if FORCED_DATE_FIELD in qcols else None, "date_approved_sql"),
        sel(pick(["custom_project_name", "project_name", "project"]), "project_name"),
        sel(pick(["custom_prospect_name", "prospect_name", "customer", "party_name"]), "prospect_name"),
        sel(pick(service_candidates), "service_category_sql"),
        sel(pick(["custom_sub_service_category", "sub_service_category", "sub_service"]), "sub_service_category"),
        sel(pick(["custom_city", "city", "location"]), "location"),
        sel(pick([FORCED_REVENUE_FIELD, "custom_revenue", "revenue", "grand_total"]), "revenue_sql"),
        sel(pick([FORCED_PARTNER_COST_FIELD, "partner_cost", "custom_total_inr_1"]), "partner_cost_sql"),
        sel(pick(["custom_other_costs", "other_costs"]), "other_costs"),
        sel(FORCED_TOTAL_COST_FIELD if FORCED_TOTAL_COST_FIELD in qcols else None, "total_cost_sql"),
        "NULL AS total_costs_computed",
        "NULL AS profit",
        "NULL AS profit_margin",
        sel(pick(["custom_account_manager", "account_manager", "sales_owner", "owner"]), "account_manager"),
        sel(pick(["status", "deal_status"]), "deal_status"),
        # <-- return quotation-level reason as 'reason' so report reads r.get('reason') directly
        sel(pick(reason_candidates), "reason"),
        "NULL AS actual_revenue",
        "NULL AS actual_partner_cost",
        "NULL AS revenue_difference",
        "NULL AS partner_cost_difference",
    ]

    select_sql = ",\n    ".join(select_parts)

    where = []
    vals: Dict[str, Any] = {}
    if filters.get("from_date") and FORCED_DATE_FIELD in qcols:
        where.append(f"q.`{FORCED_DATE_FIELD}` >= %(from_date)s")
        vals["from_date"] = filters["from_date"]
    if filters.get("to_date") and FORCED_DATE_FIELD in qcols:
        where.append(f"q.`{FORCED_DATE_FIELD}` <= %(to_date)s")
        vals["to_date"] = filters["to_date"]
    if filters.get("crm_id") and FORCED_CRM_FIELD in qcols:
        where.append(f"q.`{FORCED_CRM_FIELD}` = %(crm_id)s")
        vals["crm_id"] = filters["crm_id"]
    if filters.get("project_id") and FORCED_PROJECT_FIELD in qcols:
        where.append(f"q.`{FORCED_PROJECT_FIELD}` = %(project_id)s")
        vals["project_id"] = filters["project_id"]
    if filters.get("status") and "status" in qcols:
        where.append("q.`status` = %(status)s")
        vals["status"] = filters["status"]
    if filters.get("company") and "company" in qcols:
        where.append("q.`company` = %(company)s")
        vals["company"] = filters["company"]

    where_sql = "WHERE " + " AND ".join(where) if where else ""
    limit = int(filters.get("limit") or 2000)
    order_col = FORCED_DATE_FIELD if FORCED_DATE_FIELD in qcols else "name"

    query = f"""
        SELECT
            {select_sql}
        FROM `tabQuotation` q
        {where_sql}
        ORDER BY q.`{order_col}` DESC
        LIMIT %(limit)s
    """

    rows = frappe.db.sql(query, values={**vals, "limit": limit}, as_dict=True)
    if not rows:
        return columns, []

    # collect keys for bulk actuals lookup
    crm_keys: List[str] = []
    proj_keys: List[str] = []
    for r in rows:
        if r.get("crm_id_sql"):
            crm_keys.append(str(r.get("crm_id_sql")))
        if r.get("project_id_sql"):
            proj_keys.append(str(r.get("project_id_sql")))
        if r.get("project_name"):
            proj_keys.append(str(r.get("project_name")))

    crm_keys = list(dict.fromkeys([c for c in crm_keys if c]))
    proj_keys = list(dict.fromkeys([p for p in proj_keys if p]))

    # bulk actual revenue by opportunity and project_name
    actual_revenue_map: Dict[str, float] = {}
    if crm_keys:
        try:
            so_rows = frappe.db.sql(
                """
                SELECT opportunity AS key_field, SUM(grand_total) AS total
                FROM `tabSales Order`
                WHERE opportunity IN %(crm_list)s
                GROUP BY opportunity
                """,
                {"crm_list": tuple(crm_keys)},
                as_dict=True,
            )
            for s in so_rows:
                actual_revenue_map[str(s["key_field"])] = flt(s["total"])
        except Exception:
            pass

    if proj_keys:
        try:
            so_rows = frappe.db.sql(
                """
                SELECT project_name AS key_field, SUM(grand_total) AS total
                FROM `tabSales Order`
                WHERE project_name IN %(proj_list)s
                GROUP BY project_name
                """,
                {"proj_list": tuple(proj_keys)},
                as_dict=True,
            )
            for s in so_rows:
                if not actual_revenue_map.get(str(s["key_field"])):
                    actual_revenue_map[str(s["key_field"])] = flt(s["total"])
        except Exception:
            pass

    # bulk actual partner cost by project_name from Purchase Orders
    actual_partner_map: Dict[str, float] = {}
    if proj_keys:
        try:
            po_rows = frappe.db.sql(
                """
                SELECT project_name AS key_field, SUM(COALESCE(rounded_total, grand_total, 0)) AS total
                FROM `tabPurchase Order`
                WHERE project_name IN %(proj_list)s
                GROUP BY project_name
                """,
                {"proj_list": tuple(proj_keys)},
                as_dict=True,
            )
            for p in po_rows:
                actual_partner_map[str(p["key_field"])] = flt(p["total"])
        except Exception:
            pass

    out_rows: List[Dict[str, Any]] = []

    # candidate fields to try on CRM (Opportunity / Lead)
    crm_reason_candidates = ["order_lost_reason", "loss_reason", "reason", "custom_reason", "remarks"]

    for r in rows:
        qname = r.get("_qname")
        debug: List[str] = []

        # --- Resolve crm_val (opportunity id) robustly
        crm_val = r.get("crm_id_sql") or ""
        if not crm_val:
            try:
                tmp = frappe.db.get_value("Quotation", qname, FORCED_CRM_FIELD) if FORCED_CRM_FIELD in qcols else None
                crm_val = tmp or ""
                if crm_val:
                    debug.append("crm:db_get_value")
            except Exception:
                pass
        if not crm_val:
            try:
                qdoc = frappe.get_cached_doc("Quotation", qname)
                crm_val = (
                    getattr(qdoc, FORCED_CRM_FIELD, "")
                    or getattr(qdoc, "crm_id", "")
                    or getattr(qdoc, "opportunity", "")
                    or ""
                )
                if crm_val:
                    debug.append("crm:get_cached_doc")
            except Exception:
                pass
        if not crm_val:
            for alt in [c for c in qcols if "crm" in c or "opportunity" in c]:
                try:
                    tmp = frappe.db.get_value("Quotation", qname, alt)
                    if tmp:
                        crm_val = tmp
                        debug.append(f"crm:fallback:{alt}")
                        break
                except Exception:
                    continue
        if crm_val and not any(d.startswith("crm:") for d in debug):
            debug.append("crm:sql_or_direct")

        # --- Resolve project/date similar to prior logic
        proj_val = r.get("project_id_sql") or ""
        if not proj_val:
            try:
                tmp = frappe.db.get_value("Quotation", qname, FORCED_PROJECT_FIELD) if FORCED_PROJECT_FIELD in qcols else None
                proj_val = tmp or ""
                if proj_val:
                    debug.append("proj:db_get_value")
            except Exception:
                pass
        if not proj_val:
            try:
                qdoc = frappe.get_cached_doc("Quotation", qname)
                proj_val = getattr(qdoc, FORCED_PROJECT_FIELD, "") or getattr(qdoc, "project", "") or getattr(qdoc, "project_id", "") or ""
                if proj_val:
                    debug.append("proj:get_cached_doc")
            except Exception:
                pass
        if not proj_val:
            for alt in [c for c in qcols if "project" in c or "project_id" in c]:
                try:
                    tmp = frappe.db.get_value("Quotation", qname, alt)
                    if tmp:
                        proj_val = tmp
                        debug.append(f"proj:fallback:{alt}")
                        break
                except Exception:
                    continue
        if proj_val and not any(d.startswith("proj:") for d in debug):
            debug.append("proj:sql_or_direct")

        date_val = r.get("date_approved_sql") or ""
        if not date_val:
            try:
                tmp = frappe.db.get_value("Quotation", qname, FORCED_DATE_FIELD) if FORCED_DATE_FIELD in qcols else None
                date_val = tmp or ""
                if date_val:
                    debug.append("date:db_get_value")
            except Exception:
                pass
        if not date_val:
            try:
                qdoc = frappe.get_cached_doc("Quotation", qname)
                date_val = getattr(qdoc, FORCED_DATE_FIELD, "") or getattr(qdoc, "transaction_date", "") or getattr(qdoc, "date", "") or ""
                if date_val:
                    debug.append("date:get_cached_doc")
            except Exception:
                pass
        if not date_val:
            for alt in [c for c in qcols if "approve" in c or "approved" in c or "approved_date" in c]:
                try:
                    tmp = frappe.db.get_value("Quotation", qname, alt)
                    if tmp:
                        date_val = tmp
                        debug.append(f"date:fallback:{alt}")
                        break
                except Exception:
                    continue
        if date_val and not any(d.startswith("date:") for d in debug):
            debug.append("date:sql_or_direct")

        # --- Service category: prefer SQL select -> quotation fields -> linked lead/opportunity
        svc = r.get("service_category_sql") or ""
        if not svc:
            # try quotation-level fields
            for f in service_candidates:
                try:
                    v = frappe.db.get_value("Quotation", qname, f)
                except Exception:
                    v = None
                if v:
                    svc = v
                    debug.append(f"svc:quote_db:{f}")
                    break
        if not svc:
            try:
                qdoc = frappe.get_cached_doc("Quotation", qname)
                for f in service_candidates:
                    v = getattr(qdoc, f, None)
                    if v:
                        svc = v
                        debug.append(f"svc:quote_cached:{f}")
                        break
            except Exception:
                pass
        if not svc:
            # try linked Lead then Opportunity
            try:
                qdoc = frappe.get_cached_doc("Quotation", qname)
                lead_name = getattr(qdoc, "lead", None)
                if lead_name:
                    for f in service_candidates:
                        try:
                            v = frappe.db.get_value("Lead", lead_name, f)
                        except Exception:
                            v = None
                        if v:
                            svc = v
                            debug.append(f"svc:lead:{f}")
                            break
                if not svc:
                    opp_name = getattr(qdoc, "opportunity", None)
                    if opp_name:
                        for f in service_candidates:
                            try:
                                v = frappe.db.get_value("Opportunity", opp_name, f)
                            except Exception:
                                v = None
                            if v:
                                svc = v
                                debug.append(f"svc:opportunity:{f}")
                                break
            except Exception:
                pass

        # --- Revenue/partner/total cost (kept similar)
        revenue_val = flt(r.get("revenue_sql") or 0)
        if revenue_val == 0 and FORCED_REVENUE_FIELD in qcols:
            try:
                tmp = frappe.db.get_value("Quotation", qname, FORCED_REVENUE_FIELD)
                if tmp:
                    revenue_val = flt(tmp)
                    debug.append("revenue:db_get_value_forced")
            except Exception:
                pass
        if revenue_val == 0:
            try:
                qdoc = frappe.get_cached_doc("Quotation", qname)
                tmp = getattr(qdoc, FORCED_REVENUE_FIELD, None) or getattr(qdoc, "custom_total_inr", None) or getattr(qdoc, "grand_total", None)
                if tmp:
                    revenue_val = flt(tmp)
                    debug.append("revenue:get_cached_doc")
            except Exception:
                pass

        partner_cost_val = flt(r.get("partner_cost_sql") or 0)
        if partner_cost_val == 0 and FORCED_PARTNER_COST_FIELD in qcols:
            try:
                tmp = frappe.db.get_value("Quotation", qname, FORCED_PARTNER_COST_FIELD)
                if tmp:
                    partner_cost_val = flt(tmp)
                    debug.append("partner:db_get_value_forced")
            except Exception:
                pass
        if partner_cost_val == 0:
            try:
                qdoc = frappe.get_cached_doc("Quotation", qname)
                tmp = getattr(qdoc, FORCED_PARTNER_COST_FIELD, None) or getattr(qdoc, "custom_total_inr_1", None)
                if tmp:
                    partner_cost_val = flt(tmp)
                    debug.append("partner:get_cached_doc")
            except Exception:
                pass

        total_cost_val = flt(r.get("total_cost_sql") or 0)
        if total_cost_val == 0 and FORCED_TOTAL_COST_FIELD in qcols:
            try:
                tmp = frappe.db.get_value("Quotation", qname, FORCED_TOTAL_COST_FIELD)
                if tmp:
                    total_cost_val = flt(tmp)
                    debug.append("total_cost:db_get_value_forced")
            except Exception:
                pass
        if total_cost_val == 0:
            try:
                qdoc = frappe.get_cached_doc("Quotation", qname)
                tmp = getattr(qdoc, FORCED_TOTAL_COST_FIELD, None) or getattr(qdoc, "custom_total_cost_by_company", None)
                if tmp:
                    total_cost_val = flt(tmp)
                    debug.append("total_cost:get_cached_doc")
            except Exception:
                pass

        other_costs_val = flt(r.get("other_costs") or 0)
        if total_cost_val == 0:
            total_cost_val = partner_cost_val + other_costs_val

        # --- Resolve reason: priority -> CRM (Opportunity/Lead via crm_val) -> Quotation fields -> fuzzy
        # Accept either column name returned by SQL: 'reason' (preferred) or 'reason_sql' (if present)
        reason_val = (r.get("reason") or r.get("reason_sql") or "")  # defensive: accept either alias

        # If crm_val exists, try Opportunity then Lead fields for order_lost_reason/loss_reason/reason
        if crm_val and not reason_val:
            # try Opportunity by name = crm_val
            try:
                if frappe.db.exists("Opportunity", crm_val):
                    for fld in crm_reason_candidates:
                        try:
                            tmp = frappe.db.get_value("Opportunity", crm_val, fld)
                        except Exception:
                            tmp = None
                        if tmp:
                            reason_val = tmp
                            debug.append(f"reason:opportunity:{fld}")
                            break
            except Exception:
                pass

            # try Lead by name = crm_val (if not found)
            if not reason_val:
                try:
                    if frappe.db.exists("Lead", crm_val):
                        for fld in crm_reason_candidates:
                            try:
                                tmp = frappe.db.get_value("Lead", crm_val, fld)
                            except Exception:
                                tmp = None
                            if tmp:
                                reason_val = tmp
                                debug.append(f"reason:lead:{fld}")
                                break
                except Exception:
                    pass

        # If still not found, try quotation-level fields (db.get_value + cached)
        if not reason_val:
            try:
                tmp = (
                    frappe.db.get_value("Quotation", qname, "order_lost_reason")
                    or frappe.db.get_value("Quotation", qname, "custom_reason")
                    or frappe.db.get_value("Quotation", qname, "reason")
                )
                if tmp:
                    reason_val = tmp
                    debug.append("reason:quote_db_fields")
            except Exception:
                pass
        if not reason_val:
            try:
                qdoc = frappe.get_cached_doc("Quotation", qname)
                reason_val = reason_val or getattr(qdoc, "order_lost_reason", "") or getattr(qdoc, "custom_reason", "") or getattr(qdoc, "reason", "") or ""
                if reason_val:
                    debug.append("reason:quote_cached")
            except Exception:
                pass
        # last-ditch: fuzzy scan columns with 'lost' or 'reason'
        if not reason_val:
            for alt in [c for c in qcols if "lost" in c or "reason" in c]:
                try:
                    tmp = frappe.db.get_value("Quotation", qname, alt)
                    if tmp:
                        reason_val = tmp
                        debug.append(f"reason:fuzzy:{alt}")
                        break
                except Exception:
                    continue

        # fill human-friendly names if missing
        project_name = r.get("project_name") or ""
        prospect_name = r.get("prospect_name") or ""
        sub_service_category = r.get("sub_service_category") or ""
        location = r.get("location") or ""
        try:
            if (not project_name) or (not prospect_name) or (not location) or (not svc):
                qdoc = frappe.get_cached_doc("Quotation", qname)
                project_name = project_name or getattr(qdoc, "custom_project_name", "") or getattr(qdoc, "project_name", "") or getattr(qdoc, "project", "") or project_name
                prospect_name = prospect_name or getattr(qdoc, "custom_prospect_name", "") or getattr(qdoc, "prospect_name", "") or getattr(qdoc, "customer", "") or getattr(qdoc, "party_name", "") or prospect_name
                location = location or getattr(qdoc, "custom_city", "") or getattr(qdoc, "custom_location", "") or getattr(qdoc, "city", "") or getattr(qdoc, "location", "") or getattr(qdoc, "territory", "") or getattr(qdoc, "region", "") or location
                svc = svc or getattr(qdoc, "custom_service_category", "") or getattr(qdoc, "service_category", "") or getattr(qdoc, "service", "") or svc
        except Exception:
            pass

        # account manager & status fallback
        account_manager = r.get("account_manager") or ""
        deal_status = r.get("deal_status") or ""
        if not account_manager or not deal_status:
            try:
                qdoc = frappe.get_cached_doc("Quotation", qname)
                if not account_manager:
                    account_manager = getattr(qdoc, "owner", "") or getattr(qdoc, "sales_owner", "") or account_manager
                if not deal_status:
                    deal_status = getattr(qdoc, "status", "") or deal_status
            except Exception:
                pass

        profit = revenue_val - total_cost_val
        profit_margin = f"{(profit / revenue_val * 100):.2f}%" if revenue_val > 0 else ""

        # actuals from maps (prefer crm then project)
        actual_rev = None
        if crm_val and str(crm_val) in actual_revenue_map:
            actual_rev = actual_revenue_map.get(str(crm_val))
        elif proj_val and str(proj_val) in actual_revenue_map:
            actual_rev = actual_revenue_map.get(str(proj_val))

        actual_partner = None
        if proj_val and str(proj_val) in actual_partner_map:
            actual_partner = actual_partner_map.get(str(proj_val))
        elif crm_val and str(crm_val) in actual_partner_map:
            actual_partner = actual_partner_map.get(str(crm_val))

        revenue_diff = flt(revenue_val - flt(actual_rev)) if actual_rev is not None else ""
        partner_cost_diff = flt(partner_cost_val - flt(actual_partner)) if actual_partner is not None else ""

        out_rows.append(
            {
                "crm_id": crm_val or "",
                "project_id": proj_val or "",
                "date_approved": date_val or "",
                "project_name": project_name or "",
                "prospect_name": prospect_name or "",
                "service_category": svc or "",
                "sub_service_category": sub_service_category or "",
                "location": location or "",
                "revenue": flt(revenue_val, 2),
                "partner_cost": flt(partner_cost_val, 2),
                "other_costs": flt(other_costs_val, 2),
                "total_costs": flt(total_cost_val, 2),
                "profit": flt(profit, 2),
                "profit_margin": profit_margin,
                "account_manager": account_manager,
                "deal_status": deal_status,
                # reason: prefer CRM (Opportunity/Lead) -> Quotation -> fuzzy
                "reason": reason_val or "",
                "actual_revenue": flt(actual_rev, 2) if actual_rev is not None else "",
                "actual_partner_cost": flt(actual_partner, 2) if actual_partner is not None else "",
                "revenue_difference": revenue_diff,
                "partner_cost_difference": partner_cost_diff,
                "debug_note": ";".join([p for p in debug if p]),
            }
        )

    return columns, out_rows


def get_columns() -> List[Dict[str, Any]]:
    cols = [
        {"fieldname": "crm_id", "label": "CRM ID", "fieldtype": "Data", "width": 150},
        {"fieldname": "project_id", "label": "Project ID", "fieldtype": "Data", "width": 150},
        {"fieldname": "date_approved", "label": "Date Approved", "fieldtype": "Date", "width": 110},
        {"fieldname": "project_name", "label": "Project Name", "fieldtype": "Data", "width": 220},
        {"fieldname": "prospect_name", "label": "Prospect Name", "fieldtype": "Data", "width": 160},
        {"fieldname": "service_category", "label": "Service Category", "fieldtype": "Data", "width": 140},
        {"fieldname": "sub_service_category", "label": "Sub-service Category", "fieldtype": "Data", "width": 160},
        {"fieldname": "location", "label": "Location", "fieldtype": "Data", "width": 120},
        {"fieldname": "revenue", "label": "Revenue", "fieldtype": "Currency", "width": 120},
        {"fieldname": "partner_cost", "label": "Partner Cost", "fieldtype": "Currency", "width": 120},
        {"fieldname": "other_costs", "label": "Other Costs", "fieldtype": "Currency", "width": 120},
        {"fieldname": "total_costs", "label": "Total Costs", "fieldtype": "Currency", "width": 120},
        {"fieldname": "profit", "label": "Profit", "fieldtype": "Currency", "width": 120},
        {"fieldname": "profit_margin", "label": "Profit Margin", "fieldtype": "Data", "width": 100},
        {"fieldname": "account_manager", "label": "Account Manager", "fieldtype": "Data", "width": 160},
        {"fieldname": "deal_status", "label": "Deal Status", "fieldtype": "Data", "width": 120},
        {"fieldname": "reason", "label": "Reason", "fieldtype": "Data", "width": 180},
        {"fieldname": "actual_revenue", "label": "Actual Revenue", "fieldtype": "Currency", "width": 140},
        {"fieldname": "actual_partner_cost", "label": "Actual Partner Cost", "fieldtype": "Currency", "width": 160},
        {"fieldname": "revenue_difference", "label": "Revenue Difference", "fieldtype": "Currency", "width": 150},
        {"fieldname": "partner_cost_difference", "label": "Partner Cost Difference", "fieldtype": "Currency", "width": 170},
    ]
    cols.append({"fieldname": "debug_note", "label": "debug_note", "fieldtype": "Data", "width": 250})
    return cols
