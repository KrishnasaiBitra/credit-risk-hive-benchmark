-- Infrastructure smoke test only; no borrower data is loaded.
CREATE EXTERNAL TABLE IF NOT EXISTS credit_risk.setup_check_orc (
  id INT,
  message STRING
)
STORED AS ORC
LOCATION 'hdfs://namenode:8020/warehouse/external/setup_check_orc';
INSERT OVERWRITE TABLE credit_risk.setup_check_orc
SELECT id, message FROM credit_risk.setup_check;
SELECT message, COUNT(*) AS row_count
FROM credit_risk.setup_check_orc
GROUP BY message;
