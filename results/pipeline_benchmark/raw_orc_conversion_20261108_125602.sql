CREATE TABLE credit_risk.raw_orc_timing_20261108_125602 (`id` string, `issue_d` string, `loan_status` string, `loan_amnt` string, `term` string, `annual_inc` string, `dti` string, `emp_length` string, `home_ownership` string, `purpose` string, `verification_status` string, `fico_range_low` string, `fico_range_high` string, `delinq_2yrs` string, `inq_last_6mths` string, `open_acc` string, `pub_rec` string, `revol_bal` string, `revol_util` string, `total_acc` string, `pub_rec_bankruptcies` string, `earliest_cr_line` string)
STORED AS ORC
TBLPROPERTIES (
    'orc.compress'='ZLIB',
    'transactional'='false'
);

INSERT OVERWRITE TABLE credit_risk.raw_orc_timing_20261108_125602
SELECT `id`, `issue_d`, `loan_status`, `loan_amnt`, `term`, `annual_inc`, `dti`, `emp_length`, `home_ownership`, `purpose`, `verification_status`, `fico_range_low`, `fico_range_high`, `delinq_2yrs`, `inq_last_6mths`, `open_acc`, `pub_rec`, `revol_bal`, `revol_util`, `total_acc`, `pub_rec_bankruptcies`, `earliest_cr_line`
FROM credit_risk.raw_credit;
