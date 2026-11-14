CREATE EXTERNAL TABLE `credit_risk`.`preprocessing_stats`(
  `training_rows` bigint, 
  `employment_fill` double, 
  `utilization_fill` double)
ROW FORMAT SERDE 
  'org.apache.hadoop.hive.ql.io.orc.OrcSerde' 
STORED AS INPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.orc.OrcInputFormat' 
OUTPUTFORMAT 
  'org.apache.hadoop.hive.ql.io.orc.OrcOutputFormat'
LOCATION
  'hdfs://namenode:8020/warehouse/external/preprocessing_stats'
TBLPROPERTIES (
  'bucketing_version'='2', 
  'transient_lastDdlTime'='1794118577');
