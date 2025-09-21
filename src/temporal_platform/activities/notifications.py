"""
Notification activities implementing Pattern 3: Fire-and-Forget.
Demonstrates background task execution without waiting for completion.
"""
import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from temporalio import activity
import structlog
import httpx

from ..models.workflows import NotificationEvent, Priority
from ..exceptions.core import ActivityExecutionError, RateLimitError
from ..config.settings import settings

logger = structlog.get_logger(__name__)


@activity.defn
async def send_webhook_notification(notification: NotificationEvent) -> Dict[str, Any]:
    """
    Send webhook notification for fire-and-forget operations.
    Implements Pattern 3: Fire-and-Forget background task execution.
    
    Args:
        notification: The notification event to send
        
    Returns:
        Dictionary with notification delivery result
        
    Raises:
        ActivityExecutionError: When notification delivery fails
    """
    start_time = time.time()
    
    logger.info(
        "Sending webhook notification",
        event_type=notification.event_type,
        source_workflow_id=notification.source_workflow_id,
        target_endpoint=notification.target_endpoint,
        priority=notification.priority
    )
    
    try:
        # Prepare webhook payload
        payload = {
            "id": notification.id,
            "event_type": notification.event_type,
            "source_workflow_id": notification.source_workflow_id,
            "timestamp": notification.created_at.isoformat(),
            "priority": notification.priority.value,
            "data": notification.event_data
        }
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "TemporalPlatform/1.0",
            "X-Event-Type": notification.event_type,
            "X-Priority": notification.priority.value,
            "X-Timestamp": notification.created_at.isoformat()
        }
        
        # Add authentication if configured
        if settings.security.api_key_header and settings.security.jwt_secret:
            headers[settings.security.api_key_header] = settings.security.jwt_secret
        
        # Configure retry policy
        retry_config = notification.retry_policy or {
            "max_attempts": 3,
            "initial_delay": 1,
            "max_delay": 60,
            "backoff_multiplier": 2
        }
        
        # Send webhook with retries
        delivery_result = await _send_webhook_with_retries(
            url=notification.target_endpoint,
            payload=payload,
            headers=headers,
            retry_config=retry_config
        )
        
        delivery_time = time.time() - start_time
        
        result = {
            "notification_id": notification.id,
            "event_type": notification.event_type,
            "delivery_status": "success" if delivery_result["success"] else "failed",
            "delivery_time_seconds": delivery_time,
            "attempts": delivery_result["attempts"],
            "response_status": delivery_result.get("status_code"),
            "response_headers": delivery_result.get("response_headers", {}),
            "error_message": delivery_result.get("error_message")
        }
        
        if delivery_result["success"]:
            logger.info(
                "Webhook notification delivered successfully",
                notification_id=notification.id,
                attempts=delivery_result["attempts"],
                delivery_time_seconds=delivery_time,
                response_status=delivery_result.get("status_code")
            )
        else:
            logger.error(
                "Webhook notification delivery failed",
                notification_id=notification.id,
                attempts=delivery_result["attempts"],
                error=delivery_result.get("error_message"),
                delivery_time_seconds=delivery_time
            )
        
        return result
        
    except Exception as e:
        delivery_time = time.time() - start_time
        error_msg = f"Webhook notification failed: {str(e)}"
        
        logger.error(
            error_msg,
            notification_id=notification.id,
            delivery_time_seconds=delivery_time,
            error=str(e),
            error_type=type(e).__name__
        )
        
        return {
            "notification_id": notification.id,
            "event_type": notification.event_type,
            "delivery_status": "error",
            "delivery_time_seconds": delivery_time,
            "attempts": 0,
            "error_message": error_msg,
            "error_type": type(e).__name__
        }


async def _send_webhook_with_retries(
    url: str,
    payload: Dict[str, Any],
    headers: Dict[str, str],
    retry_config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Send webhook with exponential backoff retry logic.
    
    Args:
        url: Target webhook URL
        payload: JSON payload to send
        headers: HTTP headers
        retry_config: Retry configuration
        
    Returns:
        Dictionary with delivery result and metadata
    """
    max_attempts = retry_config.get("max_attempts", 3)
    initial_delay = retry_config.get("initial_delay", 1)
    max_delay = retry_config.get("max_delay", 60)
    backoff_multiplier = retry_config.get("backoff_multiplier", 2)
    
    last_error = None
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for attempt in range(1, max_attempts + 1):
            try:
                logger.debug(
                    "Sending webhook request",
                    url=url,
                    attempt=attempt,
                    max_attempts=max_attempts
                )
                
                response = await client.post(
                    url=url,
                    json=payload,
                    headers=headers
                )
                
                # Check if request was successful
                if response.status_code < 400:
                    return {
                        "success": True,
                        "attempts": attempt,
                        "status_code": response.status_code,
                        "response_headers": dict(response.headers),
                        "response_body": response.text[:500] if response.text else None
                    }
                
                # Handle specific HTTP errors
                if response.status_code == 429:  # Rate limited
                    retry_after = response.headers.get("Retry-After", initial_delay)
                    try:
                        retry_delay = int(retry_after)
                    except (ValueError, TypeError):
                        retry_delay = initial_delay
                    
                    logger.warning(
                        "Webhook rate limited",
                        url=url,
                        attempt=attempt,
                        retry_after=retry_delay,
                        status_code=response.status_code
                    )
                    
                    if attempt < max_attempts:
                        await asyncio.sleep(min(retry_delay, max_delay))
                        continue
                    else:
                        raise RateLimitError(
                            f"Webhook rate limited after {max_attempts} attempts",
                            retry_after_seconds=retry_delay
                        )
                
                elif 400 <= response.status_code < 500:
                    # Client errors - don't retry
                    return {
                        "success": False,
                        "attempts": attempt,
                        "status_code": response.status_code,
                        "error_message": f"Client error: {response.status_code} - {response.text[:200]}",
                        "response_headers": dict(response.headers)
                    }
                
                else:
                    # Server errors - retry
                    last_error = f"Server error: {response.status_code} - {response.text[:200]}"
                    logger.warning(
                        "Webhook server error",
                        url=url,
                        attempt=attempt,
                        status_code=response.status_code,
                        error=last_error
                    )
                
            except httpx.RequestError as e:
                last_error = f"Network error: {str(e)}"
                logger.warning(
                    "Webhook network error",
                    url=url,
                    attempt=attempt,
                    error=last_error
                )
            
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(
                    "Webhook unexpected error",
                    url=url,
                    attempt=attempt,
                    error=last_error,
                    error_type=type(e).__name__
                )
            
            # Calculate delay before next retry
            if attempt < max_attempts:
                delay = min(initial_delay * (backoff_multiplier ** (attempt - 1)), max_delay)
                logger.debug(
                    "Retrying webhook after delay",
                    url=url,
                    attempt=attempt,
                    next_delay_seconds=delay
                )
                await asyncio.sleep(delay)
    
    # All attempts failed
    return {
        "success": False,
        "attempts": max_attempts,
        "error_message": last_error or "Unknown error after all retry attempts"
    }


@activity.defn
async def send_email_notification(
    recipient: str,
    subject: str,
    content: str,
    content_type: str = "text/plain",
    priority: Priority = Priority.MEDIUM
) -> Dict[str, Any]:
    """
    Send email notification as a fire-and-forget background task.
    
    Args:
        recipient: Email recipient address
        subject: Email subject
        content: Email content
        content_type: Content type (text/plain or text/html)
        priority: Email priority
        
    Returns:
        Dictionary with email delivery result
    """
    start_time = time.time()
    
    logger.info(
        "Sending email notification",
        recipient=recipient,
        subject=subject,
        content_type=content_type,
        priority=priority
    )
    
    try:
        # Simulate email service integration
        # In production, this would integrate with services like:
        # - Amazon SES
        # - SendGrid
        # - Mailgun
        # - SMTP server
        
        # Simulate email preparation and validation
        await asyncio.sleep(0.1)
        
        # Validate email address format
        if "@" not in recipient or "." not in recipient.split("@")[-1]:
            raise ValueError(f"Invalid email address: {recipient}")
        
        # Simulate email sending delay based on content size and priority
        content_size = len(content.encode('utf-8'))
        base_delay = 0.5  # Base sending delay
        
        # Priority affects sending delay
        priority_multipliers = {
            Priority.CRITICAL: 0.1,
            Priority.HIGH: 0.3,
            Priority.MEDIUM: 1.0,
            Priority.LOW: 2.0
        }
        
        sending_delay = base_delay * priority_multipliers[priority]
        
        # Large content takes longer to send
        if content_size > 10000:  # 10KB
            sending_delay *= 1.5
        
        await asyncio.sleep(sending_delay)
        
        # Simulate occasional failures (2% failure rate)
        import random
        if random.random() < 0.02:
            raise Exception("Email service temporarily unavailable")
        
        delivery_time = time.time() - start_time
        
        result = {
            "recipient": recipient,
            "subject": subject,
            "content_size_bytes": content_size,
            "content_type": content_type,
            "priority": priority.value,
            "delivery_status": "sent",
            "delivery_time_seconds": delivery_time,
            "message_id": f"msg_{int(time.time())}_{hash(recipient) % 10000}",
            "smtp_response": "250 2.0.0 Message accepted for delivery"
        }
        
        logger.info(
            "Email notification sent successfully",
            recipient=recipient,
            message_id=result["message_id"],
            delivery_time_seconds=delivery_time
        )
        
        return result
        
    except Exception as e:
        delivery_time = time.time() - start_time
        error_msg = f"Email notification failed: {str(e)}"
        
        logger.error(
            error_msg,
            recipient=recipient,
            subject=subject,
            delivery_time_seconds=delivery_time,
            error=str(e),
            error_type=type(e).__name__
        )
        
        return {
            "recipient": recipient,
            "subject": subject,
            "content_type": content_type,
            "priority": priority.value,
            "delivery_status": "failed",
            "delivery_time_seconds": delivery_time,
            "error_message": error_msg,
            "error_type": type(e).__name__
        }


@activity.defn
async def log_audit_event(
    event_type: str,
    user_id: str,
    resource_id: str,
    action: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Log audit events for compliance and monitoring.
    Fire-and-forget operation for security and compliance tracking.
    
    Args:
        event_type: Type of audit event
        user_id: User who performed the action
        resource_id: Resource that was affected
        action: Action that was performed
        metadata: Additional event metadata
        
    Returns:
        Dictionary with audit logging result
    """
    start_time = time.time()
    
    logger.info(
        "Logging audit event",
        event_type=event_type,
        user_id=user_id,
        resource_id=resource_id,
        action=action
    )
    
    try:
        # Create audit log entry
        audit_entry = {
            "id": f"audit_{int(time.time())}_{hash(user_id + resource_id) % 10000}",
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "resource_id": resource_id,
            "action": action,
            "metadata": metadata or {},
            "source": "temporal-platform",
            "version": "1.0.0"
        }
        
        # Simulate audit log storage
        # In production, this would store to:
        # - Elasticsearch for search and analysis
        # - PostgreSQL for relational queries
        # - AWS CloudTrail for compliance
        # - Splunk for enterprise monitoring
        
        await asyncio.sleep(0.1)  # Simulate storage operation
        
        # Simulate indexing for search
        await asyncio.sleep(0.05)
        
        logging_time = time.time() - start_time
        
        result = {
            "audit_id": audit_entry["id"],
            "event_type": event_type,
            "user_id": user_id,
            "resource_id": resource_id,
            "action": action,
            "logging_status": "success",
            "logging_time_seconds": logging_time,
            "storage_backend": "elasticsearch",
            "index_status": "indexed",
            "retention_days": 2555  # 7 years retention for compliance
        }
        
        logger.info(
            "Audit event logged successfully",
            audit_id=result["audit_id"],
            logging_time_seconds=logging_time
        )
        
        return result
        
    except Exception as e:
        logging_time = time.time() - start_time
        error_msg = f"Audit logging failed: {str(e)}"
        
        logger.error(
            error_msg,
            event_type=event_type,
            user_id=user_id,
            resource_id=resource_id,
            action=action,
            logging_time_seconds=logging_time,
            error=str(e),
            error_type=type(e).__name__
        )
        
        # Audit logging failure is critical for compliance
        raise ActivityExecutionError(
            error_msg,
            activity_type="log_audit_event",
            activity_id=f"{user_id}_{resource_id}_{action}",
            cause=e
        )


@activity.defn
async def update_metrics_dashboard(
    metric_name: str,
    metric_value: float,
    labels: Optional[Dict[str, str]] = None,
    timestamp: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Update metrics dashboard for monitoring and observability.
    Fire-and-forget operation for real-time metrics updates.
    
    Args:
        metric_name: Name of the metric to update
        metric_value: Value of the metric
        labels: Metric labels for dimensionality
        timestamp: Metric timestamp (defaults to current time)
        
    Returns:
        Dictionary with metrics update result
    """
    start_time = time.time()
    
    logger.debug(
        "Updating metrics dashboard",
        metric_name=metric_name,
        metric_value=metric_value,
        labels=labels
    )
    
    try:
        # Prepare metric entry
        metric_timestamp = timestamp or datetime.utcnow()
        metric_labels = labels or {}
        
        metric_entry = {
            "name": metric_name,
            "value": metric_value,
            "labels": metric_labels,
            "timestamp": metric_timestamp.isoformat(),
            "source": "temporal-platform"
        }
        
        # Simulate metrics storage
        # In production, this would push to:
        # - Prometheus for time-series storage
        # - InfluxDB for high-cardinality metrics
        # - CloudWatch for AWS environments
        # - Datadog for SaaS monitoring
        
        await asyncio.sleep(0.02)  # Simulate metrics push
        
        update_time = time.time() - start_time
        
        result = {
            "metric_name": metric_name,
            "metric_value": metric_value,
            "labels": metric_labels,
            "timestamp": metric_timestamp.isoformat(),
            "update_status": "success",
            "update_time_seconds": update_time,
            "metrics_backend": "prometheus",
            "scrape_interval_seconds": 15
        }
        
        return result
        
    except Exception as e:
        update_time = time.time() - start_time
        error_msg = f"Metrics update failed: {str(e)}"
        
        logger.warning(
            error_msg,
            metric_name=metric_name,
            metric_value=metric_value,
            update_time_seconds=update_time,
            error=str(e),
            error_type=type(e).__name__
        )
        
        # Metrics failures are non-critical, return error result
        return {
            "metric_name": metric_name,
            "metric_value": metric_value,
            "labels": labels or {},
            "update_status": "failed",
            "update_time_seconds": update_time,
            "error_message": error_msg,
            "error_type": type(e).__name__
        }
