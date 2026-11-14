CREATE EXTERNAL TABLE credit_risk.model_features_prepared_orc (
    `loan_id` string,
    `data_split` string,
    `target` int,
    `loan_amount` double,
    `annual_income` double,
    `dti` double,
    `employment_years` double,
    `employment_missing` int,
    `home_ownership_group` string,
    `purpose` string,
    `verification_status` string,
    `fico_midpoint` double,
    `delinq_2yrs` double,
    `inq_last_6mths` double,
    `open_accounts` double,
    `public_records` double,
    `revolving_balance` double,
    `revolving_utilization` double,
    `utilization_missing` int,
    `total_accounts` double,
    `bankruptcies` double,
    `credit_history_months` int
)
STORED AS ORC
LOCATION '/warehouse/external/model_features_prepared_orc'
TBLPROPERTIES ('orc.compress'='ZLIB');

INSERT OVERWRITE TABLE credit_risk.model_features_prepared_orc
SELECT `loan_id`, `data_split`, `target`, `loan_amount`, `annual_income`, `dti`, `employment_years`, `employment_missing`, `home_ownership_group`, `purpose`, `verification_status`, `fico_midpoint`, `delinq_2yrs`, `inq_last_6mths`, `open_accounts`, `public_records`, `revolving_balance`, `revolving_utilization`, `utilization_missing`, `total_accounts`, `bankruptcies`, `credit_history_months`
FROM credit_risk.model_features_orc;
