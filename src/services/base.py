"""
业务服务层基础架构

提供业务服务层的基础类和接口，包括事务管理、错误处理等。
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, Any, Dict, List
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime

from ..database.repositories.factory import RepositoryFactory

# 泛型类型
ServiceResult = TypeVar("ServiceResult")
logger = logging.getLogger(__name__)


class ServiceError(Exception):
    """服务层异常基类"""
    def __init__(self, message: str, error_code: str = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "SERVICE_ERROR"
        self.details = details or {}
        self.timestamp = datetime.utcnow()


class ValidationError(ServiceError):
    """数据验证异常"""
    def __init__(self, message: str, field: str = None, details: Dict[str, Any] = None):
        super().__init__(message, "VALIDATION_ERROR", details)
        self.field = field


class BusinessLogicError(ServiceError):
    """业务逻辑异常"""
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(message, "BUSINESS_LOGIC_ERROR", details)


class ResourceNotFoundError(ServiceError):
    """资源不存在异常"""
    def __init__(self, resource_type: str, resource_id: Any, details: Dict[str, Any] = None):
        message = f"{resource_type} with id {resource_id} not found"
        super().__init__(message, "RESOURCE_NOT_FOUND", details)
        self.resource_type = resource_type
        self.resource_id = resource_id


class PermissionDeniedError(ServiceError):
    """权限拒绝异常"""
    def __init__(self, message: str = "Permission denied", details: Dict[str, Any] = None):
        super().__init__(message, "PERMISSION_DENIED", details)


class ServiceResult(Generic[ServiceResult]):
    """服务结果封装"""
    
    def __init__(
        self, 
        success: bool,
        data: ServiceResult = None,
        error: ServiceError = None,
        message: str = None
    ):
        self.success = success
        self.data = data
        self.error = error
        self.message = message
        self.timestamp = datetime.utcnow()
    
    @classmethod
    def success_result(cls, data: ServiceResult = None, message: str = None) -> "ServiceResult[ServiceResult]":
        """创建成功结果"""
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error_result(cls, error: ServiceError, message: str = None) -> "ServiceResult[ServiceResult]":
        """创建错误结果"""
        return cls(success=False, error=error, message=message or str(error))
    
    @classmethod
    def validation_error(cls, message: str, field: str = None) -> "ServiceResult[ServiceResult]":
        """创建验证错误结果"""
        error = ValidationError(message, field)
        return cls.error_result(error)
    
    @classmethod
    def not_found_error(cls, resource_type: str, resource_id: Any) -> "ServiceResult[ServiceResult]":
        """创建资源不存在错误结果"""
        error = ResourceNotFoundError(resource_type, resource_id)
        return cls.error_result(error)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "success": self.success,
            "timestamp": self.timestamp.isoformat()
        }
        
        if self.success:
            result["data"] = self.data
            if self.message:
                result["message"] = self.message
        else:
            result["error"] = {
                "code": self.error.error_code,
                "message": self.error.message,
                "details": self.error.details
            }
        
        return result


class BaseService(ABC):
    """业务服务基类"""
    
    def __init__(self, repository_factory: RepositoryFactory):
        """
        初始化服务
        
        Args:
            repository_factory: Repository工厂实例
        """
        self.repos = repository_factory
        self.logger = logging.getLogger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    @asynccontextmanager
    async def transaction(self):
        """
        事务上下文管理器
        
        使用示例:
            async with service.transaction():
                await service.some_operation()
                await service.another_operation()
        """
        try:
            self.logger.debug("开始事务")
            yield self.repos
            await self.repos.session.commit()
            self.logger.debug("事务提交成功")
        except Exception as e:
            self.logger.error(f"事务回滚: {e}")
            await self.repos.session.rollback()
            raise
    
    async def _handle_service_error(
        self, 
        operation: str, 
        error: Exception
    ) -> ServiceResult[Any]:
        """
        处理服务异常
        
        Args:
            operation: 操作名称
            error: 异常对象
            
        Returns:
            错误结果
        """
        self.logger.error(f"{operation} 失败: {error}", exc_info=True)
        
        if isinstance(error, ServiceError):
            return ServiceResult.error_result(error)
        elif isinstance(error, SQLAlchemyError):
            service_error = ServiceError(
                message=f"数据库操作失败: {str(error)}",
                error_code="DATABASE_ERROR",
                details={"operation": operation}
            )
            return ServiceResult.error_result(service_error)
        else:
            service_error = ServiceError(
                message=f"未知错误: {str(error)}",
                error_code="INTERNAL_ERROR", 
                details={"operation": operation}
            )
            return ServiceResult.error_result(service_error)
    
    def _validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> None:
        """
        验证必需字段
        
        Args:
            data: 数据字典
            required_fields: 必需字段列表
            
        Raises:
            ValidationError: 字段验证失败
        """
        for field in required_fields:
            if field not in data or data[field] is None:
                raise ValidationError(f"字段 '{field}' 是必需的", field=field)
            
            # 检查字符串字段是否为空
            if isinstance(data[field], str) and not data[field].strip():
                raise ValidationError(f"字段 '{field}' 不能为空", field=field)
    
    def _validate_field_length(
        self, 
        value: str, 
        field_name: str, 
        max_length: int, 
        min_length: int = 0
    ) -> None:
        """
        验证字段长度
        
        Args:
            value: 字段值
            field_name: 字段名
            max_length: 最大长度
            min_length: 最小长度
            
        Raises:
            ValidationError: 长度验证失败
        """
        if len(value) < min_length:
            raise ValidationError(
                f"字段 '{field_name}' 长度不能少于 {min_length} 个字符",
                field=field_name
            )
        
        if len(value) > max_length:
            raise ValidationError(
                f"字段 '{field_name}' 长度不能超过 {max_length} 个字符",
                field=field_name
            )
    
    def _sanitize_search_query(self, query: str, max_length: int = 100) -> str:
        """
        清理搜索查询
        
        Args:
            query: 搜索查询
            max_length: 最大长度
            
        Returns:
            清理后的查询
        """
        if not query:
            return ""
        
        # 移除前后空白
        query = query.strip()
        
        # 限制长度
        if len(query) > max_length:
            query = query[:max_length]
        
        # 移除危险字符（防SQL注入，虽然我们使用参数化查询）
        dangerous_chars = ['--', ';', '/*', '*/', 'xp_', 'sp_']
        for char in dangerous_chars:
            query = query.replace(char, '')
        
        return query
    
    async def _check_resource_exists(
        self, 
        resource_id: int, 
        resource_type: str,
        repository_method: callable
    ) -> Any:
        """
        检查资源是否存在
        
        Args:
            resource_id: 资源ID
            resource_type: 资源类型名称
            repository_method: Repository查询方法
            
        Returns:
            资源对象
            
        Raises:
            ResourceNotFoundError: 资源不存在
        """
        resource = await repository_method(resource_id)
        if not resource:
            raise ResourceNotFoundError(resource_type, resource_id)
        return resource
    
    @abstractmethod
    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """
        服务健康检查
        
        Returns:
            健康状态结果
        """
        pass


class ServiceMetrics:
    """服务指标收集"""
    
    def __init__(self):
        self.operation_counts = {}
        self.error_counts = {}
        self.response_times = {}
    
    def record_operation(self, operation: str, duration: float, success: bool):
        """记录操作指标"""
        # 操作计数
        self.operation_counts[operation] = self.operation_counts.get(operation, 0) + 1
        
        # 错误计数
        if not success:
            self.error_counts[operation] = self.error_counts.get(operation, 0) + 1
        
        # 响应时间
        if operation not in self.response_times:
            self.response_times[operation] = []
        self.response_times[operation].append(duration)
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取指标摘要"""
        metrics = {
            "total_operations": sum(self.operation_counts.values()),
            "total_errors": sum(self.error_counts.values()),
            "operations": {}
        }
        
        for operation, count in self.operation_counts.items():
            error_count = self.error_counts.get(operation, 0)
            times = self.response_times.get(operation, [])
            
            metrics["operations"][operation] = {
                "count": count,
                "errors": error_count,
                "success_rate": (count - error_count) / count * 100 if count > 0 else 0,
                "avg_response_time": sum(times) / len(times) if times else 0,
                "max_response_time": max(times) if times else 0,
                "min_response_time": min(times) if times else 0
            }
        
        return metrics


def service_operation(operation_name: str = None):
    """
    服务操作装饰器，用于统计指标和异常处理
    
    Args:
        operation_name: 操作名称，默认使用方法名
    """
    def decorator(func):
        async def wrapper(self, *args, **kwargs):
            op_name = operation_name or func.__name__
            start_time = datetime.utcnow()
            
            try:
                result = await func(self, *args, **kwargs)
                
                # 记录成功指标
                duration = (datetime.utcnow() - start_time).total_seconds()
                if hasattr(self, 'metrics') and self.metrics:
                    self.metrics.record_operation(op_name, duration, True)
                
                return result
                
            except Exception as e:
                # 记录失败指标
                duration = (datetime.utcnow() - start_time).total_seconds()
                if hasattr(self, 'metrics') and self.metrics:
                    self.metrics.record_operation(op_name, duration, False)
                
                # 处理异常
                if isinstance(self, BaseService):
                    return await self._handle_service_error(op_name, e)
                else:
                    raise
        
        return wrapper
    return decorator