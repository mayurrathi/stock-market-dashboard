#!/usr/bin/env python3
"""
Health Check Endpoint for Stock Market Dashboard
Add this to main.py as a new endpoint
"""

health_check_code = '''
@app.get("/api/health")
async def health_check(db: Session = Depends(get_db)):
    """System health check endpoint - monitors background tasks and Telegram connection"""
    from datetime import datetime, timedelta
    
    try:
        # Check last successful task runs (within last hour)
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_successes = db.query(TaskLog).filter(
            TaskLog.created_at >= one_hour_ago,
            TaskLog.status == "success"
        ).all()
        
        # Check for active flood waits
        active_flood_waits = db.query(TaskLog).filter(
            TaskLog.status == "flood_wait",
            TaskLog.retry_after > datetime.now()
        ).all()
        
        # Check telegram authorization
        telegram_authorized = await monitor.is_authorized()
        
        # Calculate health status
        health_status = "healthy"
        if len(active_flood_waits) > 0:
            health_status = "rate_limited"
        elif len(recent_successes) < 2:  # Expect at least 2 successful tasks per hour
            health_status = "degraded"
        
        # Get task stats
        task_stats = {}
        for task_log in recent_successes[-10:]:  # Last 10 successes
            if task_log.task_name not in task_stats:
                task_stats[task_log.task_name] = {
                    "last_success": task_log.created_at.isoformat(),
                    "count": 0
                }
            task_stats[task_log.task_name]["count"] += 1
        
        return {
            "status": health_status,
            "telegram": {
                "authorized": telegram_authorized,
                "last_flood_wait": monitor._last_flood_wait.isoformat() if monitor._last_flood_wait else None,
                "active_flood_waits": len(active_flood_waits)
            },
            "tasks": {
                "recent_successes": len(recent_successes),
                "stats": task_stats
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
'''

print(health_check_code)
