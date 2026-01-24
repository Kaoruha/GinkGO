# Data Worker Implementation - Technical Research Document

## Overview

This document documents technical decisions and implementation patterns for the Data Worker component in the Ginkgo quantitative trading system. The Data Worker will consume Kafka messages requesting data updates, fetch data from external sources, and batch-write to ClickHouse.

---

## 1. Existing Worker Pattern Analysis

### 1.1 Worker Architecture Pattern

**Decision**: Use `threading.Thread`-based worker pattern with `threading.Event` for graceful shutdown

**Rationale**:
- Both TaskTimer and NotificationWorker use `threading.Thread` inheritance pattern
- `threading.Event` provides clean, blocking-safe shutdown signal
- Proven pattern in production with existing workers
- Simple debugging compared to asyncio/multiprocessing

**Alternatives Considered**:
- **asyncio**: Rejected - NotificationWorker uses threading, mixing models would complicate codebase
- **multiprocessing**: Rejected - Overkill for I/O-bound Kafka consumption, adds shared memory complexity
- **celery/rq**: Rejected - External dependency, existing workers don't use it

**Implementation Notes**:

```python
# Pattern from NotificationWorker (/home/kaoru/Ginkgo/src/ginkgo/notifier/workers/notification_worker.py)
class DataWorker(threading.Thread):
    def __init__(self, ...):
        super().__init__(daemon=True)
        self._stop_event = threading.Event()
        self._status = WorkerStatus.STOPPED

    def start(self) -> bool:
        self._status = WorkerStatus.STARTING
        self._stop_event.clear()
        # Create Kafka Consumer
        self._consumer = GinkgoConsumer(...)
        # Start thread
        super().start()
        self._status = WorkerStatus.RUNNING

    def stop(self, timeout: float = 30.0) -> bool:
        self._status = WorkerStatus.STOPPING
        self._stop_event.set()
        self.join(timeout=timeout)
        # Close consumer
        self._consumer.close()
```

**Status Management Pattern**:
```python
class WorkerStatus(IntEnum):
    STOPPED = 0
    STARTING = 1
    RUNNING = 2
    STOPPING = 3
    ERROR = 4
```

---

### 1.2 Kafka Consumer Setup

**Decision**: Use existing `GinkgoConsumer` wrapper from `/home/kaoru/Ginkgo/src/ginkgo/data/drivers/ginkgo_kafka.py`

**Rationale**:
- Consistent with NotificationWorker pattern
- Handles connection, deserialization, and error recovery
- Already integrated with GCONF for bootstrap servers
- Supports consumer groups for multi-instance deployment

**Implementation Notes**:

```python
# From GinkgoConsumer implementation
from ginkgo.data.drivers.ginkgo_kafka import GinkgoConsumer

self._consumer = GinkgoConsumer(
    topic=KafkaTopics.DATA_UPDATE,
    group_id="data_worker_group",  # Enable horizontal scaling
    offset="earliest"
)

# Check connection
if not self._consumer.is_connected:
    GLOG.ERROR(f"Failed to connect to Kafka for topic '{topic}'")
    return False
```

**Consumer Configuration** (from `ginkgo_kafka.py`):
- `max_poll_interval_ms=1800000` (30 minutes) - allows long data fetching operations
- `max_poll_records=1` - process one message at a time
- `session_timeout_ms=30000` (30 seconds)
- `heartbeat_interval_ms=3000` (3 seconds)
- `auto_offset_reset="earliest"` - don't miss messages on restart

---

### 1.3 Message Handling Loop

**Decision**: Use blocking poll with timeout, checking `_stop_event` after each message

**Rationale**:
- Pattern from NotificationWorker (proven in production)
- Allows responsive shutdown without message loss
- `timeout_ms=1000` balances CPU usage and shutdown responsiveness

**Implementation Notes**:

```python
# From NotificationWorker._run()
def _run(self):
    while not self._stop_event.is_set():
        try:
            messages = self._consumer.consumer.poll(
                timeout_ms=int(self.POLL_TIMEOUT * 1000),
                max_records=1
            )

            if not messages:
                continue

            for topic_partition, records in messages.items():
                for record in records:
                    if self._stop_event.is_set():
                        break

                    try:
                        success = self._process_message(record.value)
                        if success:
                            self._consumer.commit()
                    except Exception as e:
                        GLOG.ERROR(f"Error processing message: {e}")
                        # Don't commit - let Kafka retry

        except Exception as e:
            GLOG.ERROR(f"Error in worker loop: {e}")
            time.sleep(1)
```

**Key Points**:
- Only commit offset after successful processing
- Exception in processing skips commit - Kafka will redeliver
- Graceful handling of consumer errors

---

### 1.4 Redis Heartbeat Implementation

**Decision**: Implement heartbeat with `heartbeat:data_worker:{node_id}` key format

**Rationale**:
- Matches TaskTimer pattern for consistency
- Enables monitoring and alerting via Redis
- TTL-based auto-cleanup of dead workers
- Supports multi-instance deployment

**Implementation Notes**:

```python
# From TaskTimer pattern (/home/kaoru/Ginkgo/src/ginkgo/livecore/task_timer.py)
HEARTBEAT_INTERVAL = 10  # 10 seconds
HEARTBEAT_TTL = 30       # 30 seconds TTL

def _get_heartbeat_key(self) -> str:
    return f"heartbeat:data_worker:{self.node_id}"

def _send_heartbeat(self):
    import socket
    heartbeat_data = {
        "timestamp": datetime.now().isoformat(),
        "component_type": "data_worker",
        "component_id": self.node_id,
        "host": socket.gethostname(),
        "pid": os.getpid(),
        "messages_processed": self._stats["messages_processed"],
        "messages_failed": self._stats["messages_failed"],
    }

    heartbeat_value = json.dumps(heartbeat_data)
    self._redis_client.setex(
        self._get_heartbeat_key(),
        self.HEARTBEAT_TTL,
        heartbeat_value
    )
```

**Thread Safety**:
- Run heartbeat in dedicated daemon thread
- Use `threading.Event` for coordination
- Clean shutdown: stop event → join thread → close Redis connection

---

### 1.5 Dockerfile Structure

**Decision**: Follow TaskTimer Dockerfile pattern with uv for fast dependency installation

**Rationale**:
- Proven pattern in production
- uv is 10-100x faster than pip for dependency installation
- Minimal base image (python:3.12.11-slim-bookworm)
- Clear separation of dependencies, source, and configuration

**Implementation Notes**:

```dockerfile
# From /home/kaoru/Ginkgo/.conf/Dockerfile.tasktimer
FROM python:3.12.11-slim-bookworm

WORKDIR /ginkgo

# Install system dependencies
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package manager)
RUN pip install -i https://mirrors.aliyun.com/pypi/simple/ uv

ENV PATH="/root/.local/bin:${PATH}"

# Copy and install dependencies
COPY requirements.txt ./
RUN uv pip install -r requirements.txt --system -i https://mirrors.aliyun.com/pypi/simple/

# Copy source code
COPY main.py ./
COPY src/ ./

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/ginkgo/src

# Entry point
CMD ["python", "main.py", "dataworker", "start"]
```

**Best Practices**:
- Use Chinese mirrors for faster builds in China
- Clean up apt lists to reduce image size
- Multi-stage build not needed (no compilation artifacts)
- Volume mount logs directory

---

### 1.6 Docker Compose Integration

**Decision**: Add service to existing `/home/kaoru/Ginkgo/.conf/docker-compose.yml`

**Rationale**:
- Single file for all infrastructure services
- Consistent environment variable management
- Shared network with Kafka, ClickHouse, Redis

**Implementation Notes**:

```yaml
# From docker-compose.yml pattern
data-worker:
  build:
    context: ..
    dockerfile: .conf/Dockerfile.dataworker
  image: ginkgo/data-worker:latest
  container_name: data-worker
  restart: always
  depends_on:
    - kafka1
    - redis-master
    - clickhouse-test
  environment:
    # Kafka
    GINKGO_KAFKA_HOST: kafka1
    GINKGO_KAFKA_PORT: 9092
    # Redis (heartbeat)
    GINKGO_REDIS_HOST: redis-master
    GINKGO_REDIS_PORT: 6379
    # ClickHouse (write data)
    GINKGO_CLICKHOUSE_HOST: clickhouse-test
    GINKGO_CLICKHOUSE_PORT: 8123
    GINKGO_CLICKHOUSE_USER: ${CLICKHOUSE_USER:-default}
    GINKGO_CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-""}
    GINKGO_CLICKHOUSE_DATABASE: ginkgo
    # Worker config
    WORKER_GROUP_ID: data_worker_group
    GINKGO_DEBUG_MODE: "False"
    LOG_LEVEL: INFO
    PYTHONUNBUFFERED: 1
  volumes:
    - ../.logs/dataworker:/ginkgo/.logs
  deploy:
    resources:
      limits:
        cpus: '1.00'
        memory: 512M
      reservations:
        cpus: '0.25'
        memory: 256M
```

**Scaling**:
- Set `replicas: 3` for multi-instance deployment
- Consumer group automatically partitions topic across instances
- Each instance gets unique `node_id` via environment variable

---

## 2. Kafka Consumer Group Best Practices

### 2.1 Consumer Group ID Configuration

**Decision**: Use configurable group ID with default `"data_worker_group"`

**Rationale**:
- Enables horizontal scaling - multiple instances share load
- Each message processed by exactly one instance
- Offset tracking in Kafka `__consumer_offsets` topic
- Matches NotificationWorker pattern

**Implementation Notes**:

```python
class DataWorker:
    WORKER_GROUP_ID = "data_worker_group"

    def __init__(self, group_id: Optional[str] = None, ...):
        self._group_id = group_id or os.getenv("WORKER_GROUP_ID", self.WORKER_GROUP_ID)
```

**Multi-Instance Deployment**:
```yaml
# docker-compose.yml
data-worker:
  environment:
    WORKER_GROUP_ID: data_worker_group
  deploy:
    replicas: 3  # 3 instances sharing load
```

---

### 2.2 Topic Partitioning Strategy

**Decision**: Use `ginkgo.data.update` topic with 24 partitions

**Rationale**:
- Matches existing topic setup (from `kafka_topic_set()`)
- 24 partitions = 1 partition per hour of day (convenient for time-based routing)
- Supports up to 24 concurrent consumers without idle instances
- Balanced load distribution via Kafka's partitioner

**Implementation Notes**:

```python
# From kafka_topic_set() in ginkgo_kafka.py
topic_config = {
    "ginkgo.data.update": (24, 1),  # (partitions, replication_factor)
}
```

**Message Key Strategy** (for routing):
```python
# Route by stock code - same code always goes to same partition
message = {
    "code": "000001.SZ",
    "timestamp": "2024-01-01",
    # ... other fields
}
producer.send(
    topic="ginkgo.data.update",
    key=message["code"].encode(),  # Partition by code
    value=json.dumps(message)
)
```

---

### 2.3 Offset Commit Strategy

**Decision**: Manual commit after successful message processing

**Rationale**:
- At-least-once delivery guarantee
- No message loss on worker crash
- Automatic retry on processing failure
- Matches NotificationWorker pattern

**Implementation Notes**:

```python
def _run(self):
    while not self._stop_event.is_set():
        messages = self._consumer.consumer.poll(timeout_ms=1000, max_records=1)

        for record in messages:
            try:
                success = self._process_message(record.value)
                if success:
                    # Only commit on success
                    self._consumer.commit()
                else:
                    # Processing failed - don't commit, Kafka will redeliver
                    self._stats["messages_failed"] += 1
            except Exception as e:
                GLOG.ERROR(f"Error processing message: {e}")
                # Don't commit - trigger retry
```

**Idempotency Considerations**:
- Data updates should be idempotent (safe to retry)
- Use `INSERT OR REPLACE` or upsert patterns
- Check for existing records before insert

---

### 2.4 Consumer Rebalance Handling

**Decision**: Rely on kafka-python's automatic rebalance handling

**Rationale**:
- Default rebalance listener handles partition assignment/revocation
- No custom logic needed for simple use cases
- Proven in NotificationWorker production use

**Configuration**:
```python
# GinkgoConsumer defaults (already configured)
self.consumer = KafkaConsumer(
    topic,
    group_id=group_id,
    # Rebalance settings
    max_poll_interval_ms=1800000,  # Allow long processing (30 min)
    session_timeout_ms=30000,      # Detect dead consumers quickly
    heartbeat_interval_ms=3000,     # Regular heartbeat
)
```

**Best Practices**:
- Keep message processing time under `max_poll_interval_ms`
- Use background threads for long operations (like data fetching)
- Commit offsets frequently (after each message)

---

## 3. Data Source Integration

### 3.1 Data Source Architecture

**Decision**: Use existing data sources from `/home/kaoru/Ginkgo/src/ginkgo/data/sources/`

**Rationale**:
- Consistent with existing data update commands
- Reuse proven error handling and retry logic
- Support multiple providers (Tushare, Yahoo, AKShare, BaoStock, TDX)

**Available Sources**:
- `ginkgo_tushare` - Tushare Pro API (primary for A-shares)
- `ginkgo_yahoo` - Yahoo Finance (US/HK stocks)
- `ginkgo_akshare` - AKShare (Chinese markets)
- `ginkgo_baostock` - BaoStock (free A-share data)
- `ginkgo_tdx` - TongDaXin (real-time data)

---

### 3.2 Getting Bar Data from Sources

**Decision**: Call existing fetch methods with retry wrapper

**Rationale**:
- Methods already handle pagination and rate limiting
- Proven in production via CLI commands
- Consistent error handling via `@retry` decorator

**Implementation Notes**:

```python
# From ginkgo_tushare.py pattern
from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
from ginkgo.libs.utils.common import retry

class DataWorker:
    def __init__(self, ...):
        self._tushare_source = GinkgoTushare()

    @retry(max_try=3)
    def fetch_bar_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch bar data from Tushare with automatic retry

        Args:
            code: Stock code (e.g., "000001.SZ")
            start_date: Start date (YYYYMMDD format)
            end_date: End date (YYYYMMDD format)

        Returns:
            DataFrame with bar data
        """
        df = self._tushare_source.fetch_cn_stock_daybar(
            code=code,
            start_date=start_date,
            end_date=end_date
        )

        if df.empty:
            GLOG.WARN(f"No data returned for {code} from {start_date} to {end_date}")

        return df
```

**Key Points**:
- Methods handle large date spans with automatic pagination
- `@retry` wrapper handles transient network failures
- Returns empty DataFrame on failure (caller handles it)

---

### 3.3 API Rate Limiting Patterns

**Decision**: Rely on existing rate limiting in data sources

**Rationale**:
- Tushare source implements adaptive window sizing
- Built-in delays between segments
- Proven rate limit handling in production

**Implementation Notes**:

```python
# From ginkgo_tushare.py - fetch_cn_stock_daybar()
def fetch_cn_stock_daybar(self, code: str, start_date: any, end_date: any) -> pd.DataFrame:
    # Calculate optimal window size to avoid rate limits
    max_days_per_request = self._calculate_daybar_window_size(date_span)

    # Segment fetching for large date spans
    while current_start < end_dt:
        # Fetch segment
        r = self.pro.daily(ts_code=code, start_date=start_str, end_date=end_str)

        # Small delay between segments
        if segment_count > 1:
            time.sleep(0.1)
```

**Rate Limit Configuration**:
- Tushare Pro: 200 requests/minute (adjust based on account level)
- Implement exponential backoff on 429 errors
- Consider request queuing for high-volume updates

---

### 3.4 Error Handling and Retry Logic

**Decision**: Use `@retry` decorator with exponential backoff

**Rationale**:
- Consistent with existing codebase
- Configurable retry count and backoff factor
- Automatic logging of retries

**Implementation Notes**:

```python
# From common.py
def retry(func=None, *, max_try: int = 3, backoff_factor: float = 2.0):
    """
    Retry decorator with exponential backoff

    Args:
        max_try: Maximum retry attempts
        backoff_factor: Backoff multiplier (default: 2x)
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        for attempt in range(max_try):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_try - 1:
                    raise

                wait_time = backoff_factor ** attempt
                GLOG.WARN(f"Retry {attempt + 1}/{max_try} after {wait_time}s: {e}")
                time.sleep(wait_time)

    return wrapper

# Usage
@retry(max_try=3, backoff_factor=2)
def fetch_with_retry(self, code, start, end):
    return self._source.fetch_cn_stock_daybar(code, start, end)
```

**Error Categories**:
- **Transient**: Network errors, rate limits → Retry
- **Permanent**: Invalid codes, authentication errors → Fail fast
- **Data Errors**: Empty datasets → Log warning, continue

---

## 4. ClickHouse Batch Write Optimization

### 4.1 Batch Operations via BarCRUD

**Decision**: Use `add_batch()` from `BarCRUD` for bulk inserts

**Rationale**:
- Follows existing CRUD pattern
- Automatic connection management via BaseCRUD
- Type-safe conversion to `MBar` models
- Support for both ClickHouse and MySQL

**Implementation Notes**:

```python
# From bar_crud.py pattern
from ginkgo.data.crud.bar_crud import BarCRUD
from ginkgo.trading import Bar

class DataWorker:
    def __init__(self, ...):
        self._bar_crud = BarCRUD()

    def write_bars_to_database(self, bars: List[Bar]) -> int:
        """
        Write bars to ClickHouse in batch

        Args:
            bars: List of Bar business objects

        Returns:
            Number of bars written
        """
        try:
            # add_batch handles conversion to MBar and insertion
            result = self._bar_crud.add_batch(bars)
            count = len(result)

            GLOG.INFO(f"Successfully wrote {count} bars to ClickHouse")
            return count

        except Exception as e:
            GLOG.ERROR(f"Failed to write bars: {e}")
            return 0
```

**Key Features**:
- Automatic conversion from `Bar` to `MBar` models
- Enum field validation and conversion
- Null byte cleaning for ClickHouse FixedString fields
- Transaction handling for data integrity

---

### 4.2 Batch Size Recommendations

**Decision**: Target 1000-2000 records per batch

**Rationale**:
- ClickHouse optimal batch size: 1000+ rows
- Balances memory usage vs. insert performance
- Proven in FactorEngine (`batch_size=1000`)

**Implementation Notes**:

```python
# From factor_engine.py pattern
def _store_bars_in_batches(self, bars: List[Bar], batch_size: int = 1000) -> int:
    """
    Store bars in batches to avoid memory issues

    Args:
        bars: List of bars to store
        batch_size: Records per batch (default: 1000)

    Returns:
        Total number of bars stored
    """
    total_stored = 0

    for i in range(0, len(bars), batch_size):
        batch = bars[i:i + batch_size]

        try:
            result = self._bar_crud.add_batch(batch)
            stored_count = len(result)
            total_stored += stored_count

            GLOG.DEBUG(f"Stored batch {i//batch_size + 1}: {stored_count} records")

        except Exception as e:
            GLOG.ERROR(f"Failed to store batch {i//batch_size + 1}: {e}")

    return total_stored
```

**Batch Size Trade-offs**:
- **Too small** (< 100): High overhead, poor performance
- **Optimal** (1000-2000): Best throughput, manageable memory
- **Too large** (> 10000): Risk of OOM, long transaction times

---

### 4.3 Transaction Handling for Data Integrity

**Decision**: Use context managers for automatic commit/rollback

**Rationale**:
- Proven pattern in `/home/kaoru/Ginkgo/src/ginkgo/data/drivers/__init__.py`
- Automatic cleanup on exceptions
- Support for both ClickHouse and MySQL

**Implementation Notes**:

```python
# From drivers/__init__.py - add_all()
def add_all(values: List[Any]) -> None:
    click_list = [v for v in values if isinstance(v, MClickBase)]

    try:
        click_conn = get_click_connection()

        # Context manager ensures commit/rollback
        with click_conn.get_session() as session:
            # Group by model type for optimal performance
            model_groups = {}
            for item in click_list:
                model_type = type(item)
                if model_type not in model_groups:
                    model_groups[model_type] = []
                model_groups[model_type].append(item)

            # Bulk insert for each model type
            for model_type, items in model_groups.items():
                mappings = [item.__dict__ for item in items]
                session.bulk_insert_mappings(model_type, mappings)

    except Exception as e:
        GLOG.ERROR(f"ClickHouse batch operation failed: {e}")
        # Context manager automatically rolls back
```

**Transaction Guarantees**:
- All-or-nothing insertion for each batch
- Automatic rollback on error
- Connection cleanup via context manager

---

### 4.4 Performance Optimization Techniques

**Decision**: Use ClickHouse-specific optimizations

**Rationale**:
- ClickHouse has different performance characteristics than MySQL
- Bulk insert via `bulk_insert_mappings()` is 10-100x faster
- Avoid row-by-row inserts

**Implementation Notes**:

```python
# Optimization 1: Use bulk_insert_mappings for ClickHouse
session.bulk_insert_mappings(MBar, mappings)  # Fast

# Optimization 2: Group by model type
model_groups = {}
for item in items:
    model_groups[type(item)].append(item)

# Optimization 3: Batch size tuning
BATCH_SIZE = 1000  # Optimal for ClickHouse

# Optimization 4: Async inserts (optional)
# ClickHouse supports async insert for higher throughput
```

**Performance Benchmarks** (approximate):
- Row-by-row: 100 rows/sec
- Batch 100: 1000 rows/sec
- Batch 1000: 5000 rows/sec
- Batch 10000: 8000 rows/sec (diminishing returns)

---

## 5. Container Health Check Strategy

### 5.1 Docker Healthcheck for Kafka Consumers

**Decision**: Implement healthcheck script that validates Kafka connectivity and message processing

**Rationale**:
- Matches existing healthcheck patterns
- Enables orchestrator to detect unhealthy consumers
- Supports auto-restart on failures

**Implementation Notes**:

```dockerfile
# Dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD python -c "from ginkgo.livecore.data_worker import DataWorker; worker = DataWorker(); exit(0 if worker.is_healthy else 1)" || \
    CMD curl -f http://localhost:8080/health || exit 1
```

**Healthcheck Criteria**:
1. Kafka consumer connected
2. Recent heartbeat in Redis
3. No errors in last 5 minutes
4. Thread is running (not stuck)

---

### 5.2 Detecting "Stuck" Consumer

**Decision**: Monitor heartbeat age and message processing timestamp

**Rationale**:
- Heartbeat timestamp indicates worker is alive
- Last message timestamp indicates processing is active
- Dual check catches both stuck threads and idle consumers

**Implementation Notes**:

```python
def is_healthy(self) -> bool:
    """
    Check if worker is healthy (for healthcheck endpoint)

    Returns:
        True if healthy, False otherwise
    """
    # Check 1: Thread is running
    if not self.is_running:
        return False

    # Check 2: Recent heartbeat
    heartbeat_age = time.time() - self._last_heartbeat_time
    if heartbeat_age > self.HEARTBEAT_TTL * 2:  # 2x TTL = 60 seconds
        GLOG.WARN(f"Healthcheck failed: heartbeat too old ({heartbeat_age:.1f}s)")
        return False

    # Check 3: Not stuck (processing messages)
    if self._stats["last_message_time"]:
        message_age = (datetime.now() - self._stats["last_message_time"]).total_seconds()
        # Allow up to 10 minutes without messages (might be idle)
        if message_age > 600:
            GLOG.WARN(f"Healthcheck warning: no messages for {message_age:.1f}s")
            # Don't fail - consumer might be idle

    return True
```

**Stuck Detection Triggers**:
- Heartbeat age > 60 seconds (2x TTL)
- Thread status != RUNNING
- Consumer disconnected
- Continuous processing errors

---

### 5.3 Liveness vs Readiness Probes

**Decision**: Separate liveness and readiness checks

**Rationale**:
- **Liveness**: Is the container alive? (restart if not)
- **Readiness**: Can the container accept traffic? (don't route if not)
- Kubernetes best practices

**Implementation Notes**:

```yaml
# docker-compose.yml (for Kubernetes deployment)
deploy:
  replicas: 3
  restart_policy:
    condition: on-failure
    delay: 5s
    max_attempts: 3
  # Liveness probe - restart if fails
  liveness_probe:
    exec:
      command: ["sh", "-c", "python -c 'from ginkgo.livecore.data_worker import DataWorker; worker = DataWorker(); exit(0 if worker.is_alive() else 1)'"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
  # Readiness probe - don't route if fails
  readiness_probe:
    exec:
      command: ["sh", "-c", "python -c 'from ginkgo.livecore.data_worker import DataWorker; worker = DataWorker(); exit(0 if worker.is_ready() else 1)'"]
    interval: 10s
    timeout: 5s
    retries: 2
    start_period: 30s
```

**Liveness Check**:
```python
def is_alive(self) -> bool:
    """Check if worker process is alive (for liveness probe)"""
    return self.is_alive()  # threading.Thread.is_alive()
```

**Readiness Check**:
```python
def is_ready(self) -> bool:
    """Check if worker is ready to process messages (for readiness probe)"""
    return (
        self.is_alive() and  # Thread is running
        self._consumer and self._consumer.is_connected and  # Kafka connected
        self._last_heartbeat_time > 0  # Heartbeat active
    )
```

---

## 6. Summary of Technical Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| **Worker Pattern** | `threading.Thread` with `threading.Event` | Consistent with existing workers, proven in production |
| **Kafka Consumer** | Use existing `GinkgoConsumer` wrapper | Handles connection, deserialization, errors |
| **Heartbeat** | Redis with TTL-based key expiration | Matches TaskTimer pattern, enables monitoring |
| **Dockerfile** | Follow TaskTimer pattern with uv | Fast builds, minimal image, proven pattern |
| **Consumer Group** | Configurable group ID, default `"data_worker_group"` | Enables horizontal scaling, automatic load distribution |
| **Offset Commit** | Manual commit after successful processing | At-least-once delivery, automatic retry on failure |
| **Data Sources** | Use existing sources (Tushare, Yahoo, etc.) | Reuse proven code, consistent with CLI commands |
| **Batch Size** | Target 1000-2000 records per batch | Optimal for ClickHouse, balances memory and performance |
| **Transactions** | Context managers for automatic commit/rollback | Data integrity guarantees, automatic cleanup |
| **Health Check** | Separate liveness/readiness probes | Kubernetes best practices, proper failure detection |

---

## 7. References

### Code Files Analyzed

1. **Worker Patterns**:
   - `/home/kaoru/Ginkgo/src/ginkgo/livecore/task_timer.py` - TaskTimer implementation
   - `/home/kaoru/Ginkgo/src/ginkgo/notifier/workers/notification_worker.py` - NotificationWorker implementation

2. **Kafka Integration**:
   - `/home/kaoru/Ginkgo/src/ginkgo/data/drivers/ginkgo_kafka.py` - GinkgoProducer/Consumer
   - `/home/kaoru/Ginkgo/src/ginkgo/interfaces/kafka_topics.py` - Kafka topic definitions

3. **Data Operations**:
   - `/home/kaoru/Ginkgo/src/ginkgo/data/crud/bar_crud.py` - BarCRUD implementation
   - `/home/kaoru/Ginkgo/src/ginkgo/data/crud/base_crud.py` - BaseCRUD with batch operations
   - `/home/kaoru/Ginkgo/src/ginkgo/data/sources/ginkgo_tushare.py` - Tushare data source

4. **Deployment**:
   - `/home/kaoru/Ginkgo/.conf/Dockerfile.tasktimer` - Container pattern
   - `/home/kaoru/Ginkgo/.conf/docker-compose.yml` - Service configuration

5. **Utilities**:
   - `/home/kaoru/Ginkgo/src/ginkgo/libs/utils/common.py` - Decorators (@retry, @time_logger)
   - `/home/kaoru/Ginkgo/src/ginkgo/libs/utils/health_check.py` - Health check utilities

### Related Documentation

- `CLAUDE.md` - Project architecture and development patterns
- `specs/008-live-data-module/README.md` - Live data module architecture

---

## 8. Next Steps

1. **Create Data Worker Specification** - Document API and behavior
2. **Implement Data Worker Class** - Following patterns in this research
3. **Create Dockerfile** - Based on TaskTimer pattern
4. **Update docker-compose.yml** - Add data-worker service
5. **Write Unit Tests** - Test message handling, error cases
6. **Integration Testing** - Test with real Kafka, ClickHouse, Redis
7. **Performance Testing** - Validate batch sizes and throughput
8. **Monitoring Setup** - Dashboard for worker health and metrics
