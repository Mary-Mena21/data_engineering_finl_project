# The community DuckDB driver's JNI native library is linked against glibc's
# libstdc++, but the official Metabase image is Alpine (musl) and doesn't ship
# it — DuckDBNative fails to load with "Could not initialize class
# org.duckdb.DuckDBNative" / UnsatisfiedLinkError: libstdc++.so.6 not found.
FROM metabase/metabase:v0.62.6
RUN apk add --no-cache libstdc++ gcompat
