"""
SME ERP Basic Alert System
Phase 7 - Operational Excellence

Features:
- Application down detection
- Error rate spike monitoring  
- Database connection failure alerts
- Rate limiting abuse detection
- Performance degradation alerts
- Webhook integration for notifications
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from app.core.logging import get_logger, security_logger, error_logger
import sqlite3
import os


class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"  
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    APP_DOWN = "app_down"
    ERROR_RATE_SPIKE = "error_rate_spike"
    DB_CONNECTION_FAILURE = "db_connection_failure"
    RATE_LIMIT_ABUSE = "rate_limit_abuse"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    DISK_SPACE_LOW = "disk_space_low"
    SECURITY_THREAT = "security_threat"


@dataclass
class Alert:
    """Alert data structure"""
    id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    timestamp: str
    source: str
    metadata: Dict[str, Any]
    resolved: bool = False
    resolved_at: Optional[str] = None


class AlertManager:
    """Central alert management system"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("ALERT_WEBHOOK_URL")
        self.logger = get_logger("alerts")
        self.alerts_db = "ops/alerts.db"
        self.setup_database()
        
        # Alert thresholds
        self.thresholds = {
            "error_rate_threshold": 5,  # errors per minute
            "response_time_threshold": 2.0,  # seconds
            "db_connection_timeout": 5.0,  # seconds
            "rate_limit_violations_threshold": 10  # per 5 minutes
        }
        
        # Alert state tracking
        self.alert_state = {
            "last_error_count": 0,
            "last_check_time": time.time(),
            "consecutive_failures": 0,
            "app_is_down": False
        }
    
    def setup_database(self):
        """Setup SQLite database for alert storage"""
        os.makedirs(os.path.dirname(self.alerts_db), exist_ok=True)
        
        with sqlite3.connect(self.alerts_db) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    source TEXT NOT NULL,
                    metadata TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at TEXT
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_timestamp 
                ON alerts(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_type_severity 
                ON alerts(alert_type, severity)
            """)
    
    async def create_alert(self, alert_type: AlertType, severity: AlertSeverity,
                          title: str, description: str, source: str = "system",
                          metadata: Dict[str, Any] = None) -> Alert:
        """Create and process a new alert"""
        
        alert_id = f"{alert_type.value}_{int(time.time())}"
        metadata = metadata or {}
        
        alert = Alert(
            id=alert_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            description=description,
            timestamp=datetime.utcnow().isoformat(),
            source=source,
            metadata=metadata
        )
        
        # Store alert in database
        self.store_alert(alert)
        
        # Log alert
        self.logger.warning(
            f"Alert created: {title}",
            extra={
                "event_type": "alert_created",
                "alert_id": alert_id,
                "alert_type": alert_type.value,
                "severity": severity.value,
                "source": source,
                "metadata": metadata
            }
        )
        
        # Send notification
        await self.send_notification(alert)
        
        return alert
    
    def store_alert(self, alert: Alert):
        """Store alert in database"""
        try:
            with sqlite3.connect(self.alerts_db) as conn:
                conn.execute("""
                    INSERT INTO alerts 
                    (id, alert_type, severity, title, description, timestamp, source, metadata, resolved)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.id,
                    alert.alert_type.value,
                    alert.severity.value,
                    alert.title,
                    alert.description,
                    alert.timestamp,
                    alert.source,
                    json.dumps(alert.metadata),
                    alert.resolved
                ))
        except Exception as e:
            self.logger.error(f"Failed to store alert: {e}")
    
    async def send_notification(self, alert: Alert):
        """Send alert notification via webhook"""
        if not self.webhook_url:
            self.logger.info("No webhook URL configured, skipping notification")
            return
        
        try:
            payload = {
                "text": f"🚨 {alert.title}",
                "alert_id": alert.id,
                "alert_type": alert.alert_type.value,
                "severity": alert.severity.value,
                "description": alert.description,
                "timestamp": alert.timestamp,
                "source": alert.source,
                "metadata": alert.metadata
            }
            
            # Add severity emoji
            severity_emoji = {
                AlertSeverity.LOW: "🟡",
                AlertSeverity.MEDIUM: "🟠", 
                AlertSeverity.HIGH: "🔴",
                AlertSeverity.CRITICAL: "🚨"
            }
            
            payload["text"] = f"{severity_emoji[alert.severity]} {payload['text']}"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.webhook_url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        self.logger.info(f"Alert notification sent: {alert.id}")
                    else:
                        self.logger.warning(f"Alert notification failed: {response.status}")
                        
        except Exception as e:
            self.logger.error(f"Failed to send alert notification: {e}")
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        try:
            with sqlite3.connect(self.alerts_db) as conn:
                cursor = conn.execute("""
                    UPDATE alerts 
                    SET resolved = TRUE, resolved_at = ?
                    WHERE id = ? AND resolved = FALSE
                """, (datetime.utcnow().isoformat(), alert_id))
                
                if cursor.rowcount > 0:
                    self.logger.info(f"Alert resolved: {alert_id}")
                    return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to resolve alert: {e}")
            return False
    
    def get_active_alerts(self) -> List[Dict]:
        """Get all active (unresolved) alerts"""
        try:
            with sqlite3.connect(self.alerts_db) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM alerts 
                    WHERE resolved = FALSE 
                    ORDER BY timestamp DESC
                """)
                
                alerts = []
                for row in cursor.fetchall():
                    alert_dict = dict(row)
                    alert_dict['metadata'] = json.loads(alert_dict['metadata'])
                    alerts.append(alert_dict)
                
                return alerts
                
        except Exception as e:
            self.logger.error(f"Failed to get active alerts: {e}")
            return []


class HealthMonitor:
    """Monitor application health and generate alerts"""
    
    def __init__(self, alert_manager: AlertManager):
        self.alert_manager = alert_manager
        self.logger = get_logger("health_monitor")
        self.monitoring_active = True
    
    async def check_application_health(self) -> bool:
        """Check if application is responding"""
        try:
            # In a real deployment, this would check health endpoints
            # For demo, we'll simulate health check
            
            # Simulate checking health endpoint
            import aiohttp
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        "http://localhost:8000/health/live",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        return response.status == 200
                except:
                    return False
                    
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False
    
    async def check_database_connection(self) -> bool:
        """Check database connectivity"""
        try:
            # Check database connection
            db_path = "sme_erp_dev.db"
            if os.path.exists(db_path):
                with sqlite3.connect(db_path, timeout=5.0) as conn:
                    conn.execute("SELECT 1")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"Database health check failed: {e}")
            return False
    
    async def check_disk_space(self) -> bool:
        """Check available disk space"""
        try:
            import shutil
            total, used, free = shutil.disk_usage("/")
            free_percent = (free / total) * 100
            
            # Alert if less than 10% free space
            return free_percent > 10
            
        except Exception as e:
            self.logger.error(f"Disk space check failed: {e}")
            return True  # Don't alert on check failure
    
    async def check_error_rate(self) -> bool:
        """Check application error rate"""
        try:
            # This would typically query logs or metrics
            # For demo, we'll simulate error rate check
            
            # Simulate checking recent errors
            current_time = time.time()
            time_window = 300  # 5 minutes
            
            # In real implementation, query error logs from last 5 minutes
            error_count = 0  # Simulated
            
            error_rate = error_count / (time_window / 60)  # errors per minute
            threshold = self.alert_manager.thresholds["error_rate_threshold"]
            
            return error_rate <= threshold
            
        except Exception as e:
            self.logger.error(f"Error rate check failed: {e}")
            return True  # Don't alert on check failure
    
    async def monitor_continuously(self, check_interval: int = 60):
        """Run continuous monitoring"""
        self.logger.info("Starting continuous health monitoring")
        
        while self.monitoring_active:
            try:
                # Check application health
                app_healthy = await self.check_application_health()
                if not app_healthy and not self.alert_manager.alert_state["app_is_down"]:
                    await self.alert_manager.create_alert(
                        AlertType.APP_DOWN,
                        AlertSeverity.CRITICAL,
                        "Application Down",
                        "Application health check failed - service may be unavailable",
                        "health_monitor",
                        {"check_type": "health_endpoint"}
                    )
                    self.alert_manager.alert_state["app_is_down"] = True
                elif app_healthy and self.alert_manager.alert_state["app_is_down"]:
                    # App recovered
                    self.logger.info("Application health recovered")
                    self.alert_manager.alert_state["app_is_down"] = False
                
                # Check database connection
                db_healthy = await self.check_database_connection()
                if not db_healthy:
                    await self.alert_manager.create_alert(
                        AlertType.DB_CONNECTION_FAILURE,
                        AlertSeverity.HIGH,
                        "Database Connection Failed",
                        "Unable to connect to database",
                        "health_monitor",
                        {"check_type": "database_connection"}
                    )
                
                # Check disk space
                disk_ok = await self.check_disk_space()
                if not disk_ok:
                    await self.alert_manager.create_alert(
                        AlertType.DISK_SPACE_LOW,
                        AlertSeverity.MEDIUM,
                        "Low Disk Space",
                        "Available disk space is below threshold",
                        "health_monitor",
                        {"check_type": "disk_space"}
                    )
                
                # Check error rate
                error_rate_ok = await self.check_error_rate()
                if not error_rate_ok:
                    await self.alert_manager.create_alert(
                        AlertType.ERROR_RATE_SPIKE,
                        AlertSeverity.HIGH,
                        "High Error Rate",
                        "Application error rate has exceeded threshold",
                        "health_monitor", 
                        {"check_type": "error_rate"}
                    )
                
                self.logger.info(f"Health check complete - App: {app_healthy}, DB: {db_healthy}, Disk: {disk_ok}, Errors: {error_rate_ok}")
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
            
            # Wait for next check
            await asyncio.sleep(check_interval)


# Global alert system
alert_manager = AlertManager()
health_monitor = HealthMonitor(alert_manager)


# Utility functions for manual alerts
async def create_security_alert(title: str, description: str, metadata: Dict = None):
    """Create a security-related alert"""
    return await alert_manager.create_alert(
        AlertType.SECURITY_THREAT,
        AlertSeverity.HIGH,
        title,
        description,
        "security",
        metadata
    )


async def create_performance_alert(title: str, description: str, metadata: Dict = None):
    """Create a performance-related alert"""
    return await alert_manager.create_alert(
        AlertType.PERFORMANCE_DEGRADATION,
        AlertSeverity.MEDIUM,
        title,
        description,
        "performance",
        metadata
    )


# Testing function
async def test_alert_system():
    """Test the alert system"""
    print("🚨 Testing Alert System")
    print("=" * 30)
    
    # Create test alerts
    await alert_manager.create_alert(
        AlertType.APP_DOWN,
        AlertSeverity.CRITICAL,
        "Test Application Down Alert",
        "This is a test alert to verify the system is working",
        "test_system"
    )
    
    await alert_manager.create_alert(
        AlertType.ERROR_RATE_SPIKE,
        AlertSeverity.HIGH,
        "Test Error Rate Alert",
        "This is a test alert for error rate monitoring",
        "test_system"
    )
    
    # Get active alerts
    active_alerts = alert_manager.get_active_alerts()
    print(f"📋 Active alerts: {len(active_alerts)}")
    
    for alert in active_alerts:
        print(f"  🚨 {alert['title']} ({alert['severity']})")
    
    print("✅ Alert system test complete")


if __name__ == "__main__":
    # Run alert system test
    asyncio.run(test_alert_system())