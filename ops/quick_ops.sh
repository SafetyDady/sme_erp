#!/bin/bash
# SME ERP Operations Quick Reference
# Phase 7 - Operational Excellence

echo "🔧 SME ERP Operations Quick Reference"
echo "====================================="

show_help() {
    echo "
🚀 DEPLOYMENT
  ./ops/deploy.sh deploy     - Blue-green deployment
  ./ops/deploy.sh rollback   - Emergency rollback  
  ./ops/deploy.sh status     - Check deployment status
  ./ops/deploy.sh cleanup    - Clean up all deployments

💾 BACKUP & RESTORE
  python3 ops/backup.py                    - Create backup
  python3 ops/restore.py                   - Disaster recovery drill
  python3 ops/restore.py --list            - List available backups

🏥 HEALTH CHECKS
  curl localhost:8000/health/live          - Liveness probe
  curl localhost:8000/health/ready         - Readiness probe  
  curl localhost:8000/health/startup       - Startup validation
  curl localhost:8000/health/metrics       - Basic metrics

🚨 ALERTS & MONITORING
  sqlite3 ops/alerts.db 'SELECT * FROM alerts WHERE resolved=0'
  tail -f ops/app_port_*.log
  grep ERROR ops/*.log

⚡ EMERGENCY PROCEDURES
  CRITICAL: ./ops/deploy.sh rollback && python3 ops/restore.py
  APP DOWN: ./ops/deploy.sh cleanup && ./ops/deploy.sh deploy
  DB ISSUE: python3 ops/restore.py
  
📊 QUICK DIAGNOSTICS
  ./ops/deploy.sh status                   - Deployment state
  python3 -c 'import sqlite3; sqlite3.connect(\"sme_erp_dev.db\").execute(\"SELECT 1\")' 
  ps aux | grep python                     - Process check
  df -h                                    - Disk space

🔒 SECURITY
  Rate limits: Check /internal/rate-limits/stats
  Auth logs: grep authentication ops/*.log
  Failed logins: grep 401 ops/*.log
"
}

case "${1:-help}" in
    "help"|"-h"|"--help")
        show_help
        ;;
    "status")
        echo "📊 System Status Check"
        echo "-------------------"
        
        # Deployment status
        if [ -f "ops/active_port.txt" ]; then
            port=$(cat ops/active_port.txt)
            echo "🚀 Active deployment: port $port"
            
            if curl -s -f "http://localhost:$port/health/ready" > /dev/null; then
                echo "✅ Application: Healthy"
            else
                echo "❌ Application: Unhealthy"
            fi
        else
            echo "❌ No active deployment detected"
        fi
        
        # Database check
        if python3 -c "import sqlite3; sqlite3.connect('sme_erp_dev.db').execute('SELECT 1')" 2>/dev/null; then
            echo "✅ Database: Connected"
        else
            echo "❌ Database: Connection failed"
        fi
        
        # Disk space
        available=$(df -h . | tail -1 | awk '{print $4}')
        echo "💾 Disk space available: $available"
        
        # Active alerts
        if [ -f "ops/alerts.db" ]; then
            alert_count=$(sqlite3 ops/alerts.db "SELECT COUNT(*) FROM alerts WHERE resolved=0" 2>/dev/null || echo "0")
            echo "🚨 Active alerts: $alert_count"
        fi
        ;;
        
    "emergency")
        echo "🚨 EMERGENCY RESPONSE ACTIVATED"
        echo "==============================="
        
        echo "1. Checking system status..."
        $0 status
        
        echo -e "\n2. Recent errors..."
        if [ -f "ops/app_port_8000.log" ] || [ -f "ops/app_port_8001.log" ]; then
            tail -10 ops/app_port_*.log | grep -i error || echo "No recent errors found"
        fi
        
        echo -e "\n3. Emergency actions available:"
        echo "   $0 rollback    - Rollback deployment"
        echo "   $0 restore     - Restore from backup"
        echo "   $0 restart     - Restart application"
        ;;
        
    "rollback")
        echo "⏪ Executing emergency rollback..."
        ./ops/deploy.sh rollback
        ;;
        
    "restore")
        echo "💾 Executing disaster recovery..."
        python3 ops/restore.py
        ;;
        
    "restart")
        echo "🔄 Restarting application..."
        ./ops/deploy.sh cleanup
        sleep 2
        ./ops/deploy.sh deploy
        ;;
        
    "backup")
        echo "💾 Creating backup..."
        python3 ops/backup.py
        ;;
        
    "logs")
        echo "📋 Recent logs..."
        if [ -f "ops/deploy.log" ]; then
            tail -20 ops/deploy.log
        fi
        
        if [ -f "ops/app_port_8000.log" ] || [ -f "ops/app_port_8001.log" ]; then
            echo -e "\n--- Application Logs ---"
            tail -10 ops/app_port_*.log
        fi
        ;;
        
    "alerts")
        echo "🚨 Active Alerts"
        echo "==============="
        
        if [ -f "ops/alerts.db" ]; then
            sqlite3 -header -column ops/alerts.db "
                SELECT 
                    substr(id, 1, 20) as id,
                    alert_type,
                    severity, 
                    title,
                    substr(timestamp, 1, 19) as timestamp
                FROM alerts 
                WHERE resolved = 0 
                ORDER BY timestamp DESC
            "
        else
            echo "No alerts database found"
        fi
        ;;
        
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac