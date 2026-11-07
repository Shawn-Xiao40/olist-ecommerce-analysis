# Official Superset image + DuckDB driver
FROM apache/superset:4.1.2

USER root
# Keep the duckdb version in sync with the project's requirements.txt
RUN pip install --no-cache-dir duckdb==1.2.2 duckdb-engine==0.17.0
USER superset
