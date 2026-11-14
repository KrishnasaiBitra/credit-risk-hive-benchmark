WITH combined AS (
    SELECT `id`, `issue_d`, `loan_status`, `loan_amnt`, `term`, `annual_inc`, `dti`, `emp_length`, `home_ownership`, `purpose`, `verification_status`, `fico_range_low`, `fico_range_high`, `delinq_2yrs`, `inq_last_6mths`, `open_acc`, `pub_rec`, `revol_bal`, `revol_util`, `total_acc`, `pub_rec_bankruptcies`, `earliest_cr_line`, 1 AS source_weight
    FROM credit_risk.raw_credit

    UNION ALL

    SELECT `id`, `issue_d`, `loan_status`, `loan_amnt`, `term`, `annual_inc`, `dti`, `emp_length`, `home_ownership`, `purpose`, `verification_status`, `fico_range_low`, `fico_range_high`, `delinq_2yrs`, `inq_last_6mths`, `open_acc`, `pub_rec`, `revol_bal`, `revol_util`, `total_acc`, `pub_rec_bankruptcies`, `earliest_cr_line`, -1 AS source_weight
    FROM credit_risk.raw_credit_orc
),
differences AS (
    SELECT `id`, `issue_d`, `loan_status`, `loan_amnt`, `term`, `annual_inc`, `dti`, `emp_length`, `home_ownership`, `purpose`, `verification_status`, `fico_range_low`, `fico_range_high`, `delinq_2yrs`, `inq_last_6mths`, `open_acc`, `pub_rec`, `revol_bal`, `revol_util`, `total_acc`, `pub_rec_bankruptcies`, `earliest_cr_line`, SUM(source_weight) AS count_difference
    FROM combined
    GROUP BY `id`, `issue_d`, `loan_status`, `loan_amnt`, `term`, `annual_inc`, `dti`, `emp_length`, `home_ownership`, `purpose`, `verification_status`, `fico_range_low`, `fico_range_high`, `delinq_2yrs`, `inq_last_6mths`, `open_acc`, `pub_rec`, `revol_bal`, `revol_util`, `total_acc`, `pub_rec_bankruptcies`, `earliest_cr_line`
    HAVING SUM(source_weight) <> 0
)
SELECT COUNT(*) AS mismatched_row_patterns
FROM differences;
