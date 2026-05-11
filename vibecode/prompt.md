Execute this action to add monitoring to the codebase. Base on this general infra:

```txt
FastAPI/Flask App
    │
    ├── structlog ──────────► stdout (JSON logs)
    │                              │
    │                         Promtail (đọc log)
    │                              │
    │                           Loki (lưu log)
    │                              │
    │                         Grafana (xem log)
    │
    └── prometheus_client ──► /metrics endpoint
                                   │
                              Prometheus (scrape mỗi 15s)
                                   │
                              Grafana (xem metrics + alert)
```

Top metrics to monitor:
1. Request latency
2. Error rates
3. Throughput (requests per second)
4. Resource utilization (CPU, memory)
5. Token per request
6. Token per user
7. Price per request
8. Price per user 
That metrics is must have for LLM application. You can add more if you think it's useful.
Moreover, you can create some diagrams to illustrate how the monitoring system works, and how the data flows from the application to the monitoring tools. You can also provide some examples of how to query the logs and metrics in Grafana to get insights about the application's performance and behavior.

