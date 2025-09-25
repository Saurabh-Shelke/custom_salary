# # Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# # License: GNU General Public License v3. See license.txt


# import frappe
# from frappe import _
# from frappe.utils import flt

# import erpnext

# salary_slip = frappe.qb.DocType("Salary Slip")
# salary_detail = frappe.qb.DocType("Salary Detail")
# salary_component = frappe.qb.DocType("Salary Component")


# def execute(filters=None):
# 	if not filters:
# 		filters = {}

# 	currency = None
# 	if filters.get("currency"):
# 		currency = filters.get("currency")
# 	company_currency = erpnext.get_company_currency(filters.get("company"))

# 	salary_slips = get_salary_slips(filters, company_currency)
# 	if not salary_slips:
# 		return [], []

# 	earning_types, ded_types = get_earning_and_deduction_types(salary_slips)
# 	columns = get_columns(earning_types, ded_types)

# 	ss_earning_map = get_salary_slip_details(salary_slips, currency, company_currency, "earnings")
# 	ss_ded_map = get_salary_slip_details(salary_slips, currency, company_currency, "deductions")

# 	doj_map = get_employee_doj_map()

# 	data = []
# 	for ss in salary_slips:
# 		row = {
# 			"salary_slip_id": ss.name,
# 			"employee": ss.employee,
# 			"employee_name": ss.employee_name,
# 			"bank_beneficiary_id": frappe.db.get_value("Employee", ss.employee, "bank_ac_no"),
# 			"data_of_joining": doj_map.get(ss.employee),
# 			"branch": ss.branch,
# 			"department": ss.department,
# 			"designation": ss.designation,
# 			"company": ss.company,
# 			"start_date": ss.start_date,
# 			"end_date": ss.end_date,
# 			"leave_without_pay": ss.leave_without_pay,
# 			"absent_days": ss.absent_days,
# 			"payment_days": ss.payment_days,
# 			"currency": currency or company_currency,
# 			"total_loan_repayment": ss.total_loan_repayment,
# 		}

# 		update_column_width(ss, columns)

# 		for e in earning_types:
# 			row.update({frappe.scrub(e): ss_earning_map.get(ss.name, {}).get(e)})

# 		for d in ded_types:
# 			row.update({frappe.scrub(d): ss_ded_map.get(ss.name, {}).get(d)})

# 		if currency == company_currency:
# 			row.update(
# 				{
# 					"gross_pay": flt(ss.gross_pay) * flt(ss.exchange_rate),
# 					"total_deduction": flt(ss.total_deduction) * flt(ss.exchange_rate),
# 					"net_pay": flt(ss.net_pay) * flt(ss.exchange_rate),
# 				}
# 			)

# 		else:
# 			row.update(
# 				{"gross_pay": ss.gross_pay, "total_deduction": ss.total_deduction, "net_pay": ss.net_pay}
# 			)

# 		data.append(row)

# 	# === Add Total Row ===
# 	totals_row = {
#     "salary_slip_id": "Total",
#     "is_total_row": 1
# }

# 	total_fields = [
# 		"leave_without_pay",
# 		"absent_days",
# 		"payment_days",
# 		"gross_pay",
# 		"total_loan_repayment",
# 		"total_deduction",
# 		"net_pay",
# 	]

# 	# Include earnings and deduction fields
# 	earning_fields = [frappe.scrub(e) for e in earning_types]
# 	deduction_fields = [frappe.scrub(d) for d in ded_types]
# 	total_fields.extend(earning_fields)
# 	total_fields.extend(deduction_fields)

# 	for field in total_fields:
# 		totals_row[field] = 0.0

# 	for row in data:
# 		for field in total_fields:
# 			totals_row[field] += flt(row.get(field))

# 	data.append(totals_row)	

# 	return columns, data


# def get_earning_and_deduction_types(salary_slips):
# 	salary_component_and_type = {_("Earning"): [], _("Deduction"): []}

# 	for salary_component in get_salary_components(salary_slips):
# 		component_type = get_salary_component_type(salary_component)
# 		salary_component_and_type[_(component_type)].append(salary_component)

# 	return sorted(salary_component_and_type[_("Earning")]), sorted(salary_component_and_type[_("Deduction")])


# def update_column_width(ss, columns):
# 	if ss.branch is not None:
# 		columns[3].update({"width": 120})
# 	if ss.department is not None:
# 		columns[4].update({"width": 120})
# 	if ss.designation is not None:
# 		columns[5].update({"width": 120})
# 	if ss.leave_without_pay is not None:
# 		columns[9].update({"width": 120})


# def get_columns(earning_types, ded_types):
# 	columns = [
# 		{
# 			"label": _("Salary Slip ID"),
# 			"fieldname": "salary_slip_id",
# 			"fieldtype": "Link",
# 			"options": "Salary Slip",
# 			"width": 150,
# 		},
# 		{
# 			"label": _("Employee"),
# 			"fieldname": "employee",
# 			"fieldtype": "Link",
# 			"options": "Employee",
# 			"width": 120,
# 		},
# 		{
# 			"label": _("Employee Name"),
# 			"fieldname": "employee_name",
# 			"fieldtype": "Data",
# 			"width": 180,
# 		},
# 		{
# 	"label": _("Bank Beneficiary ID"),
# 	"fieldname": "bank_beneficiary_id",
# 	"fieldtype": "Data",
# 	"width": 180,
# },
# 		{
# 			"label": _("Date of Joining"),
# 			"fieldname": "data_of_joining",
# 			"fieldtype": "Date",
# 			"width": 180,
# 		},
# 		{
# 			"label": _("Branch"),
# 			"fieldname": "branch",
# 			"fieldtype": "Link",
# 			"options": "Branch",
# 			"width": 140,
# 		},
# 		{
# 			"label": _("Department"),
# 			"fieldname": "department",
# 			"fieldtype": "Link",
# 			"options": "Department",
# 			"width": 140,
# 		},
# 		{
# 			"label": _("Designation"),
# 			"fieldname": "designation",
# 			"fieldtype": "Link",
# 			"options": "Designation",
# 			"width": 120,
# 		},
# 		{
# 			"label": _("Company"),
# 			"fieldname": "company",
# 			"fieldtype": "Link",
# 			"options": "Company",
# 			"width": 120,
# 		},
# 		{
# 			"label": _("Start Date"),
# 			"fieldname": "start_date",
# 			"fieldtype": "Data",
# 			"width": 80,
# 		},
# 		{
# 			"label": _("End Date"),
# 			"fieldname": "end_date",
# 			"fieldtype": "Data",
# 			"width": 180,
# 		},
# 		{
# 			"label": _("Leave Without Pay"),
# 			"fieldname": "leave_without_pay",
# 			"fieldtype": "Float",
# 			"width": 150,
# 		},
# 		{
# 			"label": _("Absent Days"),
# 			"fieldname": "absent_days",
# 			"fieldtype": "Float",
# 			"width": 150,
# 		},
# 		{
# 			"label": _("Payment Days"),
# 			"fieldname": "payment_days",
# 			"fieldtype": "Float",
# 			"width": 120,
# 		},
# 	]

# 	for earning in earning_types:
# 		columns.append(
# 			{
# 				"label": earning,
# 				"fieldname": frappe.scrub(earning),
# 				"fieldtype": "Currency",
# 				"options": "currency",
# 				"width": 120,
# 			}
# 		)

# 	columns.append(
# 		{
# 			"label": _("Gross Pay"),
# 			"fieldname": "gross_pay",
# 			"fieldtype": "Currency",
# 			"options": "currency",
# 			"width": 120,
# 		}
# 	)

# 	for deduction in ded_types:
# 		columns.append(
# 			{
# 				"label": deduction,
# 				"fieldname": frappe.scrub(deduction),
# 				"fieldtype": "Currency",
# 				"options": "currency",
# 				"width": 120,
# 			}
# 		)

# 	columns.extend(
# 		[
# 			{
# 				"label": _("Loan Repayment"),
# 				"fieldname": "total_loan_repayment",
# 				"fieldtype": "Currency",
# 				"options": "currency",
# 				"width": 140,
# 			},
# 			{
# 				"label": _("Total Deduction"),
# 				"fieldname": "total_deduction",
# 				"fieldtype": "Currency",
# 				"options": "currency",
# 				"width": 140,
# 			},
# 			{
# 				"label": _("Net Pay"),
# 				"fieldname": "net_pay",
# 				"fieldtype": "Currency",
# 				"options": "currency",
# 				"width": 120,
# 			},
			
# 			{
# 				"label": _("Currency"),
# 				"fieldtype": "Data",
# 				"fieldname": "currency",
# 				"options": "Currency",
# 				"hidden": 1,
# 			},
# 		]
# 	)

# 	columns.append({
#     "label": "Is Total Row",
#     "fieldname": "is_total_row",
#     "fieldtype": "Check",
#     "hidden": 1
#      })
	
# 	return columns


# def get_salary_components(salary_slips):
# 	return (
# 		frappe.qb.from_(salary_detail)
# 		.where((salary_detail.amount != 0) & (salary_detail.parent.isin([d.name for d in salary_slips])))
# 		.select(salary_detail.salary_component)
# 		.distinct()
# 	).run(pluck=True)


# def get_salary_component_type(salary_component):
# 	return frappe.db.get_value("Salary Component", salary_component, "type", cache=True)


# def get_salary_slips(filters, company_currency):
# 	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

# 	query = frappe.qb.from_(salary_slip).select(salary_slip.star)

# 	if filters.get("docstatus"):
# 		query = query.where(salary_slip.docstatus == doc_status[filters.get("docstatus")])

# 	if filters.get("from_date"):
# 		query = query.where(salary_slip.start_date >= filters.get("from_date"))

# 	if filters.get("to_date"):
# 		query = query.where(salary_slip.end_date <= filters.get("to_date"))

# 	if filters.get("company"):
# 		query = query.where(salary_slip.company == filters.get("company"))

# 	if filters.get("employee"):
# 		query = query.where(salary_slip.employee == filters.get("employee"))

# 	if filters.get("currency") and filters.get("currency") != company_currency:
# 		query = query.where(salary_slip.currency == filters.get("currency"))

# 	if filters.get("department"):
# 		query = query.where(salary_slip.department == filters["department"])

# 	if filters.get("designation"):
# 		query = query.where(salary_slip.designation == filters["designation"])

# 	if filters.get("branch"):
# 		query = query.where(salary_slip.branch == filters["branch"])

# 	salary_slips = query.run(as_dict=1)

# 	return salary_slips or []


# def get_employee_doj_map():
# 	employee = frappe.qb.DocType("Employee")

# 	result = (frappe.qb.from_(employee).select(employee.name, employee.date_of_joining)).run()

# 	return frappe._dict(result)


# def get_salary_slip_details(salary_slips, currency, company_currency, component_type):
# 	salary_slips = [ss.name for ss in salary_slips]

# 	result = (
# 		frappe.qb.from_(salary_slip)
# 		.join(salary_detail)
# 		.on(salary_slip.name == salary_detail.parent)
# 		.where((salary_detail.parent.isin(salary_slips)) & (salary_detail.parentfield == component_type))
# 		.select(
# 			salary_detail.parent,
# 			salary_detail.salary_component,
# 			salary_detail.amount,
# 			salary_slip.exchange_rate,
# 		)
# 	).run(as_dict=1)

# 	ss_map = {}

# 	for d in result:
# 		ss_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, 0.0)
# 		if currency == company_currency:
# 			ss_map[d.parent][d.salary_component] += flt(d.amount) * flt(
# 				d.exchange_rate if d.exchange_rate else 1
# 			)
# 		else:
# 			ss_map[d.parent][d.salary_component] += flt(d.amount)

# 	return ss_map



# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt








# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# import frappe
# from frappe import _
# from frappe.utils import flt

# import erpnext

# salary_slip = frappe.qb.DocType("Salary Slip")
# salary_detail = frappe.qb.DocType("Salary Detail")
# salary_component = frappe.qb.DocType("Salary Component")


# def execute(filters=None):
# 	if not filters:
# 		filters = {}

# 	# requested report currency (None means use company currency)
# 	currency = filters.get("currency")
# 	company_currency = erpnext.get_company_currency(filters.get("company"))

# 	# Choose report_currency for columns/options display
# 	report_currency = currency or company_currency

# 	salary_slips = get_salary_slips(filters, company_currency)
# 	if not salary_slips:
# 		return [], []

# 	# Get raw component lists (component names as stored)
# 	earning_types, ded_types = get_earning_and_deduction_types(salary_slips)

# 	# Build unique fieldname mapping for each salary component to avoid collisions
# 	component_field_map = build_unique_component_field_map(earning_types + ded_types)

# 	# Build columns using the unique fieldnames
# 	columns = get_columns(earning_types, ded_types, report_currency, component_field_map)

# 	# Build maps of earnings and deductions (converted if needed)
# 	ss_earning_map = get_salary_slip_details(salary_slips, currency, company_currency, "earnings")
# 	ss_ded_map = get_salary_slip_details(salary_slips, currency, company_currency, "deductions")

# 	doj_map = get_employee_doj_map()

# 	data = []
# 	for ss in salary_slips:
# 		row = {
# 			"salary_slip_id": ss.name,
# 			"employee": ss.employee,
# 			"employee_name": ss.employee_name,
# 			"bank_beneficiary_id": frappe.db.get_value("Employee", ss.employee, "bank_ac_no"),
# 			"data_of_joining": doj_map.get(ss.employee),
# 			"branch": ss.branch,
# 			"department": ss.department,
# 			"designation": ss.designation,
# 			"company": ss.company,
# 			"start_date": ss.start_date,
# 			"end_date": ss.end_date,
# 			"leave_without_pay": ss.leave_without_pay,
# 			"absent_days": ss.absent_days,
# 			"payment_days": ss.payment_days,
# 			"currency": report_currency,
# 			"total_loan_repayment": ss.total_loan_repayment,
# 		}

# 		# Update widths based on present values (safer: find by fieldname)
# 		update_column_width(ss, columns)

# 		# Add earnings & deductions from maps (use unique fieldnames from component_field_map)
# 		for e in earning_types:
# 			fieldname = component_field_map[e]
# 			# Use the component name (e) to fetch the amount from ss_earning_map
# 			row[fieldname] = flt(ss_earning_map.get(ss.name, {}).get(e))

# 		for d in ded_types:
# 			fieldname = component_field_map[d]
# 			row[fieldname] = flt(ss_ded_map.get(ss.name, {}).get(d))

# 		# Convert summary fields only when user requested a different currency than company currency.
# 		if currency and currency != company_currency:
# 			# note: exchange_rate is expected to convert stored (company currency) amounts to requested currency.
# 			rate = flt(ss.exchange_rate or 1)
# 			row.update(
# 				{
# 					"gross_pay": flt(ss.gross_pay) * rate,
# 					"total_deduction": flt(ss.total_deduction) * rate,
# 					"net_pay": flt(ss.net_pay) * rate,
# 				}
# 			)
# 		else:
# 			row.update(
# 				{
# 					"gross_pay": flt(ss.gross_pay),
# 					"total_deduction": flt(ss.total_deduction),
# 					"net_pay": flt(ss.net_pay),
# 				}
# 			)

# 		data.append(row)

# 	# === Add Total Row ===
# 	totals_row = {
# 		"salary_slip_id": "Total",
# 		"is_total_row": 1,
# 	}

# 	# Base total fields
# 	total_fields = [
# 		"leave_without_pay",
# 		"absent_days",
# 		"payment_days",
# 		"gross_pay",
# 		"total_loan_repayment",
# 		"total_deduction",
# 		"net_pay",
# 	]

# 	# Include earnings and deduction fields (using the unique fieldnames)
# 	earning_fields = [component_field_map[e] for e in earning_types]
# 	deduction_fields = [component_field_map[d] for d in ded_types]
# 	total_fields.extend(earning_fields)
# 	total_fields.extend(deduction_fields)

# 	# Initialize totals
# 	for field in total_fields:
# 		totals_row[field] = 0.0

# 	# Sum rows
# 	for row in data:
# 		for field in total_fields:
# 			totals_row[field] += flt(row.get(field))

# 	# Append totals row
# 	data.append(totals_row)

# 	return columns, data


# def build_unique_component_field_map(components):
# 	"""
# 	Given a list of component names, return a dict mapping:
# 	   { component_name -> unique_fieldname }
# 	Ensures that scrubbed fieldnames are unique by appending _1, _2... when collisions occur.
# 	"""
# 	field_map = {}
# 	used = set()

# 	for comp in components:
# 		base = frappe.scrub(comp)
# 		fieldname = base
# 		counter = 1
# 		while fieldname in used:
# 			fieldname = f"{base}_{counter}"
# 			counter += 1
# 		used.add(fieldname)
# 		field_map[comp] = fieldname

# 	return field_map


# def get_earning_and_deduction_types(salary_slips):
# 	salary_component_and_type = {_("Earning"): [], _("Deduction"): []}

# 	for salary_component in get_salary_components(salary_slips):
# 		component_type = get_salary_component_type(salary_component)
# 		salary_component_and_type[_(component_type)].append(salary_component)

# 	# return earnings, deductions (sorted)
# 	return sorted(salary_component_and_type[_("Earning")]), sorted(
# 		salary_component_and_type[_("Deduction")]
# 	)


# def update_column_width(ss, columns):
# 	"""
# 	Update widths for branch/department/designation/leave_without_pay fields if the value exists.
# 	We find column by fieldname instead of relying on fixed indices (safer).
# 	"""
# 	field_width_map = {
# 		"branch": ("branch", 120),
# 		"department": ("department", 120),
# 		"designation": ("designation", 120),
# 		"leave_without_pay": ("leave_without_pay", 120),
# 	}

# 	for key, (fieldname, width) in field_width_map.items():
# 		if getattr(ss, key, None) is not None:
# 			for col in columns:
# 				if col.get("fieldname") == fieldname:
# 					col.update({"width": width})
# 					break


# def get_columns(earning_types, ded_types, report_currency, component_field_map):
# 	# report_currency passed in to set Currency column options so header shows correct currency.
# 	columns = [
# 		{
# 			"label": _("Salary Slip ID"),
# 			"fieldname": "salary_slip_id",
# 			"fieldtype": "Link",
# 			"options": "Salary Slip",
# 			"width": 150,
# 		},
# 		{
# 			"label": _("Employee"),
# 			"fieldname": "employee",
# 			"fieldtype": "Link",
# 			"options": "Employee",
# 			"width": 120,
# 		},
# 		{
# 			"label": _("Employee Name"),
# 			"fieldname": "employee_name",
# 			"fieldtype": "Data",
# 			"width": 180,
# 		},
# 		{
# 			"label": _("Bank Beneficiary ID"),
# 			"fieldname": "bank_beneficiary_id",
# 			"fieldtype": "Data",
# 			"width": 180,
# 		},
# 		{
# 			"label": _("Date of Joining"),
# 			"fieldname": "data_of_joining",
# 			"fieldtype": "Date",
# 			"width": 180,
# 		},
# 		{
# 			"label": _("Branch"),
# 			"fieldname": "branch",
# 			"fieldtype": "Link",
# 			"options": "Branch",
# 			"width": 140,
# 		},
# 		{
# 			"label": _("Department"),
# 			"fieldname": "department",
# 			"fieldtype": "Link",
# 			"options": "Department",
# 			"width": 140,
# 		},
# 		{
# 			"label": _("Designation"),
# 			"fieldname": "designation",
# 			"fieldtype": "Link",
# 			"options": "Designation",
# 			"width": 120,
# 		},
# 		{
# 			"label": _("Company"),
# 			"fieldname": "company",
# 			"fieldtype": "Link",
# 			"options": "Company",
# 			"width": 120,
# 		},
# 		{
# 			"label": _("Start Date"),
# 			"fieldname": "start_date",
# 			"fieldtype": "Data",
# 			"width": 80,
# 		},
# 		{
# 			"label": _("End Date"),
# 			"fieldname": "end_date",
# 			"fieldtype": "Data",
# 			"width": 180,
# 		},
# 		{
# 			"label": _("Leave Without Pay"),
# 			"fieldname": "leave_without_pay",
# 			"fieldtype": "Float",
# 			"width": 150,
# 		},
# 		{
# 			"label": _("Absent Days"),
# 			"fieldname": "absent_days",
# 			"fieldtype": "Float",
# 			"width": 150,
# 		},
# 		{
# 			"label": _("Payment Days"),
# 			"fieldname": "payment_days",
# 			"fieldtype": "Float",
# 			"width": 120,
# 		},
# 	]

# 	# Earnings columns (currency)
# 	for earning in earning_types:
# 		columns.append(
# 			{
# 				"label": earning,
# 				"fieldname": component_field_map[earning],
# 				"fieldtype": "Currency",
# 				"options": report_currency,
# 				"width": 120,
# 			}
# 		)

# 	columns.append(
# 		{
# 			"label": _("Gross Pay"),
# 			"fieldname": "gross_pay",
# 			"fieldtype": "Currency",
# 			"options": report_currency,
# 			"width": 120,
# 		}
# 	)

# 	# Deductions columns (currency)
# 	for deduction in ded_types:
# 		columns.append(
# 			{
# 				"label": deduction,
# 				"fieldname": component_field_map[deduction],
# 				"fieldtype": "Currency",
# 				"options": report_currency,
# 				"width": 120,
# 			}
# 		)

# 	columns.extend(
# 		[
# 			{
# 				"label": _("Loan Repayment"),
# 				"fieldname": "total_loan_repayment",
# 				"fieldtype": "Currency",
# 				"options": report_currency,
# 				"width": 140,
# 			},
# 			{
# 				"label": _("Total Deduction"),
# 				"fieldname": "total_deduction",
# 				"fieldtype": "Currency",
# 				"options": report_currency,
# 				"width": 140,
# 			},
# 			{
# 				"label": _("Net Pay"),
# 				"fieldname": "net_pay",
# 				"fieldtype": "Currency",
# 				"options": report_currency,
# 				"width": 120,
# 			},
# 			{
# 				"label": _("Currency"),
# 				"fieldtype": "Data",
# 				"fieldname": "currency",
# 				"hidden": 1,
# 			},
# 		]
# 	)

# 	columns.append(
# 		{
# 			"label": "Is Total Row",
# 			"fieldname": "is_total_row",
# 			"fieldtype": "Check",
# 			"hidden": 1,
# 		}
# 	)

# 	return columns


# def get_salary_components(salary_slips):
# 	return (
# 		frappe.qb.from_(salary_detail)
# 		.where((salary_detail.amount != 0) & (salary_detail.parent.isin([d.name for d in salary_slips])))
# 		.select(salary_detail.salary_component)
# 		.distinct()
# 	).run(pluck=True)


# def get_salary_component_type(salary_component):
# 	return frappe.db.get_value("Salary Component", salary_component, "type", cache=True)


# def get_salary_slips(filters, company_currency):
# 	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}

# 	query = frappe.qb.from_(salary_slip).select(salary_slip.star)

# 	if filters.get("docstatus"):
# 		query = query.where(salary_slip.docstatus == doc_status[filters.get("docstatus")])

# 	if filters.get("from_date"):
# 		query = query.where(salary_slip.start_date >= filters.get("from_date"))

# 	if filters.get("to_date"):
# 		query = query.where(salary_slip.end_date <= filters.get("to_date"))

# 	if filters.get("company"):
# 		query = query.where(salary_slip.company == filters.get("company"))

# 	if filters.get("employee"):
# 		query = query.where(salary_slip.employee == filters.get("employee"))

# 	# If user requested a currency different from company currency, filter salary_slips by that currency.
# 	if filters.get("currency") and filters.get("currency") != company_currency:
# 		query = query.where(salary_slip.currency == filters.get("currency"))

# 	if filters.get("department"):
# 		query = query.where(salary_slip.department == filters["department"])

# 	if filters.get("designation"):
# 		query = query.where(salary_slip.designation == filters["designation"])

# 	if filters.get("branch"):
# 		query = query.where(salary_slip.branch == filters["branch"])

# 	salary_slips = query.run(as_dict=1)

# 	return salary_slips or []


# def get_employee_doj_map():
# 	employee = frappe.qb.DocType("Employee")

# 	result = (frappe.qb.from_(employee).select(employee.name, employee.date_of_joining)).run()

# 	# convert list of tuples to dict-like mapping
# 	return frappe._dict(result)


# def get_salary_slip_details(salary_slips, currency, company_currency, component_type):
# 	"""
# 	Build map: { salary_slip_name: { salary_component_name: amount_in_report_currency } }

# 	If `currency` is provided and differs from company currency, amounts are multiplied by exchange_rate
# 	(which is expected to convert stored company-currency amounts into the requested currency).
# 	"""
# 	salary_slips = [ss.name for ss in salary_slips]

# 	result = (
# 		frappe.qb.from_(salary_slip)
# 		.join(salary_detail)
# 		.on(salary_slip.name == salary_detail.parent)
# 		.where((salary_detail.parent.isin(salary_slips)) & (salary_detail.parentfield == component_type))
# 		.select(
# 			salary_detail.parent,
# 			salary_detail.salary_component,
# 			salary_detail.amount,
# 			salary_slip.exchange_rate,
# 		)
# 	).run(as_dict=1)

# 	ss_map = {}

# 	for d in result:
# 		ss_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, 0.0)
# 		# Convert only when user requested a different currency than company currency
# 		if currency and currency != company_currency:
# 			ss_map[d.parent][d.salary_component] += flt(d.amount) * flt(d.exchange_rate or 1)
# 		else:
# 			ss_map[d.parent][d.salary_component] += flt(d.amount)

# 	return ss_map

# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

# import frappe
# from frappe import _
# from frappe.utils import flt

# import erpnext

# salary_slip = frappe.qb.DocType("Salary Slip")
# salary_detail = frappe.qb.DocType("Salary Detail")
# salary_component = frappe.qb.DocType("Salary Component")


# def execute(filters=None):
# 	if not filters:
# 		filters = {}

# 	# optional filter to force exact label
# 	forced_annual_component = filters.get("annual_component")

# 	# requested report currency (None -> company currency)
# 	currency = filters.get("currency")
# 	company_currency = erpnext.get_company_currency(filters.get("company"))
# 	report_currency = currency or company_currency

# 	# fetch salary slips
# 	salary_slips = get_salary_slips(filters, company_currency)
# 	if not salary_slips:
# 		return [], []

# 	# detected components present across these slips
# 	earning_types, ded_types = get_earning_and_deduction_types(salary_slips)

# 	# build unique fieldname map
# 	component_field_map = build_unique_component_field_map(earning_types + ded_types)

# 	# detection heuristics
# 	annual_component = detect_annual_variable_component(earning_types, forced_annual_component)
# 	arrears_component = detect_arrears_component(earning_types)

# 	# choose display labels (prefer detected names)
# 	annual_label = annual_component or "Annual Variable Pay"
# 	arrears_label = arrears_component or "Arrears"

# 	# ensure map has entries for the always-present labels (avoid collisions)
# 	if annual_label not in component_field_map:
# 		component_field_map[annual_label] = make_unique_scrubbed_fieldname(component_field_map, annual_label)
# 	if arrears_label not in component_field_map:
# 		component_field_map[arrears_label] = make_unique_scrubbed_fieldname(component_field_map, arrears_label)

# 	# build columns: earnings components, gross, then arrears, annual, deductions, totals
# 	columns = get_columns(earning_types, ded_types, report_currency, component_field_map, annual_label, arrears_label, arrears_component in earning_types)

# 	# get earnings/deductions mapping per slip (handles conversion when currency filter set)
# 	ss_earning_map = get_salary_slip_details(salary_slips, currency, company_currency, "earnings")
# 	ss_ded_map = get_salary_slip_details(salary_slips, currency, company_currency, "deductions")

# 	doj_map = get_employee_doj_map()

# 	data = []
# 	for ss in salary_slips:
# 		row = {
# 			"salary_slip_id": ss.name,
# 			"employee": ss.employee,
# 			"employee_name": ss.employee_name,
# 			"bank_beneficiary_id": frappe.db.get_value("Employee", ss.employee, "bank_ac_no"),
# 			"data_of_joining": doj_map.get(ss.employee),
# 			"branch": ss.branch,
# 			"department": ss.department,
# 			"designation": ss.designation,
# 			"company": ss.company,
# 			"start_date": ss.start_date,
# 			"end_date": ss.end_date,
# 			"leave_without_pay": ss.leave_without_pay,
# 			"absent_days": ss.absent_days,
# 			"payment_days": ss.payment_days,
# 			"currency": report_currency,
# 			"total_loan_repayment": ss.total_loan_repayment,
# 		}

# 		# populate earnings component columns (these use ss_earning_map; amounts already converted if required)
# 		for e in earning_types:
# 			fname = component_field_map.get(e)
# 			row[fname] = flt(ss_earning_map.get(ss.name, {}).get(e, 0.0))

# 		# populate deductions
# 		for d in ded_types:
# 			fname = component_field_map.get(d)
# 			row[fname] = flt(ss_ded_map.get(ss.name, {}).get(d, 0.0))

# 		# Now ensure Arrears (component) column contains the component amount (if present in earnings)
# 		arrears_fieldname = component_field_map[arrears_label]
# 		if arrears_component:
# 			# fetch by actual component label from earnings map
# 			row[arrears_fieldname] = flt(ss_earning_map.get(ss.name, {}).get(arrears_component, 0.0))
# 		else:
# 			# if no detected component, still try key "Arrears" or default 0
# 			row[arrears_fieldname] = flt(ss_earning_map.get(ss.name, {}).get("Arrears", 0.0))

# 		# Ensure Annual Variable Pay column gets the component amount (if present)
# 		annual_fieldname = component_field_map[annual_label]
# 		annual_val = 0.0
# 		if annual_component:
# 			annual_val = flt(ss_earning_map.get(ss.name, {}).get(annual_component, 0.0))
# 		# fallback to using the chosen label key if needed
# 		if not annual_val:
# 			annual_val = flt(ss_earning_map.get(ss.name, {}).get(annual_label, 0.0))
# 		row[annual_fieldname] = annual_val

# 		# summary fields (gross/total/net) - convert using slip.exchange_rate when currency requested != company currency
# 		if currency and currency != company_currency:
# 			rate = flt(ss.exchange_rate or 1)
# 			row["gross_pay"] = flt(ss.gross_pay) * rate
# 			row["total_deduction"] = flt(ss.total_deduction) * rate
# 			row["net_pay"] = flt(ss.net_pay) * rate
# 		else:
# 			row["gross_pay"] = flt(ss.gross_pay)
# 			row["total_deduction"] = flt(ss.total_deduction)
# 			row["net_pay"] = flt(ss.net_pay)

# 		data.append(row)

# 	# build total row
# 	totals_row = {"salary_slip_id": "Total", "is_total_row": 1}

# 	# base totals
# 	total_fields = [
# 		"leave_without_pay",
# 		"absent_days",
# 		"payment_days",
# 		"gross_pay",
# 		"total_loan_repayment",
# 		"total_deduction",
# 		"net_pay",
# 	]

# 	# include all component fields in totals
# 	earning_fields = [component_field_map[e] for e in earning_types]
# 	deduction_fields = [component_field_map[d] for d in ded_types]

# 	# ensure arrears and annual fieldnames are in totals (avoid duplicates)
# 	if arrears_fieldname not in earning_fields:
# 		earning_fields.append(arrears_fieldname)
# 	if annual_fieldname not in earning_fields:
# 		earning_fields.append(annual_fieldname)

# 	total_fields.extend(earning_fields)
# 	total_fields.extend(deduction_fields)

# 	for f in total_fields:
# 		totals_row[f] = 0.0

# 	for row in data:
# 		for f in total_fields:
# 			totals_row[f] += flt(row.get(f))

# 	data.append(totals_row)

# 	return columns, data


# # ---------- helper functions ----------


# def detect_annual_variable_component(earning_types, forced_name=None):
# 	"""Return exact component label if found, or None. If forced_name given, return it (if exact match found)."""
# 	if forced_name:
# 		for e in earning_types:
# 			if e.strip().lower() == forced_name.strip().lower():
# 				return e
# 		# if forced provided but not exact match, return forced so column label matches user's intent
# 		return forced_name

# 	if not earning_types:
# 		return None

# 	lowered = [e.strip().lower() for e in earning_types]

# 	# common exact forms
# 	for i, e in enumerate(lowered):
# 		if e in ("annual variable pay", "annual variable", "annualvariablepay", "annualvariable", "annualvarpay"):
# 			return earning_types[i]

# 	# contains both words
# 	for i, e in enumerate(lowered):
# 		if "annual" in e and "variable" in e:
# 			return earning_types[i]

# 	# contains either
# 	for i, e in enumerate(lowered):
# 		if "annual" in e or "variable" in e:
# 			return earning_types[i]

# 	# abbreviations
# 	for i, e in enumerate(lowered):
# 		if "avp" in e or "annualvar" in e or "annual_var" in e:
# 			return earning_types[i]

# 	# log for debugging
# 	try:
# 		frappe.log_error(f"Earning component names scanned: {earning_types}", "Annual Component Detection - Not Found")
# 	except Exception:
# 		pass

# 	return None


# def detect_arrears_component(earning_types):
# 	"""Return the first earning component that contains 'arrear' or 'arrears' (case-insensitive), or None."""
# 	if not earning_types:
# 		return None
# 	lowered = [e.strip().lower() for e in earning_types]
# 	for i, e in enumerate(lowered):
# 		if "arrear" in e or "arrears" in e:
# 			return earning_types[i]
# 	return None


# def make_unique_scrubbed_fieldname(existing_map, label):
# 	"""Create a unique scrubbed fieldname that doesn't collide with existing_map values."""
# 	base = frappe.scrub(label)
# 	fieldname = base
# 	counter = 1
# 	used = set(existing_map.values())
# 	while fieldname in used:
# 		fieldname = f"{base}_{counter}"
# 		counter += 1
# 	return fieldname


# def build_unique_component_field_map(components):
# 	"""Map component label -> unique scrubbed fieldname."""
# 	field_map = {}
# 	used = set()
# 	for comp in components:
# 		base = frappe.scrub(comp)
# 		fname = base
# 		counter = 1
# 		while fname in used:
# 			fname = f"{base}_{counter}"
# 			counter += 1
# 		used.add(fname)
# 		field_map[comp] = fname
# 	return field_map


# def get_earning_and_deduction_types(salary_slips):
# 	salary_component_and_type = {_("Earning"): [], _("Deduction"): []}
# 	for salary_component in get_salary_components(salary_slips):
# 		component_type = get_salary_component_type(salary_component)
# 		salary_component_and_type[_(component_type)].append(salary_component)
# 	return sorted(salary_component_and_type[_("Earning")]), sorted(salary_component_and_type[_("Deduction")])


# def update_column_width(ss, columns):
# 	# keep safe update behavior (optional)
# 	field_width_map = {
# 		"branch": ("branch", 120),
# 		"department": ("department", 120),
# 		"designation": ("designation", 120),
# 		"leave_without_pay": ("leave_without_pay", 120),
# 	}
# 	for key, (fieldname, width) in field_width_map.items():
# 		if getattr(ss, key, None) is not None:
# 			for col in columns:
# 				if col.get("fieldname") == fieldname:
# 					col.update({"width": width})
# 					break


# def get_columns(earning_types, ded_types, report_currency, component_field_map, annual_label, arrears_label, arrears_in_earnings):
# 	# start with basic columns
# 	columns = [
# 		{"label": _("Salary Slip ID"), "fieldname": "salary_slip_id", "fieldtype": "Link", "options": "Salary Slip", "width": 150},
# 		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
# 		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
# 		{"label": _("Bank Beneficiary ID"), "fieldname": "bank_beneficiary_id", "fieldtype": "Data", "width": 180},
# 		{"label": _("Date of Joining"), "fieldname": "data_of_joining", "fieldtype": "Date", "width": 180},
# 		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 140},
# 		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
# 		{"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 120},
# 		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
# 		{"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Data", "width": 80},
# 		{"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Data", "width": 180},
# 		{"label": _("Leave Without Pay"), "fieldname": "leave_without_pay", "fieldtype": "Float", "width": 150},
# 		{"label": _("Absent Days"), "fieldname": "absent_days", "fieldtype": "Float", "width": 150},
# 		{"label": _("Payment Days"), "fieldname": "payment_days", "fieldtype": "Float", "width": 120},
# 	]

# 	# earnings component columns
# 	for earning in earning_types:
# 		columns.append({"label": earning, "fieldname": component_field_map[earning], "fieldtype": "Currency", "options": report_currency, "width": 120})

# 	# gross pay
# 	columns.append({"label": _("Gross Pay"), "fieldname": "gross_pay", "fieldtype": "Currency", "options": report_currency, "width": 120})

# 	# component-based Arrears column (if it was part of earnings, it's already added above, but we ensure field exists and label present)
# 	arrears_fieldname = component_field_map[arrears_label]
# 	# if arrears component already added above (exists in earning_types), it will not duplicate because fieldname same label different entry,
# 	# but to keep order we add a label here only if not present in earnings loop (so Arrears appears right after Gross)
# 	if not arrears_in_earnings:
# 		columns.append({"label": arrears_label, "fieldname": arrears_fieldname, "fieldtype": "Currency", "options": report_currency, "width": 120})
# 	else:
# 		# If it is in earnings and you still want Arrears column right after Gross, add it here but ensure it's not duplicated visually.
# 		# We'll add it to preserve requested ordering (after Gross).
# 		columns.append({"label": arrears_label, "fieldname": arrears_fieldname, "fieldtype": "Currency", "options": report_currency, "width": 120})

# 	# ALWAYS add Annual Variable Pay column after Arrears
# 	annual_fieldname = component_field_map[annual_label]
# 	columns.append({"label": annual_label, "fieldname": annual_fieldname, "fieldtype": "Currency", "options": report_currency, "width": 140})

# 	# deductions
# 	for deduction in ded_types:
# 		columns.append({"label": deduction, "fieldname": component_field_map[deduction], "fieldtype": "Currency", "options": report_currency, "width": 120})

# 	columns.extend([
# 		{"label": _("Loan Repayment"), "fieldname": "total_loan_repayment", "fieldtype": "Currency", "options": report_currency, "width": 140},
# 		{"label": _("Total Deduction"), "fieldname": "total_deduction", "fieldtype": "Currency", "options": report_currency, "width": 140},
# 		{"label": _("Net Pay"), "fieldname": "net_pay", "fieldtype": "Currency", "options": report_currency, "width": 120},
# 		{"label": _("Currency"), "fieldtype": "Data", "fieldname": "currency", "hidden": 1},
# 	])

# 	columns.append({"label": "Is Total Row", "fieldname": "is_total_row", "fieldtype": "Check", "hidden": 1})

# 	return columns


# def get_salary_components(salary_slips):
# 	return (
# 		frappe.qb.from_(salary_detail)
# 		.where((salary_detail.amount != 0) & (salary_detail.parent.isin([d.name for d in salary_slips])))
# 		.select(salary_detail.salary_component)
# 		.distinct()
# 	).run(pluck=True)


# def get_salary_component_type(salary_component):
# 	return frappe.db.get_value("Salary Component", salary_component, "type", cache=True)


# def get_salary_slips(filters, company_currency):
# 	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
# 	query = frappe.qb.from_(salary_slip).select(salary_slip.star)

# 	if filters.get("docstatus"):
# 		query = query.where(salary_slip.docstatus == doc_status[filters.get("docstatus")])

# 	if filters.get("from_date"):
# 		query = query.where(salary_slip.start_date >= filters.get("from_date"))

# 	if filters.get("to_date"):
# 		query = query.where(salary_slip.end_date <= filters.get("to_date"))

# 	if filters.get("company"):
# 		query = query.where(salary_slip.company == filters.get("company"))

# 	if filters.get("employee"):
# 		query = query.where(salary_slip.employee == filters.get("employee"))

# 	if filters.get("currency") and filters.get("currency") != company_currency:
# 		query = query.where(salary_slip.currency == filters.get("currency"))

# 	if filters.get("department"):
# 		query = query.where(salary_slip.department == filters["department"])

# 	if filters.get("designation"):
# 		query = query.where(salary_slip.designation == filters["designation"])

# 	if filters.get("branch"):
# 		query = query.where(salary_slip.branch == filters["branch"])

# 	salary_slips = query.run(as_dict=1)
# 	return salary_slips or []


# def get_employee_doj_map():
# 	employee = frappe.qb.DocType("Employee")
# 	result = (frappe.qb.from_(employee).select(employee.name, employee.date_of_joining)).run()
# 	return frappe._dict(result)


# def get_salary_slip_details(salary_slips, currency, company_currency, component_type):
# 	"""Return map: { salary_slip_name: { salary_component_label: amount } }.
# 	   If currency != company_currency, amounts are multiplied by the slip.exchange_rate."""
# 	salary_slips = [ss.name for ss in salary_slips]

# 	result = (
# 		frappe.qb.from_(salary_slip)
# 		.join(salary_detail)
# 		.on(salary_slip.name == salary_detail.parent)
# 		.where((salary_detail.parent.isin(salary_slips)) & (salary_detail.parentfield == component_type))
# 		.select(salary_detail.parent, salary_detail.salary_component, salary_detail.amount, salary_slip.exchange_rate)
# 	).run(as_dict=1)

# 	ss_map = {}
# 	for d in result:
# 		ss_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, 0.0)
# 		if currency and currency != company_currency:
# 			ss_map[d.parent][d.salary_component] += flt(d.amount) * flt(d.exchange_rate or 1)
# 		else:
# 			ss_map[d.parent][d.salary_component] += flt(d.amount)

# 	return ss_map













# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe import _
from frappe.utils import flt

import erpnext

salary_slip = frappe.qb.DocType("Salary Slip")
salary_detail = frappe.qb.DocType("Salary Detail")
salary_component = frappe.qb.DocType("Salary Component")


def execute(filters=None):
	if not filters:
		filters = {}

	# optional filter to force exact label for annual variable
	forced_annual_component = filters.get("annual_component")

	# currency handling
	currency = filters.get("currency")
	company_currency = erpnext.get_company_currency(filters.get("company"))
	report_currency = currency or company_currency

	# fetch salary slips
	salary_slips = get_salary_slips(filters, company_currency)
	if not salary_slips:
		return [], []

	# detect earning & deduction components present in the selected slips
	earning_types, ded_types = get_earning_and_deduction_types(salary_slips)

	# build unique fieldname mapping for components (avoid collisions)
	component_field_map = build_unique_component_field_map(earning_types + ded_types)

	# detect special components
	annual_component = detect_annual_variable_component(earning_types, forced_annual_component)
	arrears_component = detect_arrears_component(earning_types)
	loan_component = detect_loan_repayment_component(ded_types)

	# display labels (prefer detected exact label)
	annual_label = annual_component or "Annual Variable Pay"
	arrears_label = arrears_component or "Arrears"
	# loan column in the report stays as 'Loan Repayment' (fieldname 'total_loan_repayment') but we'll source the amount
	loan_label_candidates = [loan_component] if loan_component else ["Loan Repayment"]

	# ensure component_field_map has entries for annual/arrears labels (so the column fieldnames exist)
	if annual_label not in component_field_map:
		component_field_map[annual_label] = make_unique_scrubbed_fieldname(component_field_map, annual_label)
	if arrears_label not in component_field_map:
		component_field_map[arrears_label] = make_unique_scrubbed_fieldname(component_field_map, arrears_label)
	# if the detected loan component exists and isn't in the map (unlikely), create it
	if loan_component and loan_component not in component_field_map:
		component_field_map[loan_component] = make_unique_scrubbed_fieldname(component_field_map, loan_component)

	# build columns
	columns = get_columns(
		earning_types,
		ded_types,
		report_currency,
		component_field_map,
		annual_label,
		arrears_label,
		arrears_component is not None,
	)

	# get earnings/deductions maps (these already apply exchange_rate when user requested different currency)
	ss_earning_map = get_salary_slip_details(salary_slips, currency, company_currency, "earnings")
	ss_ded_map = get_salary_slip_details(salary_slips, currency, company_currency, "deductions")

	doj_map = get_employee_doj_map()

	data = []
	for ss in salary_slips:
		row = {
			"salary_slip_id": ss.name,
			"employee": ss.employee,
			"employee_name": ss.employee_name,
			"bank_beneficiary_id": frappe.db.get_value("Employee", ss.employee, "bank_ac_no"),
			"data_of_joining": doj_map.get(ss.employee),
			"branch": ss.branch,
			"department": ss.department,
			"designation": ss.designation,
			"company": ss.company,
			"start_date": ss.start_date,
			"end_date": ss.end_date,
			"leave_without_pay": ss.leave_without_pay,
			"absent_days": ss.absent_days,
			"payment_days": ss.payment_days,
			"currency": report_currency,
			# We'll populate 'total_loan_repayment' below (from component or top-level fallback)
			"total_loan_repayment": 0.0,
		}

		# populate earnings component columns from ss_earning_map
		for e in earning_types:
			fname = component_field_map.get(e)
			row[fname] = flt(ss_earning_map.get(ss.name, {}).get(e, 0.0))

		# populate deductions component columns from ss_ded_map
		for d in ded_types:
			fname = component_field_map.get(d)
			row[fname] = flt(ss_ded_map.get(ss.name, {}).get(d, 0.0))

		# Component-based Arrears column: prefer component value if detected
		arrears_fieldname = component_field_map[arrears_label]
		if arrears_component:
			row[arrears_fieldname] = flt(ss_earning_map.get(ss.name, {}).get(arrears_component, 0.0))
		else:
			row[arrears_fieldname] = flt(ss_earning_map.get(ss.name, {}).get("Arrears", 0.0))

		# Top-level Arrears (if you want this, we also set 'arrears_slip' from Salary Slip)
		row["arrears_slip"] = flt(getattr(ss, "arrears", 0.0))

		# Annual Variable Pay: prefer detected component amount; fallback to label key
		annual_fieldname = component_field_map[annual_label]
		annual_val = 0.0
		if annual_component:
			annual_val = flt(ss_earning_map.get(ss.name, {}).get(annual_component, 0.0))
		if not annual_val:
			annual_val = flt(ss_earning_map.get(ss.name, {}).get(annual_label, 0.0))
		row[annual_fieldname] = annual_val

		# === Loan Repayment logic (fix) ===
		# Priority:
		#   1. If a deduction component matching loan_component was detected, use its amount from ss_ded_map
		#   2. Otherwise, fall back to Salary Slip top-level ss.total_loan_repayment (converted if currency requested)
		loan_value = 0.0
		if loan_component:
			loan_value = flt(ss_ded_map.get(ss.name, {}).get(loan_component, 0.0))
		# also try common label if not found above
		if not loan_value:
			loan_value = flt(ss_ded_map.get(ss.name, {}).get("Loan Repayment", 0.0))
		# fallback to top-level field (note: top-level field is stored in company currency; if user requested different currency,
		# convert using ss.exchange_rate)
		if not loan_value:
			if currency and currency != company_currency:
				rate = flt(ss.exchange_rate or 1)
				loan_value = flt(ss.total_loan_repayment or 0.0) * rate
			else:
				loan_value = flt(ss.total_loan_repayment or 0.0)

		row["total_loan_repayment"] = loan_value

		# summary fields: gross/total/net (top-level fields on Salary Slip)
		if currency and currency != company_currency:
			rate = flt(ss.exchange_rate or 1)
			row["gross_pay"] = flt(ss.gross_pay) * rate
			row["total_deduction"] = flt(ss.total_deduction) * rate
			row["net_pay"] = flt(ss.net_pay) * rate
		else:
			row["gross_pay"] = flt(ss.gross_pay)
			row["total_deduction"] = flt(ss.total_deduction)
			row["net_pay"] = flt(ss.net_pay)

		data.append(row)

	# Totals row
	totals_row = {"salary_slip_id": "Total", "is_total_row": 1}

	# base total fields
	total_fields = [
		"leave_without_pay",
		"absent_days",
		"payment_days",
		"gross_pay",
		"total_loan_repayment",  # this will now reflect component amount when present
		"total_deduction",
		"net_pay",
	]

	# include earnings and deduction component fieldnames
	earning_fields = [component_field_map[e] for e in earning_types]
	deduction_fields = [component_field_map[d] for d in ded_types]

	# ensure arrears & annual included in totals
	arrears_field = component_field_map[arrears_label]
	if arrears_field not in earning_fields:
		earning_fields.append(arrears_field)

	annual_field = component_field_map[annual_label]
	if annual_field not in earning_fields:
		earning_fields.append(annual_field)

	total_fields.extend(earning_fields)
	total_fields.extend(deduction_fields)

	# initialize totals
	for f in total_fields:
		totals_row[f] = 0.0

	# sum
	for row in data:
		for f in total_fields:
			totals_row[f] += flt(row.get(f))

	data.append(totals_row)

	return columns, data


# ---------------- helper functions ----------------

def detect_annual_variable_component(earning_types, forced_name=None):
	if forced_name:
		for e in earning_types:
			if e.strip().lower() == forced_name.strip().lower():
				return e
		return forced_name

	if not earning_types:
		return None

	lowered = [e.strip().lower() for e in earning_types]
	for i, e in enumerate(lowered):
		if e in ("annual variable pay", "annual variable", "annualvariablepay", "annualvariable", "annualvarpay"):
			return earning_types[i]
	for i, e in enumerate(lowered):
		if "annual" in e and "variable" in e:
			return earning_types[i]
	for i, e in enumerate(lowered):
		if "annual" in e or "variable" in e:
			return earning_types[i]
	for i, e in enumerate(lowered):
		if "avp" in e or "annualvar" in e or "annual_var" in e:
			return earning_types[i]
	try:
		frappe.log_error(f"Earning component names scanned: {earning_types}", "Annual Component Detection - Not Found")
	except Exception:
		pass
	return None


def detect_arrears_component(earning_types):
	if not earning_types:
		return None
	lowered = [e.strip().lower() for e in earning_types]
	for i, e in enumerate(lowered):
		if "arrear" in e or "arrears" in e:
			return earning_types[i]
	return None


def detect_loan_repayment_component(ded_types):
	"""
	Detect a deduction component that corresponds to 'Loan Repayment' (robust heuristics).
	Returns the exact component label if found, otherwise None.
	"""
	if not ded_types:
		return None
	lowered = [d.strip().lower() for d in ded_types]
	for i, d in enumerate(lowered):
		# look for common patterns
		if "loan" in d and ("repay" in d or "repayment" in d):
			return ded_types[i]
		# sometimes label might be 'Loan Repayment' exact
		if d == "loan repayment":
			return ded_types[i]
	# fallback: exact match
	for i, d in enumerate(lowered):
		if d == "loan_repayment" or d == "loanrepayment":
			return ded_types[i]
	return None


def make_unique_scrubbed_fieldname(existing_map, label):
	base = frappe.scrub(label)
	fieldname = base
	counter = 1
	used = set(existing_map.values())
	while fieldname in used:
		fieldname = f"{base}_{counter}"
		counter += 1
	return fieldname


def build_unique_component_field_map(components):
	field_map = {}
	used = set()
	for comp in components:
		base = frappe.scrub(comp)
		fname = base
		counter = 1
		while fname in used:
			fname = f"{base}_{counter}"
			counter += 1
		used.add(fname)
		field_map[comp] = fname
	return field_map


def get_earning_and_deduction_types(salary_slips):
	salary_component_and_type = {_("Earning"): [], _("Deduction"): []}
	for salary_component in get_salary_components(salary_slips):
		component_type = get_salary_component_type(salary_component)
		salary_component_and_type[_(component_type)].append(salary_component)
	return sorted(salary_component_and_type[_("Earning")]), sorted(salary_component_and_type[_("Deduction")])


def update_column_width(ss, columns):
	field_width_map = {
		"branch": ("branch", 120),
		"department": ("department", 120),
		"designation": ("designation", 120),
		"leave_without_pay": ("leave_without_pay", 120),
	}
	for key, (fieldname, width) in field_width_map.items():
		if getattr(ss, key, None) is not None:
			for col in columns:
				if col.get("fieldname") == fieldname:
					col.update({"width": width})
					break


def get_columns(earning_types, ded_types, report_currency, component_field_map, annual_label, arrears_label, has_arrears_component):
	# basic columns
	columns = [
		{"label": _("Salary Slip ID"), "fieldname": "salary_slip_id", "fieldtype": "Link", "options": "Salary Slip", "width": 150},
		{"label": _("Employee"), "fieldname": "employee", "fieldtype": "Link", "options": "Employee", "width": 120},
		{"label": _("Employee Name"), "fieldname": "employee_name", "fieldtype": "Data", "width": 180},
		{"label": _("Bank Beneficiary ID"), "fieldname": "bank_beneficiary_id", "fieldtype": "Data", "width": 180},
		{"label": _("Date of Joining"), "fieldname": "data_of_joining", "fieldtype": "Date", "width": 180},
		{"label": _("Branch"), "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 140},
		{"label": _("Department"), "fieldname": "department", "fieldtype": "Link", "options": "Department", "width": 140},
		{"label": _("Designation"), "fieldname": "designation", "fieldtype": "Link", "options": "Designation", "width": 120},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
		{"label": _("Start Date"), "fieldname": "start_date", "fieldtype": "Data", "width": 80},
		{"label": _("End Date"), "fieldname": "end_date", "fieldtype": "Data", "width": 180},
		{"label": _("Leave Without Pay"), "fieldname": "leave_without_pay", "fieldtype": "Float", "width": 150},
		{"label": _("Absent Days"), "fieldname": "absent_days", "fieldtype": "Float", "width": 150},
		{"label": _("Payment Days"), "fieldname": "payment_days", "fieldtype": "Float", "width": 120},
	]

	# earnings components columns
	for earning in earning_types:
		columns.append({"label": earning, "fieldname": component_field_map[earning], "fieldtype": "Currency", "options": report_currency, "width": 120})

	# gross
	columns.append({"label": _("Gross Pay"), "fieldname": "gross_pay", "fieldtype": "Currency", "options": report_currency, "width": 120})

	# component-based Arrears (add after Gross)
	arrears_fieldname = component_field_map[arrears_label]
	columns.append({"label": arrears_label, "fieldname": arrears_fieldname, "fieldtype": "Currency", "options": report_currency, "width": 120})

	# top-level Arrears (slip) - optional, you can remove if not needed
	columns.append({"label": _("Arrears (slip)"), "fieldname": "arrears_slip", "fieldtype": "Currency", "options": report_currency, "width": 120})

	# ALWAYS append Annual Variable Pay column
	annual_fieldname = component_field_map[annual_label]
	columns.append({"label": annual_label, "fieldname": annual_fieldname, "fieldtype": "Currency", "options": report_currency, "width": 140})

	# deduction columns
	for deduction in ded_types:
		columns.append({"label": deduction, "fieldname": component_field_map[deduction], "fieldtype": "Currency", "options": report_currency, "width": 120})

	# Loan Repayment summary column (we populate this from the detected deduction component or fallback to top-level)
	columns.append({"label": _("Loan Repayment"), "fieldname": "total_loan_repayment", "fieldtype": "Currency", "options": report_currency, "width": 140})

	columns.extend([
		{"label": _("Total Deduction"), "fieldname": "total_deduction", "fieldtype": "Currency", "options": report_currency, "width": 140},
		{"label": _("Net Pay"), "fieldname": "net_pay", "fieldtype": "Currency", "options": report_currency, "width": 120},
		{"label": _("Currency"), "fieldtype": "Data", "fieldname": "currency", "hidden": 1},
	])

	columns.append({"label": "Is Total Row", "fieldname": "is_total_row", "fieldtype": "Check", "hidden": 1})

	return columns


def get_salary_components(salary_slips):
	return (
		frappe.qb.from_(salary_detail)
		.where((salary_detail.amount != 0) & (salary_detail.parent.isin([d.name for d in salary_slips])))
		.select(salary_detail.salary_component)
		.distinct()
	).run(pluck=True)


def get_salary_component_type(salary_component):
	return frappe.db.get_value("Salary Component", salary_component, "type", cache=True)


def get_salary_slips(filters, company_currency):
	doc_status = {"Draft": 0, "Submitted": 1, "Cancelled": 2}
	query = frappe.qb.from_(salary_slip).select(salary_slip.star)

	if filters.get("docstatus"):
		query = query.where(salary_slip.docstatus == doc_status[filters.get("docstatus")])

	if filters.get("from_date"):
		query = query.where(salary_slip.start_date >= filters.get("from_date"))

	if filters.get("to_date"):
		query = query.where(salary_slip.end_date <= filters.get("to_date"))

	if filters.get("company"):
		query = query.where(salary_slip.company == filters.get("company"))

	if filters.get("employee"):
		query = query.where(salary_slip.employee == filters.get("employee"))

	if filters.get("currency") and filters.get("currency") != company_currency:
		query = query.where(salary_slip.currency == filters.get("currency"))

	if filters.get("department"):
		query = query.where(salary_slip.department == filters["department"])

	if filters.get("designation"):
		query = query.where(salary_slip.designation == filters["designation"])

	if filters.get("branch"):
		query = query.where(salary_slip.branch == filters["branch"])

	salary_slips = query.run(as_dict=1)
	return salary_slips or []


def get_employee_doj_map():
	employee = frappe.qb.DocType("Employee")
	result = (frappe.qb.from_(employee).select(employee.name, employee.date_of_joining)).run()
	return frappe._dict(result)


def get_salary_slip_details(salary_slips, currency, company_currency, component_type):
	"""Return mapping { salary_slip_name: { salary_component_label: amount } }.
	If currency != company currency, amounts are multiplied by the salary_slip.exchange_rate."""
	salary_slips = [ss.name for ss in salary_slips]

	result = (
		frappe.qb.from_(salary_slip)
		.join(salary_detail)
		.on(salary_slip.name == salary_detail.parent)
		.where((salary_detail.parent.isin(salary_slips)) & (salary_detail.parentfield == component_type))
		.select(salary_detail.parent, salary_detail.salary_component, salary_detail.amount, salary_slip.exchange_rate)
	).run(as_dict=1)

	ss_map = {}
	for d in result:
		ss_map.setdefault(d.parent, frappe._dict()).setdefault(d.salary_component, 0.0)
		if currency and currency != company_currency:
			ss_map[d.parent][d.salary_component] += flt(d.amount) * flt(d.exchange_rate or 1)
		else:
			ss_map[d.parent][d.salary_component] += flt(d.amount)

	return ss_map
