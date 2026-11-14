CREATE OR REPLACE VIEW credit_risk.typed_credit AS
WITH parsed AS (
    SELECT
        TRIM(id) AS loan_id,

        TO_DATE(FROM_UNIXTIME(UNIX_TIMESTAMP(
            CONCAT('01-', TRIM(issue_d)), 'dd-MMM-yyyy'
        ))) AS issue_date,

        TO_DATE(FROM_UNIXTIME(UNIX_TIMESTAMP(
            CONCAT('01-', TRIM(earliest_cr_line)), 'dd-MMM-yyyy'
        ))) AS earliest_credit_date,

        TRIM(loan_status) AS loan_status,
        CAST(TRIM(loan_amnt) AS DOUBLE) AS loan_amount,
        CAST(REGEXP_EXTRACT(TRIM(term), '^([0-9]+)', 1)
             AS INT) AS term_months,
        CAST(NULLIF(TRIM(annual_inc), '') AS DOUBLE) AS annual_income,
        CAST(NULLIF(TRIM(dti), '') AS DOUBLE) AS dti,

        CASE
            WHEN TRIM(emp_length) = '' OR emp_length IS NULL THEN NULL
            WHEN TRIM(emp_length) = '< 1 year' THEN 0
            WHEN TRIM(emp_length) = '10+ years' THEN 10
            ELSE CAST(REGEXP_EXTRACT(
                TRIM(emp_length), '^([0-9]+)', 1
            ) AS INT)
        END AS employment_years,

        TRIM(home_ownership) AS home_ownership,
        TRIM(purpose) AS purpose,
        TRIM(verification_status) AS verification_status,

        CAST(NULLIF(TRIM(fico_range_low), '') AS DOUBLE) AS fico_low,
        CAST(NULLIF(TRIM(fico_range_high), '') AS DOUBLE) AS fico_high,
        CAST(NULLIF(TRIM(delinq_2yrs), '') AS DOUBLE) AS delinq_2yrs,
        CAST(NULLIF(TRIM(inq_last_6mths), '') AS DOUBLE) AS inq_last_6mths,
        CAST(NULLIF(TRIM(open_acc), '') AS DOUBLE) AS open_accounts,
        CAST(NULLIF(TRIM(pub_rec), '') AS DOUBLE) AS public_records,
        CAST(NULLIF(TRIM(revol_bal), '') AS DOUBLE) AS revolving_balance,
        CAST(NULLIF(TRIM(revol_util), '') AS DOUBLE) AS revolving_utilization,
        CAST(NULLIF(TRIM(total_acc), '') AS DOUBLE) AS total_accounts,
        CAST(NULLIF(TRIM(pub_rec_bankruptcies), '') AS DOUBLE)
            AS bankruptcies

    FROM credit_risk.raw_credit
)
SELECT
    parsed.*,

    CASE
        WHEN loan_status = 'Charged Off' THEN 1
        WHEN loan_status = 'Fully Paid' THEN 0
        ELSE NULL
    END AS target,

    CASE
        WHEN issue_date >= CAST('2012-01-01' AS DATE)
         AND issue_date < CAST('2014-01-01' AS DATE) THEN 'train'
        WHEN issue_date >= CAST('2014-01-01' AS DATE)
         AND issue_date < CAST('2014-07-01' AS DATE) THEN 'validation'
        WHEN issue_date >= CAST('2014-07-01' AS DATE)
         AND issue_date < CAST('2015-01-01' AS DATE) THEN 'test'
        ELSE 'invalid'
    END AS data_split,

    CASE
        WHEN home_ownership IN ('MORTGAGE', 'RENT', 'OWN')
            THEN home_ownership
        ELSE 'OTHER_UNKNOWN'
    END AS home_ownership_group

FROM parsed;
