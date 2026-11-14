CREATE VIEW `credit_risk`.`model_features` AS SELECT
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
FROM `credit_risk`.`typed_credit` `t`
CROSS JOIN `credit_risk`.`preprocessing_stats` `s`;
