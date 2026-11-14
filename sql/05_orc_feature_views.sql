CREATE OR REPLACE VIEW `credit_risk`.`typed_credit_orc` AS WITH parsed AS (
    SELECT
        TRIM(`raw_credit_orc`.`id`) AS `loan_id`,
        TO_DATE(FROM_UNIXTIME(UNIX_TIMESTAMP(
            CONCAT('01-', TRIM(`raw_credit_orc`.`issue_d`)), 'dd-MMM-yyyy'
        ))) AS `issue_date`,
        TO_DATE(FROM_UNIXTIME(UNIX_TIMESTAMP(
            CONCAT('01-', TRIM(`raw_credit_orc`.`earliest_cr_line`)), 'dd-MMM-yyyy'
        ))) AS `earliest_credit_date`,
        TRIM(`raw_credit_orc`.`loan_status`) AS `loan_status`,
        CAST(TRIM(`raw_credit_orc`.`loan_amnt`) AS DOUBLE) AS `loan_amount`,
        CAST(REGEXP_EXTRACT(TRIM(`raw_credit_orc`.`term`), '^([0-9]+)', 1)
             AS INT) AS `term_months`,
        CAST(NULLIF(TRIM(`raw_credit_orc`.`annual_inc`), '') AS DOUBLE) AS `annual_income`,
        CAST(NULLIF(TRIM(`raw_credit_orc`.`dti`), '') AS DOUBLE) AS `dti`,
        CASE
            WHEN TRIM(`raw_credit_orc`.`emp_length`) = '' OR `raw_credit_orc`.`emp_length` IS NULL THEN NULL
            WHEN TRIM(`raw_credit_orc`.`emp_length`) = '< 1 year' THEN 0
            WHEN TRIM(`raw_credit_orc`.`emp_length`) = '10+ years' THEN 10
            ELSE CAST(REGEXP_EXTRACT(
                TRIM(`raw_credit_orc`.`emp_length`), '^([0-9]+)', 1
            ) AS INT)
        END AS `employment_years`,
        TRIM(`raw_credit_orc`.`home_ownership`) AS `home_ownership`,
        TRIM(`raw_credit_orc`.`purpose`) AS `purpose`,
        TRIM(`raw_credit_orc`.`verification_status`) AS `verification_status`,
        CAST(NULLIF(TRIM(`raw_credit_orc`.`fico_range_low`), '') AS DOUBLE) AS `fico_low`,
        CAST(NULLIF(TRIM(`raw_credit_orc`.`fico_range_high`), '') AS DOUBLE) AS `fico_high`,
        CAST(NULLIF(TRIM(`raw_credit_orc`.`delinq_2yrs`), '') AS DOUBLE) AS `delinq_2yrs`,
        CAST(NULLIF(TRIM(`raw_credit_orc`.`inq_last_6mths`), '') AS DOUBLE) AS `inq_last_6mths`,
        CAST(NULLIF(TRIM(`raw_credit_orc`.`open_acc`), '') AS DOUBLE) AS `open_accounts`,
        CAST(NULLIF(TRIM(`raw_credit_orc`.`pub_rec`), '') AS DOUBLE) AS `public_records`,
        CAST(NULLIF(TRIM(`raw_credit_orc`.`revol_bal`), '') AS DOUBLE) AS `revolving_balance`,
        CAST(NULLIF(TRIM(`raw_credit_orc`.`revol_util`), '') AS DOUBLE) AS `revolving_utilization`,
        CAST(NULLIF(TRIM(`raw_credit_orc`.`total_acc`), '') AS DOUBLE) AS `total_accounts`,
        CAST(NULLIF(TRIM(`raw_credit_orc`.`pub_rec_bankruptcies`), '') AS DOUBLE)
            AS `bankruptcies`
    FROM `credit_risk`.`raw_credit_orc`
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

CREATE OR REPLACE VIEW `credit_risk`.`model_features_orc` AS SELECT
    `t`.`loan_id`,
    `t`.`data_split`,
    `t`.`target`,
    `t`.`loan_amount`,
    `t`.`annual_income`,
    `t`.`dti`,
    COALESCE(
        CAST(`t`.`employment_years` AS DOUBLE),
        `s`.`employment_fill`
    ) AS `employment_years`,
    CASE WHEN `t`.`employment_years` IS NULL
         THEN 1 ELSE 0 END AS `employment_missing`,
    `t`.`home_ownership_group`,
    `t`.`purpose`,
    `t`.`verification_status`,
    (`t`.`fico_low` + `t`.`fico_high`) / 2.0 AS `fico_midpoint`,
    `t`.`delinq_2yrs`,
    `t`.`inq_last_6mths`,
    `t`.`open_accounts`,
    `t`.`public_records`,
    `t`.`revolving_balance`,
    COALESCE(
        `t`.`revolving_utilization`,
        `s`.`utilization_fill`
    ) AS `revolving_utilization`,
    CASE WHEN `t`.`revolving_utilization` IS NULL
         THEN 1 ELSE 0 END AS `utilization_missing`,
    `t`.`total_accounts`,
    `t`.`bankruptcies`,
    CAST(
        MONTHS_BETWEEN(`t`.`issue_date`, `t`.`earliest_credit_date`)
        AS INT
    ) AS `credit_history_months`
FROM `credit_risk`.`typed_credit_orc` `t`
CROSS JOIN `credit_risk`.`preprocessing_stats` `s`;
