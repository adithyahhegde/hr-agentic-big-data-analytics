# Canonical HR Schema

## Implemented mapping subset

The foundation recognizes only `employee_id`, `department`, `job_role`, `age`, `tenure_years`, `salary`, `performance_rating`, `attrition`, and `overtime` via explicit aliases. Every other source field remains `unknown`; this is intentional. Alias match is evidence, not a permanent user-confirmed schema version. An `attrition` candidate gains binary-value evidence only for a known binary representation.

## Purpose
Define a stable internal vocabulary so source datasets can use different names without forcing downstream analytics code to know every vendor-specific spelling.

## Initial canonical fields
| Canonical field | Type | Semantic category | Example aliases |
|---|---|---|---|
| employee_id | string | identifier | emp_id, emp_no, employee#, staff_id |
| department | category | organization | dept, division |
| job_role | category | job | role, position, designation |
| tenure | numeric | workforce | years_at_company, yrs_co |
| salary | numeric | compensation | sal, annual_income, pay |
| performance_rating | numeric/category | performance | perf_rt, performance_score |
| job_satisfaction | numeric/category | engagement | job_sat, satisfaction |
| overtime | boolean/category/numeric | attendance/workload | ot, overtime_flag, ot_hrs |
| attrition | boolean/category | employment outcome | left_org, exited, turnover |
| promotion | boolean/category/date | career outcome | promoted, promotion_status |

## Mapping pipeline
1. Normalize formatting without destroying semantic information.
2. Match exact canonical names and curated aliases.
3. Use datatype/value-pattern evidence.
4. Use relationship/table context where available.
5. Invoke local semantic model only for ambiguous mappings when enabled.
6. Assign confidence and reason codes.
7. Validate required fields for the selected objective.
8. Ask for user confirmation when confidence is below the configured threshold.

## Important rule
Never assume a column is semantically correct solely because its name is similar. `cust_id`, for example, may be a customer identifier rather than an employee identifier. Value patterns, table context, dataset context, and user confirmation can be necessary.

## Extensibility
The canonical schema is not limited to the initial fields. New concepts must be added with datatype, semantic category, aliases, validation rules, and objective dependencies.
