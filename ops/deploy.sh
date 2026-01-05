#!/bin/bash
# SME ERP Safe Deployment Strategy - Blue-Green Deployment
# Phase 7 - Operational Excellence

set -euo pipefail

# Configuration
BLUE_PORT=${BLUE_PORT:-8000}
GREEN_PORT=${GREEN_PORT:-8001}
HEALTH_CHECK_TIMEOUT=${HEALTH_CHECK_TIMEOUT:-30}
SMOKE_TEST_TIMEOUT=${SMOKE_TEST_TIMEOUT:-15}
DEPLOYMENT_MODE=${DEPLOYMENT_MODE:-"blue-green"}  # or "rolling"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a ops/deploy.log
}

# Health check function
health_check() {
    local port=$1
    local timeout=$2
    
    for i in $(seq 1 $timeout); do
        if curl -s -f "http://localhost:$port/health/ready" > /dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    
    return 1
}

# Smoke test function
smoke_test() {
    local port=$1
    local endpoint_base="http://localhost:$port"
    
    log "🧪 Running smoke tests against port $port..."
    
    # Test 1: Health endpoints
    if ! curl -s -f "$endpoint_base/health/live" > /dev/null; then
        log "❌ Smoke test failed: /health/live"
        return 1
    fi
    
    if ! curl -s -f "$endpoint_base/health/ready" > /dev/null; then
        log "❌ Smoke test failed: /health/ready"
        return 1
    fi
    
    if ! curl -s -f "$endpoint_base/health/startup" > /dev/null; then
        log "❌ Smoke test failed: /health/startup"
        return 1
    fi
    
    # Test 2: API endpoints (no auth needed)
    if ! curl -s -f "$endpoint_base/docs" > /dev/null; then
        log "❌ Smoke test failed: /docs (OpenAPI)"
        return 1
    fi
    
    # Test 3: Database connectivity (via health check response)
    health_response=$(curl -s "$endpoint_base/health/ready")
    if ! echo "$health_response" | grep -q "healthy"; then
        log "❌ Smoke test failed: Database connectivity check"
        return 1
    fi
    
    log "✅ All smoke tests passed"
    return 0
}

# Pre-deployment checks
pre_deployment_checks() {
    log "🔍 Running pre-deployment checks..."
    
    # Check 1: Git status (ensure clean state)
    if ! git diff-index --quiet HEAD --; then
        log "⚠️  Warning: Uncommitted changes detected"
    fi
    
    # Check 2: Database migrations (dry run)
    log "📊 Checking database migrations..."
    if [ -f "alembic.ini" ]; then
        # In production, this would run: alembic check
        log "✅ Migration check passed (simulated)"
    fi
    
    # Check 3: Environment variables
    if [ -z "${DATABASE_URL:-}" ]; then
        log "⚠️  Warning: DATABASE_URL not set"
    fi
    
    # Check 4: Required dependencies
    if ! python3 -c "import fastapi, sqlalchemy, pydantic" 2>/dev/null; then
        log "❌ Missing required dependencies"
        return 1
    fi
    
    log "✅ Pre-deployment checks passed"
    return 0
}

# Start application on specific port
start_app() {
    local port=$1
    local env_file=${2:-".env.dev"}
    
    log "🚀 Starting application on port $port with environment $env_file..."
    
    # Load environment
    if [ -f "$env_file" ]; then
        set -a
        source "$env_file"
        set +a
    fi
    
    # Start server in background
    nohup python3 -m uvicorn app.main:app \
        --host 0.0.0.0 \
        --port $port \
        --reload \
        > "ops/app_port_$port.log" 2>&1 &
    
    local pid=$!
    echo $pid > "ops/app_port_$port.pid"
    
    log "📋 Application started with PID: $pid"
    
    # Wait for startup
    sleep 5
    
    # Verify process is running
    if ! kill -0 $pid 2>/dev/null; then
        log "❌ Application failed to start"
        return 1
    fi
    
    return 0
}

# Stop application on specific port
stop_app() {
    local port=$1
    local pid_file="ops/app_port_$port.pid"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        
        if kill -0 $pid 2>/dev/null; then
            log "🛑 Stopping application on port $port (PID: $pid)..."
            kill $pid
            
            # Wait for graceful shutdown
            sleep 5
            
            # Force kill if still running
            if kill -0 $pid 2>/dev/null; then
                kill -9 $pid
                log "⚡ Force killed application (PID: $pid)"
            fi
        fi
        
        rm -f "$pid_file"
    fi
}

# Blue-Green deployment
blue_green_deploy() {
    log "🔄 Starting Blue-Green Deployment..."
    log "================================================"
    
    # Determine current active deployment
    local current_port
    local new_port
    
    if health_check $BLUE_PORT 1; then
        # Blue is active, deploy to green
        current_port=$BLUE_PORT
        new_port=$GREEN_PORT
        log "📊 Current active: BLUE (port $current_port)"
        log "🎯 Deploying to: GREEN (port $new_port)"
    else
        # Deploy to blue (initial deployment or green is active)
        current_port=$GREEN_PORT
        new_port=$BLUE_PORT
        log "📊 Current active: GREEN (port $current_port) or initial deployment"
        log "🎯 Deploying to: BLUE (port $new_port)"
    fi
    
    # Stop new deployment port if running
    stop_app $new_port
    
    # Start new deployment
    if ! start_app $new_port ".env.dev"; then
        log "❌ Failed to start new deployment"
        return 1
    fi
    
    # Health check new deployment
    log "🏥 Health checking new deployment..."
    if ! health_check $new_port $HEALTH_CHECK_TIMEOUT; then
        log "❌ New deployment health check failed"
        stop_app $new_port
        return 1
    fi
    
    log "✅ New deployment health check passed"
    
    # Run smoke tests
    if ! smoke_test $new_port; then
        log "❌ Smoke tests failed on new deployment"
        stop_app $new_port
        return 1
    fi
    
    log "✅ Smoke tests passed"
    
    # Switch traffic (in production, this would update load balancer)
    log "🔀 Switching traffic to new deployment (port $new_port)..."
    
    # Simulate traffic switch with symbolic link or configuration update
    echo "$new_port" > ops/active_port.txt
    
    # Wait a moment for traffic to stabilize
    sleep 3
    
    # Verify active deployment is still healthy
    if ! health_check $new_port 5; then
        log "❌ Active deployment became unhealthy, rolling back..."
        echo "$current_port" > ops/active_port.txt
        return 1
    fi
    
    # Stop old deployment
    if [ "$current_port" != "$new_port" ]; then
        log "🧹 Stopping old deployment (port $current_port)..."
        stop_app $current_port
    fi
    
    log "🎉 Blue-Green deployment completed successfully!"
    log "📋 Active deployment: $([ $new_port -eq $BLUE_PORT ] && echo "BLUE" || echo "GREEN") (port $new_port)"
    
    return 0
}

# Rolling deployment (alternative strategy)
rolling_deploy() {
    log "🔄 Starting Rolling Deployment..."
    log "================================================"
    
    # For demo, we'll simulate a rolling update on blue port
    local active_port=$BLUE_PORT
    
    log "📊 Active port: $active_port"
    
    # Gracefully stop current application
    log "🛑 Gracefully stopping current application..."
    stop_app $active_port
    
    # Quick downtime (< 5 seconds for rolling update simulation)
    sleep 2
    
    # Start new version
    if ! start_app $active_port ".env.dev"; then
        log "❌ Rolling deployment failed"
        return 1
    fi
    
    # Health check
    if ! health_check $active_port $HEALTH_CHECK_TIMEOUT; then
        log "❌ Rolling deployment health check failed"
        return 1
    fi
    
    # Smoke tests
    if ! smoke_test $active_port; then
        log "❌ Rolling deployment smoke tests failed"
        return 1
    fi
    
    log "🎉 Rolling deployment completed successfully!"
    
    return 0
}

# Rollback function
rollback() {
    log "⏪ Initiating rollback..."
    
    if [ -f "ops/active_port.txt" ]; then
        local current_port=$(cat ops/active_port.txt)
        local rollback_port
        
        if [ "$current_port" == "$BLUE_PORT" ]; then
            rollback_port=$GREEN_PORT
        else
            rollback_port=$BLUE_PORT
        fi
        
        log "🔀 Rolling back from port $current_port to port $rollback_port"
        
        stop_app $current_port
        
        if start_app $rollback_port ".env.dev"; then
            if health_check $rollback_port $HEALTH_CHECK_TIMEOUT; then
                echo "$rollback_port" > ops/active_port.txt
                log "✅ Rollback completed successfully"
                return 0
            fi
        fi
    fi
    
    log "❌ Rollback failed"
    return 1
}

# Main deployment function
main() {
    local action=${1:-"deploy"}
    
    case $action in
        "deploy")
            echo "🚀 SME ERP Safe Deployment System"
            echo "================================="
            echo "Mode: $DEPLOYMENT_MODE"
            echo ""
            
            # Pre-deployment checks
            if ! pre_deployment_checks; then
                echo "❌ Pre-deployment checks failed"
                exit 1
            fi
            
            # Execute deployment strategy
            if [ "$DEPLOYMENT_MODE" == "blue-green" ]; then
                if blue_green_deploy; then
                    echo "✅ Deployment successful!"
                    exit 0
                else
                    echo "❌ Deployment failed!"
                    exit 1
                fi
            elif [ "$DEPLOYMENT_MODE" == "rolling" ]; then
                if rolling_deploy; then
                    echo "✅ Deployment successful!"
                    exit 0
                else
                    echo "❌ Deployment failed!"
                    exit 1
                fi
            else
                echo "❌ Unknown deployment mode: $DEPLOYMENT_MODE"
                exit 1
            fi
            ;;
        
        "rollback")
            if rollback; then
                echo "✅ Rollback successful!"
                exit 0
            else
                echo "❌ Rollback failed!"
                exit 1
            fi
            ;;
        
        "status")
            echo "📊 Deployment Status:"
            echo "===================="
            
            if [ -f "ops/active_port.txt" ]; then
                local active_port=$(cat ops/active_port.txt)
                echo "Active deployment: port $active_port"
                
                if health_check $active_port 1; then
                    echo "Status: ✅ Healthy"
                else
                    echo "Status: ❌ Unhealthy"
                fi
            else
                echo "No active deployment detected"
            fi
            ;;
        
        "cleanup")
            log "🧹 Cleaning up deployment artifacts..."
            stop_app $BLUE_PORT
            stop_app $GREEN_PORT
            rm -f ops/active_port.txt
            rm -f ops/app_port_*.pid
            rm -f ops/app_port_*.log
            log "✅ Cleanup completed"
            ;;
        
        *)
            echo "Usage: $0 {deploy|rollback|status|cleanup}"
            echo ""
            echo "Environment variables:"
            echo "  DEPLOYMENT_MODE: blue-green (default) or rolling"
            echo "  BLUE_PORT: $BLUE_PORT (default)"
            echo "  GREEN_PORT: $GREEN_PORT (default)"
            exit 1
            ;;
    esac
}

# Create ops directory if it doesn't exist
mkdir -p ops

# Run main function with arguments
main "$@"