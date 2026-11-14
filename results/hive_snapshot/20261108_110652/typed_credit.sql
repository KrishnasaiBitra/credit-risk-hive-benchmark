CREATE VIEW `credit_risk`.`typed_credit` AS WITH parsed AS (
    SELECT
        TRIM(`raw_credit`.`id`) AS `loan_id`,
        TO_DATE(FROM_UNIXTIME(UNIX_TIMESTAMP(
            CONCAT('01-', TRIM(`raw_credit`.`issue_d`)), 'dd-MMM-yyyy'
        ))) AS `issue_date`,
        TO_DATE(FROM_UNIXTIME(UNIX_TIMESTAMP(
            CONCAT('01-', TRIM(`raw_credit`.`earliest_cr_line`)), 'dd-MMM-yyyy'
        ))) AS `earliest_credit_date`,
        TRIM(`raw_credit`.`loan_status`) AS `loan_status`,
        CAST(TRIM(`raw_credit`.`loan_amnt`) AS DOUBLE) AS `loan_amount`,
        CAST(REGEXP_EXTRACT(TRIM(`raw_credit`.`term`), '^([0-9]+)', 1)
             AS INT) AS `term_months`,
        CAST(NULLIF(TRIM(`raw_credit`.`annual_inc`), '') AS DOUBLE) AS `annual_income`,
        CAST(NULLIF(TRIM(`raw_credit`.`dti`), '') AS DOUBLE) AS `dti`,
        CASE
            WHEN TRIM(`raw_credit`.`emp_length`) = '' OR `raw_credit`.`emp_length` IS NULL THEN NULL
            WHEN TRIM(`raw_credit`.`emp_length`) = '< 1 year' THEN 0
            WHEN TRIM(`raw_credit`.`emp_length`) = '10+ years' THEN 10
            ELSE CAST(REGEXP_EXTRACT(
                TRIM(`raw_credit`.`emp_length`), '^([0-9]+)', 1
            ) AS INT)
        END AS `employment_years`,
        TRIM(`raw_credit`.`home_ownership`) AS `home_ownership`,
        TRIM(`raw_credit`.`purpose`) AS `purpose`,
        TRIM(`raw_credit`.`verification_status`) AS `verification_status`,
        CAST(NULLIF(TRIM(`raw_credit`.`fico_range_low`), '') AS DOUBLE) AS `fico_low`,
        CAST(NULLIF(TRIM(`raw_credit`.`fico_range_high`), '') AS DOUBLE) AS `fico_high`,
        CAST(NULLIF(TRIM(`raw_credit`.`delinq_2yrs`), '') AS DOUBLE) AS `delinq_2yrs`,
        CAST(NULLIF(TRIM(`raw_credit`.`inq_last_6mths`), '') AS DOUBLE) AS `inq_last_6mths`,
        CAST(NULLIF(TRIM(`raw_credit`.`open_acc`), '') AS DOUBLE) AS `open_accounts`,
        CAST(NULLIF(TRIM(`raw_credit`.`pub_rec`), '') AS DOUBLE) AS `public_records`,
        CAST(NULLIF(TRIM(`raw_credit`.`revol_bal`), '') AS DOUBLE) AS `revolving_balance`,
        CAST(NULLIF(TRIM(`raw_credit`.`revol_util`), '') AS DOUBLE) AS `revolving_utilization`,
        CAST(NULLIF(TRIM(`raw_credit`.`total_acc`), '') AS DOUBLE) AS `total_accounts`,
        CAST(NULLIF(TRIM(`raw_credit`.`pub_rec_bankruptcies`), '') AS DOUBLE)
            AS `bankruptcies`
    FROM `credit_risk`.`raw_credit`
)
SELECT
    `parsed`.`loan_id`, `parsed`.`issue_date`, `parsed`.`earliest_credit_date`, `parsed`.`loan_status`, `parsed`.`loan_amount`, `parsed`.`term_months`, `parsed`.`annual_income`, `parsed`.`dti`, `parsed`.`employment_years`, `parsed`.`home_ownership`, `parsed`.`purpose`, `parsed`.`verification_status`, `parsed`.`fico_low`, `parsed`.`fico_high`, `parsed`.`delinq_2yrs`, `parsed`.`inq_last_6mths`, `parsed`.`open_accounts`, `parsed`.`public_records`, `parsed`.`revolving_balance`, `parsed`.`revolving_utilization`, `parsed`.`total_accounts`, `parsed`.`bankruptcies`,
    CASE
        WHEN `parsed`.`loan_status` = 'Charged Off' THEN 1
        WHEN `parsed`.`loan_status` = 'Fully Paid' THEN 0
        ELSE NULL
    END AS `target`,
    CASE
        WHEN `parsed`.`issue_date` >= CAST('2012-01-01' AS DATE)
         AND `parsed`.`issue_date` < CAST('2014-01-01' AS DATE) THEN 'train'
        WHEN `parsed`.`issue_date` >= CAST('2014-01-01' AS DATE)
         AND `parsed`.`issue_date` < CAST('2014-07-01' AS DATE) THEN 'validation'
        WHEN `parsed`.`issue_date` >= CAST('2014-07-01' AS DATE)
         AND `parsed`.`issue_date` < CAST('2015-01-01' AS DATE) THEN 'test'
        ELSE 'invalid'
    END AS `data_split`,
    CASE
        WHEN `parsed`.`home_ownership` IN ('MORTGAGE', 'RENT', 'OWN')
            THEN `parsed`.`home_ownership`
        ELSE 'OTHER_UNKNOWN'
    END AS `home_ownership_group`
FROM parsed;
