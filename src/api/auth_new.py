"""
认证API路由 - 新ORM架构适配版本

将现有的认证API适配到新的服务层架构
"""

import logging
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from ..dependencies import (
    get_auth_service,
    get_user_service,
    get_current_user,
    with_service_error_handling
)
from ..services.user import AuthService, UserService, AuthContext
from ..services.base import ServiceError, ValidationError

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic模型定义
class UserCreate(BaseModel):
    """用户创建请求"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=8, max_length=128, description="密码")
    

class UserLogin(BaseModel):
    """用户登录请求"""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class TokenResponse(BaseModel):
    """令牌响应"""
    access_token: str
    token_type: str
    expires_in: int
    user: dict


class UserProfile(BaseModel):
    """用户资料响应"""
    id: int
    username: str
    created_at: str
    has_bangumi_auth: bool


class PasswordChange(BaseModel):
    """密码修改请求"""
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")


class APITokenCreate(BaseModel):
    """API令牌创建请求"""
    name: str = Field(..., min_length=1, max_length=100, description="令牌名称")
    expires_days: Optional[int] = Field(None, ge=1, le=365, description="过期天数")


class APITokenResponse(BaseModel):
    """API令牌响应"""
    token: dict
    message: str


# 用户注册
@router.post("/register", response_model=dict)
@with_service_error_handling
async def register_user(
    user_data: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    用户注册
    
    适配说明：
    - 使用新的UserService.create_user方法
    - 统一的数据验证和错误处理
    """
    try:
        result = await user_service.create_user(
            username=user_data.username,
            password=user_data.password,
            validate_strength=True
        )
        
        if not result.success:
            if result.error.error_code == "VALIDATION_ERROR":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.error.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.error.message
                )
        
        return {
            "message": result.message,
            "user": result.data["user"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户注册失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册服务器错误"
        )


# 用户登录
@router.post("/login", response_model=TokenResponse)
@with_service_error_handling
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    用户登录
    
    适配说明：
    - 使用OAuth2PasswordRequestForm标准表单
    - 集成UserService认证和AuthService令牌生成
    """
    try:
        # 验证用户凭据
        auth_result = await user_service.authenticate_user(
            username=form_data.username,
            password=form_data.password
        )
        
        if not auth_result.success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # 生成JWT令牌
        user_data = auth_result.data["user"]
        token_result = await auth_service.create_jwt_token(
            user_id=user_data["id"],
            expires_hours=24
        )
        
        if not token_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="令牌生成失败"
            )
        
        return TokenResponse(
            access_token=token_result.data["token"],
            token_type=token_result.data["token_type"],
            expires_in=token_result.data["expires_in"],
            user=token_result.data["user"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录服务器错误"
        )


# 简化的登录端点（兼容性）
@router.post("/login-simple")
@with_service_error_handling
async def login_simple(
    login_data: UserLogin,
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    简化的登录端点
    
    为了保持与现有前端的兼容性
    """
    try:
        # 验证用户凭据
        auth_result = await user_service.authenticate_user(
            username=login_data.username,
            password=login_data.password
        )
        
        if not auth_result.success:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误"
            )
        
        # 生成JWT令牌
        user_data = auth_result.data["user"]
        token_result = await auth_service.create_jwt_token(
            user_id=user_data["id"],
            expires_hours=24
        )
        
        if not token_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="令牌生成失败"
            )
        
        return {
            "access_token": token_result.data["token"],
            "token_type": token_result.data["token_type"],
            "expires_at": token_result.data["expires_at"],
            "user": token_result.data["user"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"简化登录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录服务器错误"
        )


# 获取当前用户信息
@router.get("/me", response_model=UserProfile)
@with_service_error_handling
async def get_current_user_profile(
    current_user: AuthContext = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    获取当前用户资料
    
    适配说明：
    - 使用新的认证上下文
    - 可以扩展获取更多用户信息
    """
    try:
        # 从认证上下文构造用户资料
        return UserProfile(
            id=current_user.user_id,
            username=current_user.username,
            created_at=datetime.utcnow().isoformat(),  # 这里应该从数据库获取实际创建时间
            has_bangumi_auth=False  # 这里应该检查是否有Bangumi认证
        )
        
    except Exception as e:
        logger.error(f"获取用户资料失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户资料失败"
        )


# 修改密码
@router.put("/password")
@with_service_error_handling
async def change_password(
    password_data: PasswordChange,
    current_user: AuthContext = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    修改密码
    
    适配说明：
    - 使用新的UserService.update_user_password方法
    - 自动验证旧密码和新密码强度
    """
    try:
        result = await user_service.update_user_password(
            user_id=current_user.user_id,
            old_password=password_data.old_password,
            new_password=password_data.new_password,
            validate_strength=True
        )
        
        if not result.success:
            if result.error.error_code == "VALIDATION_ERROR":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.error.message
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.error.message
                )
        
        return {
            "message": result.message,
            "updated_at": result.data["updated_at"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"修改密码失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="修改密码失败"
        )


# API令牌管理
@router.post("/tokens", response_model=APITokenResponse)
@with_service_error_handling
async def create_api_token(
    token_data: APITokenCreate,
    current_user: AuthContext = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    创建API令牌
    
    适配说明：
    - 使用新的AuthService.create_api_token方法
    - 支持自定义过期时间
    """
    try:
        result = await auth_service.create_api_token(
            name=token_data.name,
            expires_days=token_data.expires_days,
            user_context=current_user
        )
        
        if not result.success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.error.message
            )
        
        return APITokenResponse(
            token=result.data["token"],
            message=result.message
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建API令牌失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建API令牌失败"
        )


@router.get("/tokens")
@with_service_error_handling
async def list_api_tokens(
    current_user: AuthContext = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    获取API令牌列表
    
    注意：这里需要扩展AuthService以支持获取用户的令牌列表
    """
    # 暂时返回模拟数据
    return {
        "message": "API令牌列表功能需要进一步实现",
        "user_id": current_user.user_id
    }


@router.delete("/tokens/{token_id}")
@with_service_error_handling
async def revoke_api_token(
    token_id: int,
    current_user: AuthContext = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    撤销API令牌
    
    适配说明：
    - 使用新的AuthService.revoke_token方法
    """
    try:
        result = await auth_service.revoke_token(
            token_id=token_id,
            token_type="api_token"
        )
        
        if not result.success:
            if result.error.error_code == "RESOURCE_NOT_FOUND":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="令牌不存在"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.error.message
                )
        
        return {"message": result.message}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"撤销API令牌失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="撤销API令牌失败"
        )


# 令牌验证端点（用于测试）
@router.get("/verify")
@with_service_error_handling
async def verify_token(
    current_user: AuthContext = Depends(get_current_user)
):
    """
    验证令牌有效性
    
    适配说明：
    - 使用新的认证上下文验证
    """
    return {
        "valid": True,
        "user_id": current_user.user_id,
        "username": current_user.username,
        "token_type": current_user.token_type,
        "permissions": current_user.permissions,
        "expires_at": current_user.expires_at.isoformat() if current_user.expires_at else None
    }


# 登出端点（主要是前端清除令牌）
@router.post("/logout")
@with_service_error_handling
async def logout_user(
    current_user: AuthContext = Depends(get_current_user)
):
    """
    用户登出
    
    注意：JWT令牌是无状态的，主要靠前端清除令牌
    未来可以考虑实现令牌黑名单机制
    """
    return {
        "message": "登出成功",
        "user_id": current_user.user_id
    }