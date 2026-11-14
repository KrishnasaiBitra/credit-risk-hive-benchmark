CREATE EXTERNAL TABLE `credit_risk`.`raw_credit`(
  `id` string, 
  `issue_d` string, 
  `loan_status` string, 
  `loan_amnt` string, 
  `term` string, 
  `annual_inc` string, 
  `dti` string, 
  `emp_length` string, 
  `home_ownership` string, 
  `purpose` string, 
  `verification_status` string, 
  `fico_range_low` string, 
  `fico_range_high` string, 
  `delinq_2yrs` string, 
  `inq_last_6mths` string, 
  `open_acc` string, 
  `pub_rec` string, 
  `revol_bal` string, 
  `revol_util` string, 
  `total_acc` string, 
  `pub_rec_bankruptcies` string, 
  `earliest_cr_line` string)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.serde2.OpenCSVSerde' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.mapred.TextInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION
  'hdfs://namenode:8020/credit-risk/raw/cohort'
TBLPROPERTIES (
  'bucketing_version'='2', 
  'skip.header.line.count'='1', 
  'transient_lastDdlTime'='1794117432');
