# -*- coding: utf-8 -*-
# Deal Status Report - robust Deal resolution including custom_productservice_for_planning for order_lost_reason
# Actual Revenue from Sales Order.grand_total via child filter (Sales Order Item.prevdoc_docname = Quotation)
# Actual Partner Cost from Purchase Order.grand_total via:
#   A) Purchase Order.custom_sales_order IN <SO IDs>
#   B) Purchase Order Item.sales_order IN <SO IDs>
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

# Purchase Order header field that stores Sales Order link
PO_SO_HEADER_FIELD = "custom_sales_order"


def resolve_deal_from_crm(crm_val: str) -> Optional[str]:
    if not crm_val:
        return None
    crm_val = crm_val.strip()
    try:
        if frappe.db.exists("Deal", crm_val):
            return crm_val
        res = frappe.db.sql(
            """
            SELECT name FROM tabDeal
            WHERE (lead = %s OR opportunity = %s OR custom_crm_id_details = %s)
            LIMIT 1
            """,
            (crm_val, crm_val, crm_val),
            as_dict=True,
        )
        if res:
            return res[0]["name"]

        if frappe.db.exists("Lead", crm_val) or frappe.db.exists("Opportunity", crm_val):
            res = frappe.db.sql(
                """
                SELECT name FROM tabDeal
                WHERE lead = %s OR opportunity = %s
                LIMIT 1
                """,
                (crm_val, crm_val),
                as_dict=True,
            )
            if res:
                return res[0]["name"]
        return None
    except Exception:
        return None


def execute(filters: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if filters is None:
        filters = {}

    columns = get_columns()

    # fetch table columns once
    try:
        qcols = frappe.db.get_table_columns("tabQuotation") or []
    except Exception:
        qcols = []
    try:
        ocols = frappe.db.get_table_columns("tabOpportunity") or []
    except Exception:
        ocols = []

    # fields list (kept for gentle fallbacks only)
    service_candidates_primary = ["custom_service_category"]
    service_candidates_fallback = ["service_category", "service", "custom_service_category1", "service_category1"]

    # subservice fields (used for fallback only)
    subservice_field_pool = [
        "custom_productservice_for_planning",
        "custom_productservice_for_design",
        "custom_productservice_for_implementation",
        "custom_productservice_for_audit__compliance",
        "custom_productservice_for_epc",
        "custom_sub_service_category",
        "sub_service_category",
        "sub_service",
    ]
    reason_candidates = ["order_lost_reason", "loss_reason", "reason", "custom_reason", "remarks"]

    def sel(colname: Optional[str], alias: str, table_alias: str = "q") -> str:
        if colname and (
            (table_alias == "q" and colname in qcols) or (table_alias == "o" and colname in ocols)
        ):
            return f"{table_alias}.{colname} AS {alias}"
        return f"NULL AS {alias}"

    def pick(col_list: List[str], table_alias: str = "q") -> Optional[str]:
        cols = qcols if table_alias == "q" else ocols
        for c in col_list:
            if c in cols:
                return c
        return None

    # ------------------ SERVICE CATEGORY & SUB-SERVICE (SQL FIRST) ------------------
    # Build a COALESCE(service) expression that prefers Quotation's custom_service_category, then Opportunity's.
    service_exists_q = "custom_service_category" in qcols
    service_exists_o = "custom_service_category" in ocols
    if service_exists_q and service_exists_o:
        base_service_expr_sql = "COALESCE(q.custom_service_category, o.custom_service_category)"
    elif service_exists_q:
        base_service_expr_sql = "q.custom_service_category"
    elif service_exists_o:
        base_service_expr_sql = "o.custom_service_category"
    else:
        q_fb = pick(service_candidates_fallback, "q")
        o_fb = pick(service_candidates_fallback, "o")
        if q_fb and o_fb:
            base_service_expr_sql = f"COALESCE(q.{q_fb}, o.{o_fb})"
        elif q_fb:
            base_service_expr_sql = f"q.{q_fb}"
        elif o_fb:
            base_service_expr_sql = f"o.{o_fb}"
        else:
            base_service_expr_sql = "NULL"

    def both_side(field_q: str, field_o: str) -> str:
        has_q = field_q in qcols
        has_o = field_o in ocols
        if has_q and has_o:
            return f"COALESCE(q.{field_q}, o.{field_o})"
        elif has_q:
            return f"q.{field_q}"
        elif has_o:
            return f"o.{field_o}"
        return "NULL"

    def nonempty(expr: str) -> str:
        # returns SQL that is NULL if expr is '' or NULL; non-NULL otherwise
        return f"NULLIF(TRIM({expr}), '')"

    sub_planning    = both_side("custom_productservice_for_planning", "custom_productservice_for_planning")
    sub_design      = both_side("custom_productservice_for_design", "custom_productservice_for_design")
    sub_impl        = both_side("custom_productservice_for_implementation", "custom_productservice_for_implementation")
    sub_audit       = both_side("custom_productservice_for_audit__compliance", "custom_productservice_for_audit__compliance")
    sub_epc         = both_side("custom_productservice_for_epc", "custom_productservice_for_epc")

    # If service category missing, infer from whichever sub-service has data
    inferred_service_from_subs = f"""
        CASE
            WHEN {nonempty(sub_planning)} IS NOT NULL THEN 'Planning'
            WHEN {nonempty(sub_design)}   IS NOT NULL THEN 'Design'
            WHEN {nonempty(sub_impl)}     IS NOT NULL THEN 'Implementation'
            WHEN {nonempty(sub_audit)}    IS NOT NULL THEN 'Audit & Compliance'
            WHEN {nonempty(sub_epc)}      IS NOT NULL THEN 'EPC'
            ELSE NULL
        END
    """

    # Final service expression used everywhere in SQL
    service_expr_sql = f"COALESCE({base_service_expr_sql}, {inferred_service_from_subs})"

    subservice_case_sql = f"""
        CASE
            WHEN {service_expr_sql} = 'Planning'           THEN {sub_planning}
            WHEN {service_expr_sql} = 'Design'             THEN {sub_design}
            WHEN {service_expr_sql} = 'Implementation'     THEN {sub_impl}
            WHEN {service_expr_sql} = 'Audit & Compliance' THEN {sub_audit}
            WHEN {service_expr_sql} = 'EPC'                THEN {sub_epc}
            ELSE NULL
        END AS sub_service_category_sql
    """

    # ------------------ SELECT PARTS ------------------
    select_parts = [
        "q.name AS _qname",
        sel(FORCED_CRM_FIELD if FORCED_CRM_FIELD in qcols else None, "crm_id_sql", "q"),
        sel(FORCED_PROJECT_FIELD if FORCED_PROJECT_FIELD in qcols else None, "project_id_sql", "q"),
        sel(FORCED_DATE_FIELD if FORCED_DATE_FIELD in qcols else None, "date_approved_sql", "q"),
        sel(pick(["custom_project_name", "project_name", "project"], "q"), "project_name", "q"),
        sel(pick(["custom_prospect_name", "prospect_name", "customer", "party_name"], "q"), "prospect_name", "q"),

        # Service category (now infers from sub-service when blank)
        f"{service_expr_sql} AS service_category_sql",

        # Sub-service derived via CASE with COALESCE(q.*, o.*)
        subservice_case_sql,

        sel(pick(["custom_city", "city", "location"], "q"), "location", "q"),
        sel(pick([FORCED_REVENUE_FIELD, "custom_revenue", "revenue", "grand_total"], "q"), "revenue_sql", "q"),
        sel(pick([FORCED_PARTNER_COST_FIELD, "partner_cost", "custom_total_inr_1"], "q"), "partner_cost_sql", "q"),
        sel(pick(["custom_other_costs", "other_costs"], "q"), "other_costs", "q"),
        sel(FORCED_TOTAL_COST_FIELD if FORCED_TOTAL_COST_FIELD in qcols else None, "total_cost_sql", "q"),
        "NULL AS total_costs_computed",
        "NULL AS profit",
        "NULL AS profit_margin",
        sel(pick(["custom_account_manager", "account_manager", "sales_owner", "owner"], "q"), "account_manager", "q"),
        sel(pick(["status", "deal_status"], "q"), "deal_status", "q"),
        sel(pick(reason_candidates, "q"), "reason", "q"),
        "NULL AS actual_revenue",
        "NULL AS actual_partner_cost",
        "NULL AS revenue_difference",
        "NULL AS partner_cost_difference",
    ]
    select_sql = ",\n ".join(select_parts)

    # ------------------ WHERE / FILTERS ------------------
    where = []
    vals: Dict[str, Any] = {}
    if filters.get("from_date") and FORCED_DATE_FIELD in qcols:
        where.append(f"q.{FORCED_DATE_FIELD} >= %(from_date)s")
        vals["from_date"] = filters["from_date"]
    if filters.get("to_date") and FORCED_DATE_FIELD in qcols:
        where.append(f"q.{FORCED_DATE_FIELD} <= %(to_date)s")
        vals["to_date"] = filters["to_date"]
    if filters.get("crm_id") and FORCED_CRM_FIELD in qcols:
        where.append(f"q.{FORCED_CRM_FIELD} = %(crm_id)s")
        vals["crm_id"] = filters["crm_id"]
    if filters.get("project_id") and FORCED_PROJECT_FIELD in qcols:
        where.append(f"q.{FORCED_PROJECT_FIELD} = %(project_id)s")
        vals["project_id"] = filters["project_id"]
    if filters.get("status") and "status" in qcols:
        where.append("q.status = %(status)s")
        vals["status"] = filters["status"]
    if filters.get("company") and "company" in qcols:
        where.append("q.company = %(company)s")
        vals["company"] = filters["company"]

    where_sql = "WHERE " + " AND ".join(where) if where else ""
    limit = int(filters.get("limit") or 2000)
    order_col = FORCED_DATE_FIELD if FORCED_DATE_FIELD in qcols else "name"

    # ------------------ MAIN QUERY (JOIN OPPORTUNITY) ------------------
    query = f"""
        SELECT {select_sql}
        FROM tabQuotation q
        LEFT JOIN tabOpportunity o
               ON o.name = q.opportunity
        {where_sql}
        ORDER BY q.{order_col} DESC
        LIMIT %(limit)s
    """
    rows = frappe.db.sql(query, values={**vals, "limit": limit}, as_dict=True)
    if not rows:
        return columns, []

    out_rows: List[Dict[str, Any]] = []
    crm_reason_candidates = ["order_lost_reason", "loss_reason", "reason", "custom_reason", "remarks"]

    for r in rows:
        qname = r.get("_qname")
        debug: List[str] = []

        # --- Resolve crm/project/date ---
        crm_val = (r.get("crm_id_sql") or "").strip()
        if not crm_val:
            try:
                tmp = frappe.db.get_value("Quotation", qname, FORCED_CRM_FIELD) if FORCED_CRM_FIELD in qcols else None
                crm_val = (tmp or "").strip()
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
                ).strip()
                if crm_val:
                    debug.append("crm:get_cached_doc")
            except Exception:
                pass
        if not crm_val:
            for alt in [c for c in qcols if "crm" in c or "opportunity" in c]:
                try:
                    tmp = frappe.db.get_value("Quotation", qname, alt)
                    if tmp:
                        crm_val = tmp.strip()
                        debug.append(f"crm:fallback:{alt}")
                        break
                except Exception:
                    continue
        if crm_val and not any(d.startswith("crm:") for d in debug):
            debug.append("crm:sql_or_direct")

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

        # --- SERVICE CATEGORY (SQL-FIRST; if still blank, infer from sub-service fields) ---
        svc = r.get("service_category_sql") or ""
        if not svc:
            # 1) strictly try custom_service_category on Quotation, then Opportunity, then generic fallbacks
            if "custom_service_category" in qcols:
                try:
                    tmp = frappe.db.get_value("Quotation", qname, "custom_service_category")
                    if tmp:
                        svc = tmp
                        debug.append("svc:q.custom_service_category_db")
                except Exception:
                    pass
            if not svc and "custom_service_category" in ocols:
                try:
                    opp_name = frappe.db.get_value("Quotation", qname, "opportunity")
                    if opp_name:
                        tmp = frappe.db.get_value("Opportunity", opp_name, "custom_service_category")
                        if tmp:
                            svc = tmp
                            debug.append("svc:o.custom_service_category_db")
                except Exception:
                    pass
            if not svc:
                for f in service_candidates_fallback:
                    try:
                        v = frappe.db.get_value("Quotation", qname, f)
                        if v:
                            svc = v
                            debug.append(f"svc:q.fallback_db:{f}")
                            break
                    except Exception:
                        continue

            # 2) still blank? infer from sub-service fields (Quotation then Opportunity)
            if not svc:
                try:
                    qdoc_local = frappe.get_cached_doc("Quotation", qname)
                except Exception:
                    qdoc_local = None
                if qdoc_local:
                    if getattr(qdoc_local, "custom_productservice_for_planning", None):
                        svc = "Planning"
                    elif getattr(qdoc_local, "custom_productservice_for_design", None):
                        svc = "Design"
                    elif getattr(qdoc_local, "custom_productservice_for_implementation", None):
                        svc = "Implementation"
                    elif getattr(qdoc_local, "custom_productservice_for_audit__compliance", None):
                        svc = "Audit & Compliance"
                    elif getattr(qdoc_local, "custom_productservice_for_epc", None):
                        svc = "EPC"
                    if svc:
                        debug.append("svc:inferred_from_q_subservice")

            if not svc:
                try:
                    opp_name = frappe.db.get_value("Quotation", qname, "opportunity")
                    if opp_name:
                        # Check Opportunity sub-service fields
                        fields = [
                            ("custom_productservice_for_planning", "Planning"),
                            ("custom_productservice_for_design", "Design"),
                            ("custom_productservice_for_implementation", "Implementation"),
                            ("custom_productservice_for_audit__compliance", "Audit & Compliance"),
                            ("custom_productservice_for_epc", "EPC"),
                        ]
                        for f, label in fields:
                            try:
                                v = frappe.db.get_value("Opportunity", opp_name, f)
                            except Exception:
                                v = None
                            if v:
                                svc = label
                                debug.append("svc:inferred_from_o_subservice")
                                break
                except Exception:
                    pass

        # --- SUB-SERVICE (SQL CASE preferred; gentle fallbacks if blank) ---
        sub_service_category = r.get("sub_service_category_sql") or ""
        if not sub_service_category:
            # gentle fallback to common subservice fields on Quotation
            try:
                qdoc_local = frappe.get_cached_doc("Quotation", qname)
            except Exception:
                qdoc_local = None
            if qdoc_local:
                for f in subservice_field_pool:
                    v = getattr(qdoc_local, f, None)
                    if v:
                        sub_service_category = v
                        debug.append(f"subsvc:qdoc_fallback:{f}")
                        break
            if not sub_service_category:
                for f in subservice_field_pool:
                    try:
                        v = frappe.db.get_value("Quotation", qname, f)
                    except Exception:
                        v = None
                    if v:
                        sub_service_category = v
                        debug.append(f"subsvc:q.db_fallback:{f}")
                        break
        # If still blank, try Opportunity side for common subservice fields
        if not sub_service_category:
            try:
                opp_name = frappe.db.get_value("Quotation", qname, "opportunity")
                if opp_name:
                    for f in subservice_field_pool:
                        try:
                            v = frappe.db.get_value("Opportunity", opp_name, f)
                        except Exception:
                            v = None
                        if v:
                            sub_service_category = v
                            debug.append(f"subsvc:o.db_fallback:{f}")
                            break
            except Exception:
                pass

        # --- Monetary & other fields ---
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

        reason_val = (r.get("reason") or r.get("reason_sql") or "")

        deal_name = None
        if crm_val:
            try:
                deal_name = resolve_deal_from_crm(crm_val)
                if deal_name:
                    debug.append(f"deal_resolved:{deal_name}")
            except Exception:
                deal_name = None

        if not deal_name:
            try:
                prospect_val = ""
                proj_val2 = ""
                qdoc = None
                try:
                    qdoc = frappe.get_cached_doc("Quotation", qname)
                except Exception:
                    qdoc = None

                if qdoc:
                    prospect_val = (
                        getattr(qdoc, "custom_prospect_name", "")
                        or getattr(qdoc, "prospect_name", "")
                        or getattr(qdoc, "customer", "")
                        or ""
                    ).strip()
                    proj_val2 = (
                        getattr(qdoc, "custom_project_name", "")
                        or getattr(qdoc, "project_name", "")
                        or getattr(qdoc, "project", "")
                        or ""
                    ).strip()

                subsvc_for_match = (sub_service_category or "").strip()
                if subsvc_for_match or prospect_val or proj_val2:
                    res = frappe.db.sql(
                        """
                        SELECT name, order_lost_reason
                        FROM tabDeal
                        WHERE
                          (COALESCE(custom_productservice_for_planning, '') = %s
                           OR COALESCE(sub_service_category, '') = %s
                           OR COALESCE(service, '') = %s)
                          OR (COALESCE(prospect_name, '') = %s OR COALESCE(customer, '') = %s)
                          OR (COALESCE(project_name, '') = %s)
                        LIMIT 1
                        """,
                        (subsvc_for_match, subsvc_for_match, subsvc_for_match, prospect_val, prospect_val, proj_val2),
                        as_dict=True,
                    )
                    if res:
                        deal_name = res[0]["name"]
                        if res[0].get("order_lost_reason"):
                            reason_val = res[0]["order_lost_reason"]
                            debug.append(f"reason:deal_matched_by_subsvc_or_prospect:{deal_name}")
                        else:
                            debug.append(f"deal_matched_by_subsvc_or_prospect_no_reason:{deal_name}")
            except Exception:
                pass

        if deal_name and not reason_val:
            try:
                tmp = frappe.db.get_value("Deal", deal_name, "order_lost_reason")
                if tmp:
                    reason_val = tmp
                    debug.append("reason:deal:order_lost_reason")
                else:
                    for fld in ["order_lost_reason", "loss_reason", "reason", "custom_reason", "remarks"]:
                        try:
                            tmp = frappe.db.get_value("Deal", deal_name, fld)
                        except Exception:
                            tmp = None
                        if tmp:
                            reason_val = tmp
                            debug.append(f"reason:deal:{fld}")
                            break
            except Exception:
                pass

        if not reason_val and crm_val:
            try:
                if frappe.db.exists("Opportunity", crm_val):
                    for fld in ["order_lost_reason", "loss_reason", "reason", "custom_reason", "remarks"]:
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

        if not reason_val:
            try:
                if frappe.db.exists("Lead", crm_val):
                    for fld in ["order_lost_reason", "loss_reason", "reason", "custom_reason", "remarks"]:
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

        # --------- Final row ---------
        project_name = r.get("project_name") or ""
        prospect_name = r.get("prospect_name") or ""
        location = r.get("location") or ""

        try:
            if (not project_name) or (not prospect_name) or (not location):
                qdoc = frappe.get_cached_doc("Quotation", qname)
                project_name = project_name or getattr(qdoc, "custom_project_name", "") or getattr(qdoc, "project_name", "") or getattr(qdoc, "project", "") or project_name
                prospect_name = prospect_name or getattr(qdoc, "custom_prospect_name", "") or getattr(qdoc, "prospect_name", "") or getattr(qdoc, "customer", "") or getattr(qdoc, "party_name", "") or prospect_name
                location = location or getattr(qdoc, "custom_city", "") or getattr(qdoc, "custom_location", "") or getattr(qdoc, "city", "") or getattr(qdoc, "location", "") or getattr(qdoc, "territory", "") or getattr(qdoc, "region", "") or location
        except Exception:
            pass

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

        # ------------------ ACTUAL REVENUE ------------------
        actual_rev = None
        so_list: List[Dict[str, Any]] = []
        try:
            so_list = frappe.get_all(
                "Sales Order",
                filters=[
                    ["Sales Order Item", "prevdoc_docname", "=", qname],
                    ["docstatus", "<", 2],
                ],
                fields=["name", "grand_total"],
                order_by="transaction_date desc",
                distinct=True,
            )
            if so_list:
                actual_rev = sum(flt(so.get("grand_total") or 0) for so in so_list)
                debug.append(f"actual_rev:so_by_child_prevdoc={actual_rev}")
            else:
                debug.append("actual_rev:so_by_child_prevdoc:none")
        except Exception:
            actual_rev = None

        # Fallbacks for revenue
        if (actual_rev is None or actual_rev == 0) and (crm_val or proj_val):
            try:
                if crm_val:
                    so = frappe.db.sql(
                        """
                        SELECT SUM(grand_total) AS total
                        FROM `tabSales Order`
                        WHERE opportunity = %s
                        """,
                        (crm_val,),
                        as_dict=True,
                    )
                    if so and so[0].get("total") is not None:
                        actual_rev = flt(so[0]["total"])
                        debug.append(f"actual_rev:so_by_opportunity={actual_rev}")

                if (actual_rev is None or actual_rev == 0) and proj_val:
                    so = frappe.db.sql(
                        """
                        SELECT SUM(grand_total) AS total
                        FROM `tabSales Order`
                        WHERE project_name = %s
                        """,
                        (proj_val,),
                        as_dict=True,
                    )
                    if so and so[0].get("total") is not None:
                        actual_rev = flt(so[0]["total"])
                        debug.append(f"actual_rev:so_by_project={actual_rev}")
            except Exception:
                pass

        # ------------------ ACTUAL PARTNER COST (robust) ------------------
        actual_partner = None
        try:
            so_names = [s["name"] for s in so_list] if so_list else []
            if so_names:
                po_name_set = set()

                # A) POs linked via header: custom_sales_order IN so_names
                in_clause = ", ".join(["%s"] * len(so_names))
                po_hdr = frappe.db.sql(
                    f"""
                    SELECT name
                    FROM `tabPurchase Order`
                    WHERE docstatus < 2 AND {PO_SO_HEADER_FIELD} IN ({in_clause})
                    """,
                    tuple(so_names),
                    as_dict=True,
                ) or []
                for row in po_hdr:
                    po_name_set.add(row["name"])

                # B) POs linked via child table: Purchase Order Item.sales_order IN so_names
                poi_parents = frappe.get_all(
                    "Purchase Order Item",
                    filters=[["sales_order", "in", so_names]],
                    pluck="parent",
                    distinct=True,
                ) or []
                for p in poi_parents:
                    po_name_set.add(p)

                if po_name_set:
                    po_names = list(po_name_set)
                    in_clause2 = ", ".join(["%s"] * len(po_names))
                    po_sum = frappe.db.sql(
                        f"""
                        SELECT SUM(grand_total) AS total
                        FROM `tabPurchase Order`
                        WHERE docstatus < 2 AND name IN ({in_clause2})
                        """,
                        tuple(po_names),
                        as_dict=True,
                    )
                    total_val = po_sum[0]["total"] if (po_sum and po_sum[0] and po_sum[0].get("total") is not None) else 0
                    actual_partner = flt(total_val)
                    debug.append(f"actual_partner:sum_po:{actual_partner}")
                else:
                    actual_partner = 0.0
                    debug.append("actual_partner:no_po_links")
            else:
                debug.append("actual_partner:no_so_ids_from_actual_revenue")
        except Exception as e:
            actual_partner = None
            debug.append(f"actual_partner:error:{str(e)}")

        # Fallbacks: try quotation/project/opportunity
        if (actual_partner is None or actual_partner == 0):
            try:
                po = frappe.db.sql(
                    """
                    SELECT SUM(grand_total) AS total
                    FROM `tabPurchase Order`
                    WHERE quotation = %s
                    """,
                    (qname,),
                    as_dict=True,
                )
                if po and ("total" in po[0]) and (po[0]["total"] is not None) and flt(po[0]["total"]) > 0:
                    actual_partner = flt(po[0]["total"])
                    debug.append(f"actual_partner:po_by_quotation_fallback={actual_partner}")
                elif proj_val:
                    po = frappe.db.sql(
                        """
                        SELECT SUM(grand_total) AS total
                        FROM `tabPurchase Order`
                        WHERE project_name = %s
                        """,
                        (proj_val,),
                        as_dict=True,
                    )
                    if po and ("total" in po[0]) and (po[0]["total"] is not None) and flt(po[0]["total"]) > 0:
                        actual_partner = flt(po[0]["total"])
                        debug.append(f"actual_partner:po_by_project_fallback={actual_partner}")
                elif crm_val:
                    po = frappe.db.sql(
                        """
                        SELECT SUM(grand_total) AS total
                        FROM `tabPurchase Order`
                        WHERE opportunity = %s
                        """,
                        (crm_val,),
                        as_dict=True,
                    )
                    if po and ("total" in po[0]) and (po[0]["total"] is not None) and flt(po[0]["total"]) > 0:
                        actual_partner = flt(po[0]["total"])
                        debug.append(f"actual_partner:po_by_opportunity_fallback={actual_partner}")
            except Exception:
                pass

        # --------------------------------
        profit = revenue_val - total_cost_val
        profit_margin = f"{(profit / revenue_val * 100):.2f}%" if revenue_val > 0 else ""
        revenue_diff = flt(revenue_val - flt(actual_rev)) if actual_rev is not None else ""
        partner_cost_diff = flt(partner_cost_val - flt(actual_partner)) if actual_partner is not None else ""

        out_rows.append(
            {
                "crm_id": crm_val or "",
                "project_id": proj_val or "",
                "date_approved": date_val or "",
                "project_name": project_name or "",
                "prospect_name": prospect_name or "",
                "service_category": (svc or ""),
                "sub_service_category": (sub_service_category or ""),
                "location": location or "",
                "revenue": flt(revenue_val, 2),
                "partner_cost": flt(partner_cost_val, 2),
                "other_costs": flt(other_costs_val, 2),
                "total_costs": flt(total_cost_val, 2),
                "profit": flt(profit, 2),
                "profit_margin": profit_margin,
                "account_manager": account_manager,
                "deal_status": deal_status,
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
    return cols
