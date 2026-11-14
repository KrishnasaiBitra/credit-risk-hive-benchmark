CREATE EXTERNAL TABLE credit_risk.raw_credit_orc (
    `id` STRING,
    `issue_d` STRING,
    `loan_status` STRING,
    `loan_amnt` STRING,
    `term` STRING,
    `annual_inc` STRING,
    `dti` STRING,
    `emp_length` STRING,
    `home_ownership` STRING,
    `purpose` STRING,
    `verification_status` STRING,
    `fico_range_low` STRING,
    `fico_range_high` STRING,
    `delinq_2yrs` STRING,
    `inq_last_6mths` STRING,
    `open_acc` STRING,
    `pub_rec` STRING,
    `revol_bal` STRING,
    `revol_util` STRING,
    `total_acc` STRING,
    `pub_rec_bankruptcies` STRING,
    `earliest_cr_line` STRING
)
STORED AS ORC
LOCATION '/warehouse/external/raw_credit_orc'
TBLPROPERTIES ('orc.compress'='ZLIB');

INSERT OVERWRITE TABLE credit_risk.raw_credit_orc
SELECT `id`, `issue_d`, `loan_status`, `loan_amnt`, `term`, `annual_inc`, `dti`, `emp_length`, `home_ownership`, `purpose`, `verification_status`, `fico_range_low`, `fico_range_high`, `delinq_2yrs`, `inq_last_6mths`, `open_acc`, `pub_rec`, `revol_bal`, `revol_util`, `total_acc`, `pub_rec_bankruptcies`, `earliest_cr_line`
FROM credit_risk.raw_credit;
