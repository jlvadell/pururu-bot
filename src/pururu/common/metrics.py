"""
Prometheus metrics registry for the Pururu application.

This module defines all Prometheus metrics used across the application.
Metrics are organized by domain/component for clarity.

Python runtime metrics (GC, memory, CPU, etc.) are automatically exposed
via prometheus_client's built-in collectors.
"""
from prometheus_client import (Counter, Histogram, Info, REGISTRY, ProcessCollector, PlatformCollector, GCCollector)

# Enable Python runtime metrics collection
# These collectors expose:
# - process_* metrics (CPU, memory, file descriptors, etc.)
# - python_* metrics (Python version, implementation)
# - python_gc_* metrics (Garbage collector statistics)
ProcessCollector(registry=REGISTRY)
PlatformCollector(registry=REGISTRY)
GCCollector(registry=REGISTRY)

# ============================================================================
# SQS / Event Processing Metrics
# ============================================================================

sqs_events_processed_total = Counter(
    'sqs_events_processed_total',
    'Total number of SQS events processed successfully',
    ['event_type', 'queue_name']
)

sqs_event_processing_duration_seconds = Histogram(
    'sqs_event_processing_duration_seconds',
    'Time taken to process an SQS event (from poll to delete)',
    ['event_type', 'queue_name'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 30.0, 45.0, 60.0)
)

sqs_event_age_seconds = Histogram(
    'sqs_event_age_seconds',
    'Age of SQS events when processed (time since event creation)',
    ['event_type', 'queue_name'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 15.0, 30.0)
)

# ============================================================================
# Discord Bot Metrics
# ============================================================================

discord_operation_duration_seconds = Histogram(
    'discord_operation_duration_seconds',
    'Discord operation execution time',
    ['operation'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0)
)

# ============================================================================
# Database Metrics
# ============================================================================

database_operation_duration_seconds = Histogram(
    'database_operation_duration_seconds',
    'Database operation execution time',
    ['operation', 'table'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0)
)

# ============================================================================
# Application Info
# ============================================================================

app_info = Info(
    'pururu_app',
    'Application information'
)
