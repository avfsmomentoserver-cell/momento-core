# Troubleshooting Guide

## Common Issues

### High API Latency

**Symptoms:** Response times > 500ms

**Diagnosis:**
1. Check database query performance
2. Review cache hit rates
3. Monitor CPU/memory usage
4. Check network latency

**Solutions:**
- Add missing database indexes
- Increase cache TTL
- Scale horizontally
- Optimize slow queries

### WebSocket Disconnections

**Symptoms:** Frequent client disconnections

**Diagnosis:**
1. Check server logs for errors
2. Monitor connection count
3. Review heartbeat timing
4. Check load balancer settings

**Solutions:**
- Increase timeout values
- Implement reconnection logic
- Scale WebSocket servers
- Configure sticky sessions

### Data Gaps

**Symptoms:** Missing candles or ticks

**Diagnosis:**
1. Check exchange connectivity
2. Review ingestion logs
3. Verify message queue health
4. Check for processing errors

**Solutions:**
- Restart exchange connections
- Replay missed messages
- Fix parsing bugs
- Add redundancy

### Memory Leaks

**Symptoms:** Increasing memory usage over time

**Diagnosis:**
1. Profile memory usage
2. Check for unclosed connections
3. Review event listener cleanup
4. Analyze heap snapshots

**Solutions:**
- Fix connection leaks
- Implement proper cleanup
- Add memory limits
- Schedule restarts

## Getting Help
1. Search existing issues
2. Check documentation
3. Review logs and metrics
4. Contact on-call engineer
5. Create detailed bug report
