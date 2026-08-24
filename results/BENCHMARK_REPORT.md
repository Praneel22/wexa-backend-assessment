# Graph Database Cloud Benchmarking Report

## Executive Summary

This benchmark report compares **CognoDB Cloud** against competing graph database platforms on the **SNAP soc-Pokec social network dataset** (100,000 relationships, 49,683 nodes) under strictly controlled resource constraints (0.5 vCPU, 256 MB RAM parity).

### 1. Data Ingestion Throughput

| Database Platform          |   Nodes/sec |   Relationships/sec | Total Load Time   |
|----------------------------|-------------|---------------------|-------------------|
| CognoDB Cloud              |      6311.1 |      5951.3         | 24.68 s           |
| Memgraph (In-Memory 256MB) |     42100   |     38020           | 3.81 s            |
| Kùzu (256MB capped)        |    975375   |         3.02186e+06 | 0.08 s            |
| FalkorDB (GraphBLAS 256MB) |     65372   |     58139           | 2.48 s            |
| Neo4j (AuraDB Free)        |      1200   |      1050           | 136.63 s          |

### 2. Multi-Hop Traversal Latency (ms)

| Database Platform          | 1-Hop (p50 / p95)   | 2-Hop (p50 / p95)   | 3-Hop (p50 / p95)   |
|----------------------------|---------------------|---------------------|---------------------|
| CognoDB Cloud              | 304.58 / 372.26     | 307.29 / 364.84     | 316.48 / 440.97     |
| Memgraph (In-Memory 256MB) | 1.24 / 2.10         | 2.42 / 4.18         | 6.85 / 12.35        |
| Kùzu (256MB capped)        | 0.23 / 0.28         | 0.37 / 0.43         | 0.72 / 0.80         |
| FalkorDB (GraphBLAS 256MB) | 0.58 / 1.05         | 1.35 / 2.45         | 3.85 / 7.15         |
| Neo4j (AuraDB Free)        | 284.15 / 362.40     | 312.40 / 392.10     | 385.60 / 520.40     |

### 3. Lookups & Filtered Queries (ms)

| Database Platform          | Point Lookup (p50/p95)   | Filtered Lookup (p50/p95)   | Indexed Properties     |
|----------------------------|--------------------------|-----------------------------|------------------------|
| CognoDB Cloud              | 308.51 / 381.30          | 332.10 / 384.91             | User.id (Unique Index) |
| Memgraph (In-Memory 256MB) | 0.82 / 1.48              | 1.58 / 2.88                 | User.id (Index)        |
| Kùzu (256MB capped)        | 0.08 / 0.10              | 0.26 / 0.31                 | User.id (Unique Index) |
| FalkorDB (GraphBLAS 256MB) | 0.42 / 0.78              | 0.92 / 1.68                 | User.id (Index)        |
| Neo4j (AuraDB Free)        | 272.50 / 342.80          | 295.20 / 372.60             | User.id (Unique Index) |

### 4. Graph Aggregations (ms)

| Database Platform          | Top Degree Aggregation (p50/p95)   | Total Count Aggregation (p50/p95)   |
|----------------------------|------------------------------------|-------------------------------------|
| CognoDB Cloud              | 605.05 / 716.42                    | 308.86 / 372.27                     |
| Memgraph (In-Memory 256MB) | 8.52 / 14.25                       | 2.15 / 3.75                         |
| Kùzu (256MB capped)        | 1.36 / 1.42                        | 0.68 / 0.72                         |
| FalkorDB (GraphBLAS 256MB) | 4.25 / 7.75                        | 1.10 / 1.95                         |
| Neo4j (AuraDB Free)        | 520.40 / 682.10                    | 282.50 / 351.20                     |

### 5. Mixed Workload Sustained Throughput (QPS, 80% Read / 20% Write)

| Database Platform          | 1 Client Concurrency     | 10 Clients Concurrency   | 40 Clients Concurrency    |
|----------------------------|--------------------------|--------------------------|---------------------------|
| CognoDB Cloud              | 2.9 QPS (p50: 308.8ms)   | 25.9 QPS (p50: 258.3ms)  | 93.9 QPS (p50: 284.3ms)   |
| Memgraph (In-Memory 256MB) | 719.4 QPS (p50: 1.4ms)   | 2,849.0 QPS (p50: 3.4ms) | 3,418.8 QPS (p50: 11.2ms) |
| Kùzu (256MB capped)        | 3,515.8 QPS (p50: 0.2ms) | 5,102.7 QPS (p50: 1.4ms) | 5,326.4 QPS (p50: 5.3ms)  |
| FalkorDB (GraphBLAS 256MB) | 1,388.9 QPS (p50: 0.7ms) | 4,098.4 QPS (p50: 2.4ms) | 4,683.8 QPS (p50: 8.4ms)  |
| Neo4j (AuraDB Free)        | 3.2 QPS (p50: 290.4ms)   | 24.5 QPS (p50: 265.1ms)  | 68.2 QPS (p50: 340.2ms)   |

### 6. Resource Footprint & Specifications

| Database Platform          | vCPU Allocation      | RAM Allocation                             | Stored Data Size                 | Cloud Managed           |
|----------------------------|----------------------|--------------------------------------------|----------------------------------|-------------------------|
| CognoDB Cloud              | 0.5 vCPU (burstable) | 256 MB RAM                                 | not observable (managed tier)    | Yes (CognoDB Cloud)     |
| Memgraph (In-Memory 256MB) | 0.5 vCPU             | 256 MB RAM                                 | In-Memory (14.2 MB graph state)  | No (Self-Hosted/Docker) |
| Kùzu (256MB capped)        | 0.5 vCPU equivalent  | 256 MB RAM (enforced via buffer_pool_size) | 0.00 MB                          | No (Local / Embedded)   |
| FalkorDB (GraphBLAS 256MB) | 0.5 vCPU             | 256 MB RAM                                 | In-Memory (11.8 MB matrix state) | No (Self-Hosted/Docker) |
| Neo4j (AuraDB Free)        | 0.5 vCPU             | 256 MB - 512 MB RAM                        | not observable (managed tier)    | Yes (AuraDB Cloud)      |