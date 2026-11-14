# Hadoop and Hive setup handoff

> Current project status: modelling, pipeline experiments and final test evaluation are complete.
> For the current reproducibility workflow see [REPRODUCE.md](../REPRODUCE.md).
> The status below is a historical snapshot from initial setup, before data loading.


## Status

Infrastructure setup is complete. No Lending Club records have been loaded into HDFS,
and model training has not started. The next phase is dataset auditing and preparation.

Verified:
- One live HDFS DataNode; replication target is 1.
- PostgreSQL Metastore database initialised.
- HiveServer2 SQL connection and Metastore access.
- One registered YARN NodeManager.
- A text-table GROUP BY completed both its map and reducer on Tez/YARN.
- An external ORC table was created, two test rows were written, and GROUP BY returned:
  `hive_ok,1` and `storage_ok,1`.

These small smoke tests establish functionality, not full-dataset performance.

## Versions

- HDFS servers: Apache Hadoop 3.5.0.
- Hive: 4.2.1; bundled Hadoop client/YARN services: 3.4.1.
- Tez: 0.10.5, packaged from the installed Hive image.
- PostgreSQL: image postgres:17-bookworm; exact image digests recorded in
  ../results/setup-image-versions.json.

The mixed HDFS server/client versions passed the smoke tests. Freeze this environment
for benchmarking and document both versions. Full-scale compatibility is not yet tested.

## Open the project

Run in Ubuntu:

```bash
cd /mnt/c/Users/krish/Desktop/big-data-project/infrastructure
```

The .env file includes all Compose files automatically.

## Start and check

Ensure the Docker engine is running, then:

```bash
docker compose up -d
docker compose ps -a
```

Allow startup to finish. These checks should show one RUNNING worker and one live DataNode:

```bash
docker compose exec resourcemanager /opt/hadoop/bin/yarn node -list
docker compose exec namenode hdfs dfsadmin -report
```

Connect to Hive interactively:

```bash
docker compose exec hiveserver2 beeline -u jdbc:hive2://localhost:10000/credit_risk -n hive
```

Then run:

```sql
SELECT message, COUNT(*) FROM setup_check_orc GROUP BY message;
```

Exit Beeline with `!quit`.

If services were restarted while a query was open, close the client and restart HiveServer2
to discard stale Tez sessions, then reconnect:

```bash
docker compose restart hiveserver2
```

## Stop without deleting data

```bash
docker compose stop
```

Do not use `docker compose down -v`: that removes the persistent HDFS and database volumes.

## Local dashboards

- HDFS: http://localhost:9870
- HiveServer2: http://localhost:10002
- YARN: http://localhost:8088

## Configuration notes

- Data and PostgreSQL metadata use persistent named Docker volumes.
- NodeManager log-volume ownership was corrected to the hive user (UID 1000).
- YARN uses the Hive image to match the Hadoop libraries and Java runtime used by Hive.
- YARN daemon HADOOP_OPTS includes the java.lang module access needed by its web UI library.
- The custom tez-site.xml replaces the image's external/LLAP-oriented defaults with a
  YARN-submitted session using the runtime archive at /apps/tez/tez-0.10.5.tar.gz in HDFS.
- YARN advertises 2048 MB and two vcores for tasks. Tez AM is 768 MB and tasks are 512 MB.
  These are development settings; tune and record resource settings for real benchmarks.
- HDFS permissions remain enabled; /user/hive and warehouse directories belong to hive.
- Notification API authorisation is disabled for this isolated, unauthenticated local lab.
  This setup is not a production security configuration.
- Existing logging binding warnings are still present; the tested queries succeeded.

## Files and evidence

- compose.yaml: HDFS
- compose.hive.yaml: PostgreSQL
- compose.metastore.yaml: Metastore
- compose.hiveserver.yaml: HiveServer2
- compose.yarn.yaml: YARN
- hive-conf/: shared XML settings
- runtime/tez-0.10.5.tar.gz: matching Tez archive
- backup-pre-yarn-*/: previous configuration backups
- ../sql/setup-check.sql: two-row ORC smoke test
- ../results/setup-orc-check.log: captured ORC verification output

The archive/ folder and source paper were left unchanged.
