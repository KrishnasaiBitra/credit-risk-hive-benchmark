WITH combined AS (
    SELECT `loan_id`, `data_split`, `target`, `loan_amount`, `annual_income`, `dti`, `employment_years`, `employment_missing`, `home_ownership_group`, `purpose`, `verification_status`, `fico_midpoint`, `delinq_2yrs`, `inq_last_6mths`, `open_accounts`, `public_records`, `revolving_balance`, `revolving_utilization`, `utilization_missing`, `total_accounts`, `bankruptcies`, `credit_history_months`, 1 AS source_weight
    FROM credit_risk.model_features_orc

    UNION ALL

    SELECT `loan_id`, `data_split`, `target`, `loan_amount`, `annual_income`, `dti`, `employment_years`, `employment_missing`, `home_ownership_group`, `purpose`, `verification_status`, `fico_midpoint`, `delinq_2yrs`, `inq_last_6mths`, `open_accounts`, `public_records`, `revolving_balance`, `revolving_utilization`, `utilization_missing`, `total_accounts`, `bankruptcies`, `credit_history_months`, -1 AS source_weight
    FROM credit_risk.model_features_prepared_orc
),
differences AS (
    SELECT `loan_id`, `data_split`, `target`, `loan_amount`, `annual_income`, `dti`, `employment_years`, `employment_missing`, `home_ownership_group`, `purpose`, `verification_status`, `fico_midpoint`, `delinq_2yrs`, `inq_last_6mths`, `open_accounts`, `public_records`, `revolving_balance`, `revolving_utilization`, `utilization_missing`, `total_accounts`, `bankruptcies`, `credit_history_months`, SUM(source_weight) AS count_difference
    FROM combined
    GROUP BY `loan_id`, `data_split`, `target`, `loan_amount`, `annual_income`, `dti`, `employment_years`, `employment_missing`, `home_ownership_group`, `purpose`, `verification_status`, `fico_midpoint`, `delinq_2yrs`, `inq_last_6mths`, `open_accounts`, `public_records`, `revolving_balance`, `revolving_utilization`, `utilization_missing`, `total_accounts`, `bankruptcies`, `credit_history_months`
    HAVING SUM(source_weight) <> 0
)
SELECT COUNT(*) AS mismatched_row_patterns
FROM differences;
