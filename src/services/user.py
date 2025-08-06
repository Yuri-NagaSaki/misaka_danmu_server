"""
用户和认证业务服务

提供用户管理、认证、权限控制等业务逻辑。
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
import hashlib
import secrets
import jwt
from dataclasses import dataclass

from .base import BaseService, ServiceResult, ServiceError, ValidationError, BusinessLogicError, PermissionDeniedError, service_operation
from ..database.models.user import User, APIToken, BangumiAuth, OAuthState
from ..database.repositories.factory import RepositoryFactory


@dataclass
class AuthContext:
    """认证上下文"""
    user_id: int
    username: str
    token_type: str  # jwt, api_token
    permissions: List[str]
    expires_at: Optional[datetime] = None


class UserService(BaseService):
    """用户业务服务"""
    
    def __init__(self, repository_factory: RepositoryFactory):
        super().__init__(repository_factory)
        self.metrics = None
    
    @service_operation("create_user")
    async def create_user(
        self,
        username: str,
        password: str,
        validate_strength: bool = True
    ) -> ServiceResult[Dict[str, Any]]:
        """
        创建用户
        
        Args:
            username: 用户名
            password: 密码
            validate_strength: 是否验证密码强度
            
        Returns:
            创建结果
        """
        try:
            # 验证用户名
            if not username or not username.strip():
                return ServiceResult.validation_error("用户名不能为空", "username")
            
            username = username.strip()
            self._validate_field_length(username, "username", 50, 3)
            
            # 检查用户名是否已存在
            existing_user = await self.repos.user.get_by_username(username)
            if existing_user:
                return ServiceResult.validation_error(
                    f"用户名 '{username}' 已存在", "username"
                )
            
            # 验证密码
            if not password:
                return ServiceResult.validation_error("密码不能为空", "password")
            
            if validate_strength:
                password_validation = self._validate_password_strength(password)
                if not password_validation["valid"]:
                    return ServiceResult.validation_error(
                        password_validation["message"], "password"
                    )
            
            # 哈希密码
            hashed_password = self._hash_password(password)
            
            # 创建用户
            user = await self.repos.user.create(
                username=username,
                hashed_password=hashed_password
            )
            
            result_data = {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "created_at": user.created_at.isoformat() if user.created_at else None
                }
            }
            
            return ServiceResult.success_result(
                data=result_data,
                message=f"用户 '{username}' 创建成功"
            )
            
        except Exception as e:
            return await self._handle_service_error("create_user", e)
    
    def _validate_password_strength(self, password: str) -> Dict[str, Any]:
        """验证密码强度"""
        if len(password) < 8:
            return {"valid": False, "message": "密码长度至少8位"}
        
        if len(password) > 128:
            return {"valid": False, "message": "密码长度不能超过128位"}
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        strength_score = sum([has_upper, has_lower, has_digit, has_special])
        
        if strength_score < 3:
            return {
                "valid": False,
                "message": "密码必须包含大写字母、小写字母、数字和特殊字符中的至少3种"
            }
        
        return {"valid": True, "strength_score": strength_score}
    
    def _hash_password(self, password: str) -> str:
        """哈希密码"""
        # 使用SHA-256 + salt（简单实现，生产环境建议使用bcrypt）
        salt = secrets.token_hex(16)
        hashed = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{hashed}"
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """验证密码"""
        try:
            salt, stored_hash = hashed_password.split(':', 1)
            computed_hash = hashlib.sha256((password + salt).encode()).hexdigest()
            return computed_hash == stored_hash
        except ValueError:
            return False
    
    @service_operation("authenticate_user")
    async def authenticate_user(
        self,
        username: str,
        password: str
    ) -> ServiceResult[Dict[str, Any]]:
        """
        用户认证
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            认证结果
        """
        try:
            if not username or not password:
                return ServiceResult.validation_error("用户名和密码不能为空")
            
            # 获取用户
            user = await self.repos.user.get_by_username(username.strip())
            if not user:
                return ServiceResult.validation_error("用户名或密码错误")
            
            # 验证密码
            if not self._verify_password(password, user.hashed_password):
                return ServiceResult.validation_error("用户名或密码错误")
            
            # 获取用户详细信息
            user_with_auth = await self.repos.user.get_with_auth_info(user.id)
            
            result_data = {
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "has_bangumi_auth": bool(user_with_auth.bangumi_auth) if user_with_auth else False
                },
                "authenticated_at": datetime.utcnow().isoformat()
            }
            
            return ServiceResult.success_result(
                data=result_data,
                message="认证成功"
            )
            
        except Exception as e:
            return await self._handle_service_error("authenticate_user", e)
    
    @service_operation("update_user_password")
    async def update_user_password(
        self,
        user_id: int,
        old_password: str,
        new_password: str,
        validate_strength: bool = True
    ) -> ServiceResult[Dict[str, Any]]:
        """
        更新用户密码
        
        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码
            validate_strength: 是否验证密码强度
            
        Returns:
            更新结果
        """
        try:
            # 获取用户
            user = await self._check_resource_exists(
                user_id, "User", self.repos.user.get_by_id
            )
            
            # 验证旧密码
            if not self._verify_password(old_password, user.hashed_password):
                return ServiceResult.validation_error("旧密码不正确", "old_password")
            
            # 验证新密码
            if validate_strength:
                password_validation = self._validate_password_strength(new_password)
                if not password_validation["valid"]:
                    return ServiceResult.validation_error(
                        password_validation["message"], "new_password"
                    )
            
            # 检查新密码是否与旧密码相同
            if self._verify_password(new_password, user.hashed_password):
                return ServiceResult.validation_error(
                    "新密码不能与旧密码相同", "new_password"
                )
            
            # 更新密码
            hashed_password = self._hash_password(new_password)
            await self.repos.user.update(user_id, hashed_password=hashed_password)
            
            result_data = {
                "user_id": user_id,
                "username": user.username,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            return ServiceResult.success_result(
                data=result_data,
                message="密码更新成功"
            )
            
        except Exception as e:
            return await self._handle_service_error("update_user_password", e)
    
    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """用户服务健康检查"""
        try:
            count = await self.repos.user.count()
            active_users = await self.repos.user.get_users_with_active_tokens()
            
            health_data = {
                "service": "UserService",
                "status": "healthy",
                "total_users": count,
                "active_users": len(active_users),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return ServiceResult.success_result(health_data)
            
        except Exception as e:
            return await self._handle_service_error("user_service_health_check", e)


class AuthService(BaseService):
    """认证业务服务"""
    
    def __init__(self, repository_factory: RepositoryFactory, jwt_secret: str = None):
        super().__init__(repository_factory)
        self.jwt_secret = jwt_secret or "default_secret_change_in_production"
        self.metrics = None
    
    @service_operation("create_api_token")
    async def create_api_token(
        self,
        name: str,
        expires_days: Optional[int] = None,
        user_context: Optional[AuthContext] = None
    ) -> ServiceResult[Dict[str, Any]]:
        """
        创建API令牌
        
        Args:
            name: 令牌名称
            expires_days: 过期天数（None表示永不过期）
            user_context: 用户上下文（用于权限检查）
            
        Returns:
            创建结果
        """
        try:
            # 验证令牌名称
            if not name or not name.strip():
                return ServiceResult.validation_error("令牌名称不能为空", "name")
            
            self._validate_field_length(name, "name", 100, 1)
            
            # 计算过期时间
            expires_at = None
            if expires_days and expires_days > 0:
                expires_at = datetime.utcnow() + timedelta(days=expires_days)
            
            # 生成令牌
            token_string = secrets.token_urlsafe(32)
            
            # 创建令牌记录
            api_token = await self.repos.api_token.create(
                name=name.strip(),
                token=token_string,
                is_enabled=True,
                expires_at=expires_at
            )
            
            result_data = {
                "token": {
                    "id": api_token.id,
                    "name": api_token.name,
                    "token": api_token.token,
                    "created_at": api_token.created_at.isoformat() if api_token.created_at else None,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                    "is_enabled": api_token.is_enabled
                }
            }
            
            return ServiceResult.success_result(
                data=result_data,
                message=f"API令牌 '{name}' 创建成功"
            )
            
        except Exception as e:
            return await self._handle_service_error("create_api_token", e)
    
    @service_operation("validate_api_token")
    async def validate_api_token(
        self,
        token: str,
        log_access: bool = True
    ) -> ServiceResult[AuthContext]:
        """
        验证API令牌
        
        Args:
            token: 令牌字符串
            log_access: 是否记录访问日志
            
        Returns:
            认证上下文
        """
        try:
            if not token:
                return ServiceResult.validation_error("令牌不能为空", "token")
            
            # 验证令牌
            api_token = await self.repos.api_token.validate_token(token)
            if not api_token:
                return ServiceResult.validation_error("无效的令牌", "token")
            
            # 记录访问日志
            if log_access:
                await self.repos.token_access_log.log_access(
                    token_id=api_token.id,
                    ip_address="0.0.0.0",  # 需要从请求中获取
                    status="success"
                )
            
            # 创建认证上下文
            auth_context = AuthContext(
                user_id=0,  # API令牌通常不关联用户
                username=api_token.name,
                token_type="api_token",
                permissions=["api_access"],  # 基础API权限
                expires_at=api_token.expires_at
            )
            
            return ServiceResult.success_result(auth_context)
            
        except Exception as e:
            return await self._handle_service_error("validate_api_token", e)
    
    @service_operation("create_jwt_token") 
    async def create_jwt_token(
        self,
        user_id: int,
        expires_hours: int = 24
    ) -> ServiceResult[Dict[str, Any]]:
        """
        创建JWT令牌
        
        Args:
            user_id: 用户ID
            expires_hours: 过期小时数
            
        Returns:
            JWT令牌
        """
        try:
            # 检查用户是否存在
            user = await self._check_resource_exists(
                user_id, "User", self.repos.user.get_by_id
            )
            
            # 创建JWT载荷
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
            payload = {
                "user_id": user.id,
                "username": user.username,
                "iat": datetime.utcnow().timestamp(),
                "exp": expires_at.timestamp(),
                "type": "access_token"
            }
            
            # 生成JWT
            jwt_token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
            
            # 更新用户令牌记录
            await self.repos.user.update_token(user.id, jwt_token)
            
            result_data = {
                "token": jwt_token,
                "token_type": "Bearer",
                "expires_at": expires_at.isoformat(),
                "expires_in": expires_hours * 3600,
                "user": {
                    "id": user.id,
                    "username": user.username
                }
            }
            
            return ServiceResult.success_result(
                data=result_data,
                message="JWT令牌创建成功"
            )
            
        except Exception as e:
            return await self._handle_service_error("create_jwt_token", e)
    
    @service_operation("validate_jwt_token")
    async def validate_jwt_token(self, token: str) -> ServiceResult[AuthContext]:
        """
        验证JWT令牌
        
        Args:
            token: JWT令牌
            
        Returns:
            认证上下文
        """
        try:
            if not token:
                return ServiceResult.validation_error("令牌不能为空", "token")
            
            # 解析JWT
            try:
                payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            except jwt.ExpiredSignatureError:
                return ServiceResult.validation_error("令牌已过期", "token")
            except jwt.InvalidTokenError:
                return ServiceResult.validation_error("无效的令牌", "token")
            
            # 检查用户是否存在
            user_id = payload.get("user_id")
            user = await self.repos.user.get_by_id(user_id)
            if not user:
                return ServiceResult.validation_error("用户不存在", "token")
            
            # 创建认证上下文
            auth_context = AuthContext(
                user_id=user.id,
                username=user.username,
                token_type="jwt",
                permissions=["user_access", "api_access"],  # 用户权限
                expires_at=datetime.fromtimestamp(payload.get("exp", 0))
            )
            
            return ServiceResult.success_result(auth_context)
            
        except Exception as e:
            return await self._handle_service_error("validate_jwt_token", e)
    
    @service_operation("revoke_token")
    async def revoke_token(
        self,
        token_id: int,
        token_type: str = "api_token"
    ) -> ServiceResult[Dict[str, Any]]:
        """
        撤销令牌
        
        Args:
            token_id: 令牌ID
            token_type: 令牌类型
            
        Returns:
            撤销结果
        """
        try:
            if token_type == "api_token":
                # 撤销API令牌
                result = await self.repos.api_token.update(
                    token_id, is_enabled=False
                )
                if not result:
                    return ServiceResult.not_found_error("APIToken", token_id)
                
                result_data = {
                    "token_id": token_id,
                    "token_type": token_type,
                    "revoked_at": datetime.utcnow().isoformat()
                }
                
                return ServiceResult.success_result(
                    data=result_data,
                    message="令牌撤销成功"
                )
            else:
                return ServiceResult.validation_error(
                    f"不支持的令牌类型: {token_type}", "token_type"
                )
                
        except Exception as e:
            return await self._handle_service_error("revoke_token", e)
    
    @service_operation("get_token_access_logs")
    async def get_token_access_logs(
        self,
        token_id: int,
        limit: int = 100
    ) -> ServiceResult[List[Dict[str, Any]]]:
        """
        获取令牌访问日志
        
        Args:
            token_id: 令牌ID
            limit: 返回数量限制
            
        Returns:
            访问日志列表
        """
        try:
            # 检查令牌是否存在
            token = await self._check_resource_exists(
                token_id, "APIToken", self.repos.api_token.get_by_id
            )
            
            # 获取访问日志
            logs = await self.repos.token_access_log.get_logs_by_token(token_id, limit)
            
            logs_data = [
                {
                    "id": log.id,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "access_time": log.access_time.isoformat() if log.access_time else None,
                    "status": log.status,
                    "path": log.path
                }
                for log in logs
            ]
            
            result_data = {
                "token": {
                    "id": token.id,
                    "name": token.name
                },
                "logs": logs_data,
                "total_logs": len(logs_data)
            }
            
            return ServiceResult.success_result(result_data)
            
        except Exception as e:
            return await self._handle_service_error("get_token_access_logs", e)
    
    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """认证服务健康检查"""
        try:
            active_tokens = await self.repos.api_token.get_active_tokens()
            expired_tokens = await self.repos.api_token.get_expired_tokens()
            
            health_data = {
                "service": "AuthService",
                "status": "healthy",
                "active_tokens": len(active_tokens),
                "expired_tokens": len(expired_tokens),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return ServiceResult.success_result(health_data)
            
        except Exception as e:
            return await self._handle_service_error("auth_service_health_check", e)