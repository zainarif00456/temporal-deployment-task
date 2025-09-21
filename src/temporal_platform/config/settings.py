"""
Production-grade configuration management using Pydantic v2.
All configuration is environment variable based with proper validation.
"""
from typing import List, Optional
from pydantic import BaseSettings, Field, validator
from pydantic_settings import BaseSettings as PydanticSettings


class DatabaseConfig(BaseSettings):
    """Database configuration with connection pooling support."""
    
    postgresql_host: str = Field(default="localhost", env="POSTGRESQL_HOST")
    postgresql_port: int = Field(default=5432, env="POSTGRESQL_PORT")
    postgresql_database: str = Field(default="temporal", env="POSTGRESQL_DATABASE")
    postgresql_user: str = Field(default="temporal", env="POSTGRESQL_USER")
    postgresql_password: str = Field(default="temporal", env="POSTGRESQL_PASSWORD")
    postgresql_pool_size: int = Field(default=20, env="POSTGRESQL_POOL_SIZE")
    postgresql_max_overflow: int = Field(default=30, env="POSTGRESQL_MAX_OVERFLOW")
    postgresql_pool_timeout: int = Field(default=30, env="POSTGRESQL_POOL_TIMEOUT")
    
    @property
    def postgresql_dsn(self) -> str:
        """Generate PostgreSQL connection string."""
        return (
            f"postgresql://{self.postgresql_user}:{self.postgresql_password}"
            f"@{self.postgresql_host}:{self.postgresql_port}/{self.postgresql_database}"
        )


class ElasticsearchConfig(BaseSettings):
    """Elasticsearch configuration for Temporal visibility."""
    
    elasticsearch_host: str = Field(default="localhost", env="ELASTICSEARCH_HOST")
    elasticsearch_port: int = Field(default=9200, env="ELASTICSEARCH_PORT")
    elasticsearch_scheme: str = Field(default="http", env="ELASTICSEARCH_SCHEME")
    elasticsearch_username: Optional[str] = Field(default=None, env="ELASTICSEARCH_USERNAME")
    elasticsearch_password: Optional[str] = Field(default=None, env="ELASTICSEARCH_PASSWORD")
    elasticsearch_index: str = Field(default="temporal_visibility_v1_dev", env="ELASTICSEARCH_INDEX")
    elasticsearch_version: str = Field(default="7.17", env="ELASTICSEARCH_VERSION")
    
    @property
    def elasticsearch_url(self) -> str:
        """Generate Elasticsearch connection URL."""
        auth = ""
        if self.elasticsearch_username and self.elasticsearch_password:
            auth = f"{self.elasticsearch_username}:{self.elasticsearch_password}@"
        
        return f"{self.elasticsearch_scheme}://{auth}{self.elasticsearch_host}:{self.elasticsearch_port}"


class TemporalConfig(BaseSettings):
    """Temporal cluster configuration."""
    
    temporal_host: str = Field(default="localhost", env="TEMPORAL_HOST")
    temporal_port: int = Field(default=7233, env="TEMPORAL_PORT")
    temporal_namespace: str = Field(default="default", env="TEMPORAL_NAMESPACE")
    temporal_task_queue: str = Field(default="temporal-platform-task-queue", env="TEMPORAL_TASK_QUEUE")
    temporal_ui_port: int = Field(default=8080, env="TEMPORAL_UI_PORT")
    
    # Service-specific configurations
    temporal_frontend_port: int = Field(default=7233, env="TEMPORAL_FRONTEND_PORT")
    temporal_history_port: int = Field(default=7234, env="TEMPORAL_HISTORY_PORT")
    temporal_matching_port: int = Field(default=7235, env="TEMPORAL_MATCHING_PORT")
    temporal_worker_port: int = Field(default=7239, env="TEMPORAL_WORKER_PORT")
    
    @property
    def temporal_address(self) -> str:
        """Generate Temporal server address."""
        return f"{self.temporal_host}:{self.temporal_port}"


class WorkflowConfig(BaseSettings):
    """Workflow execution configuration."""
    
    max_concurrent_workflows: int = Field(default=1000, env="MAX_CONCURRENT_WORKFLOWS")
    max_concurrent_activities: int = Field(default=1000, env="MAX_CONCURRENT_ACTIVITIES")
    workflow_execution_timeout_seconds: int = Field(
        default=3600, env="WORKFLOW_EXECUTION_TIMEOUT_SECONDS"
    )
    activity_execution_timeout_seconds: int = Field(
        default=300, env="ACTIVITY_EXECUTION_TIMEOUT_SECONDS"
    )
    activity_retry_maximum_attempts: int = Field(
        default=5, env="ACTIVITY_RETRY_MAXIMUM_ATTEMPTS"
    )
    activity_retry_initial_interval_seconds: int = Field(
        default=1, env="ACTIVITY_RETRY_INITIAL_INTERVAL_SECONDS"
    )
    activity_retry_maximum_interval_seconds: int = Field(
        default=60, env="ACTIVITY_RETRY_MAXIMUM_INTERVAL_SECONDS"
    )
    activity_retry_backoff_coefficient: float = Field(
        default=2.0, env="ACTIVITY_RETRY_BACKOFF_COEFFICIENT"
    )
    
    # Long-running operation configuration
    heartbeat_interval_seconds: int = Field(default=10, env="HEARTBEAT_INTERVAL_SECONDS")
    progress_update_interval_seconds: int = Field(
        default=5, env="PROGRESS_UPDATE_INTERVAL_SECONDS"
    )


class LoggingConfig(BaseSettings):
    """Structured logging configuration."""
    
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")  # json or text
    log_output: str = Field(default="stdout", env="LOG_OUTPUT")  # stdout, file, or both
    log_file_path: str = Field(default="./logs/temporal-platform.log", env="LOG_FILE_PATH")
    log_rotation_size: str = Field(default="100MB", env="LOG_ROTATION_SIZE")
    log_retention_days: int = Field(default=30, env="LOG_RETENTION_DAYS")
    
    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()


class SecurityConfig(BaseSettings):
    """Security configuration."""
    
    enable_tls: bool = Field(default=False, env="ENABLE_TLS")
    tls_cert_path: Optional[str] = Field(default=None, env="TLS_CERT_PATH")
    tls_key_path: Optional[str] = Field(default=None, env="TLS_KEY_PATH")
    tls_ca_path: Optional[str] = Field(default=None, env="TLS_CA_PATH")
    enable_auth: bool = Field(default=False, env="ENABLE_AUTH")
    jwt_secret: Optional[str] = Field(default=None, env="JWT_SECRET")
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    
    @validator("tls_cert_path")
    def validate_tls_config(cls, v: Optional[str], values: dict) -> Optional[str]:
        """Validate TLS configuration consistency."""
        if values.get("enable_tls") and not v:
            raise ValueError("TLS cert path required when TLS is enabled")
        return v


class MonitoringConfig(BaseSettings):
    """Monitoring and observability configuration."""
    
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    metrics_path: str = Field(default="/metrics", env="METRICS_PATH")
    enable_tracing: bool = Field(default=True, env="ENABLE_TRACING")
    jaeger_endpoint: Optional[str] = Field(default=None, env="JAEGER_ENDPOINT")
    enable_health_checks: bool = Field(default=True, env="ENABLE_HEALTH_CHECKS")
    health_check_port: int = Field(default=8081, env="HEALTH_CHECK_PORT")


class Settings(PydanticSettings):
    """
    Main settings class that aggregates all configuration sections.
    Uses environment variables with proper validation and defaults.
    """
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Configuration sections
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    elasticsearch: ElasticsearchConfig = Field(default_factory=ElasticsearchConfig)
    temporal: TemporalConfig = Field(default_factory=TemporalConfig)
    workflow: WorkflowConfig = Field(default_factory=WorkflowConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "forbid"
    
    @validator("environment")
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        valid_envs = ["development", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"Environment must be one of {valid_envs}")
        return v.lower()
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == "development"


# Global settings instance
settings = Settings()
