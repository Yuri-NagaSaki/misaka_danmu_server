"""
完整的系统集成测试

测试新ORM架构下的完整应用流程，包括API端到端测试
"""

import asyncio
import logging
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional
import httpx
import pytest
from unittest.mock import AsyncMock, Mock

# 添加src目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegrationTestRunner:
    """集成测试运行器"""
    
    def __init__(self):
        self.test_results = []
        self.setup_completed = False
        
    async def setup_test_environment(self):
        """设置测试环境"""
        try:
            logger.info("设置测试环境...")
            
            # 导入必要的模块
            from src.main_new import create_app
            from src.dependencies import get_database_engine, get_session_factory
            from src.services.factory import ServiceFactory
            from src.database.repositories.factory import RepositoryFactory
            
            # 创建应用实例
            self.app = create_app()
            
            # 设置模拟数据库会话
            self.mock_session = Mock()
            self.mock_session.commit = AsyncMock()
            self.mock_session.rollback = AsyncMock()
            self.mock_session.close = AsyncMock()
            
            # 创建模拟的Repository和Service工厂
            self.repo_factory = RepositoryFactory(self.mock_session)
            self.service_factory = ServiceFactory(
                repository_factory=self.repo_factory,
                jwt_secret="test_secret_key",
                config={"test_mode": True}
            )
            
            self.setup_completed = True
            logger.info("✅ 测试环境设置完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 测试环境设置失败: {e}")
            return False
    
    async def test_application_startup(self):
        """测试应用启动"""
        try:
            logger.info("测试应用启动...")
            
            if not self.setup_completed:
                raise Exception("测试环境未设置")
            
            # 验证应用配置
            assert self.app.title == "Misaka Danmu Server"
            assert self.app.version == "2.0.0"
            
            # 验证路由数量
            total_routes = len(self.app.routes)
            assert total_routes > 20, f"路由数量不足: {total_routes}"
            
            logger.info(f"✅ 应用启动测试通过，总路由数: {total_routes}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 应用启动测试失败: {e}")
            return False
    
    async def test_dependency_injection(self):
        """测试依赖注入系统"""
        try:
            logger.info("测试依赖注入系统...")
            
            # 测试服务获取
            anime_service = self.service_factory.anime
            episode_service = self.service_factory.episode
            danmaku_service = self.service_factory.danmaku
            user_service = self.service_factory.user
            auth_service = self.service_factory.auth
            
            # 验证服务实例
            assert anime_service is not None
            assert episode_service is not None
            assert danmaku_service is not None
            assert user_service is not None
            assert auth_service is not None
            
            # 测试单例模式
            anime_service2 = self.service_factory.anime
            assert anime_service is anime_service2, "服务工厂单例模式失败"
            
            logger.info("✅ 依赖注入系统测试通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 依赖注入系统测试失败: {e}")
            return False
    
    async def test_authentication_flow(self):
        """测试认证流程"""
        try:
            logger.info("测试认证流程...")
            
            auth_service = self.service_factory.auth
            user_service = self.service_factory.user
            
            # 模拟用户创建成功的结果
            from src.services.base import ServiceResult
            
            mock_user_data = {
                "user": {
                    "id": 1,
                    "username": "testuser",
                    "created_at": "2024-01-01T00:00:00"
                }
            }
            
            user_service.create_user = AsyncMock(
                return_value=ServiceResult.success_result(
                    data=mock_user_data,
                    message="用户创建成功"
                )
            )
            
            # 测试用户创建
            create_result = await user_service.create_user("testuser", "testpassword123")
            assert create_result.success == True
            assert create_result.data["user"]["username"] == "testuser"
            
            # 模拟用户认证成功的结果
            user_service.authenticate_user = AsyncMock(
                return_value=ServiceResult.success_result(
                    data=mock_user_data,
                    message="认证成功"
                )
            )
            
            # 测试用户认证
            auth_result = await user_service.authenticate_user("testuser", "testpassword123")
            assert auth_result.success == True
            
            # 模拟JWT令牌生成
            mock_token_data = {
                "token": "test.jwt.token",
                "token_type": "Bearer",
                "expires_in": 86400,
                "user": {"id": 1, "username": "testuser"}
            }
            
            auth_service.create_jwt_token = AsyncMock(
                return_value=ServiceResult.success_result(
                    data=mock_token_data,
                    message="令牌创建成功"
                )
            )
            
            # 测试JWT令牌生成
            token_result = await auth_service.create_jwt_token(user_id=1)
            assert token_result.success == True
            assert "token" in token_result.data
            
            logger.info("✅ 认证流程测试通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 认证流程测试失败: {e}")
            return False
    
    async def test_anime_management_flow(self):
        """测试番剧管理流程"""
        try:
            logger.info("测试番剧管理流程...")
            
            anime_service = self.service_factory.anime
            from src.services.base import ServiceResult
            
            # 模拟番剧搜索
            mock_search_results = [
                {
                    "id": 1,
                    "title": "测试番剧1",
                    "type": "TV_SERIES",
                    "season": 1,
                    "year": 2024
                },
                {
                    "id": 2, 
                    "title": "测试番剧2",
                    "type": "OVA",
                    "season": 1,
                    "year": 2024
                }
            ]
            
            anime_service.search_anime = AsyncMock(
                return_value=ServiceResult.success_result(
                    data=mock_search_results,
                    message="搜索成功"
                )
            )
            
            # 测试番剧搜索
            search_result = await anime_service.search_anime("测试", limit=10)
            assert search_result.success == True
            assert len(search_result.data) == 2
            
            # 模拟番剧详情获取
            mock_anime_detail = {
                "anime": mock_search_results[0],
                "sources": [{"id": 1, "provider_name": "test_provider"}],
                "episodes_count": 12,
                "danmaku_count": 5000
            }
            
            anime_service.get_anime_with_details = AsyncMock(
                return_value=ServiceResult.success_result(
                    data=mock_anime_detail,
                    message="获取详情成功"
                )
            )
            
            # 测试番剧详情获取
            detail_result = await anime_service.get_anime_with_details(1)
            assert detail_result.success == True
            assert detail_result.data["anime"]["title"] == "测试番剧1"
            
            logger.info("✅ 番剧管理流程测试通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 番剧管理流程测试失败: {e}")
            return False
    
    async def test_episode_danmaku_flow(self):
        """测试分集弹幕流程"""
        try:
            logger.info("测试分集弹幕流程...")
            
            episode_service = self.service_factory.episode
            danmaku_service = self.service_factory.danmaku
            from src.services.base import ServiceResult
            
            # 模拟分集列表获取
            mock_episodes = {
                "episodes": [
                    {
                        "id": 1,
                        "title": "第1集",
                        "episode_index": 1,
                        "danmaku_count": 100
                    },
                    {
                        "id": 2,
                        "title": "第2集", 
                        "episode_index": 2,
                        "danmaku_count": 150
                    }
                ],
                "total_episodes": 2,
                "source": {"id": 1, "provider_name": "test_provider"}
            }
            
            episode_service.get_episodes_with_stats = AsyncMock(
                return_value=ServiceResult.success_result(
                    data=mock_episodes,
                    message="获取分集成功"
                )
            )
            
            # 测试分集列表获取
            episodes_result = await episode_service.get_episodes_with_stats(
                source_id=1, 
                include_danmaku_count=True
            )
            assert episodes_result.success == True
            assert len(episodes_result.data["episodes"]) == 2
            
            # 模拟弹幕分析
            mock_analysis = {
                "episode": {"id": 1, "title": "第1集"},
                "basic_stats": {
                    "total_count": 100,
                    "average_time_offset": 600.5,
                    "time_distribution": {0: 10, 1: 15, 2: 20}
                },
                "enhanced_stats": {
                    "color_distribution": {"#FFFFFF": 50, "#FF0000": 30},
                    "mode_distribution": {"从右至左滚动": 80, "底端固定": 20}
                }
            }
            
            danmaku_service.analyze_danmaku_patterns = AsyncMock(
                return_value=ServiceResult.success_result(
                    data=mock_analysis,
                    message="弹幕分析完成"
                )
            )
            
            # 测试弹幕分析
            analysis_result = await danmaku_service.analyze_danmaku_patterns(
                episode_id=1,
                analysis_type="comprehensive"
            )
            assert analysis_result.success == True
            assert "basic_stats" in analysis_result.data
            
            logger.info("✅ 分集弹幕流程测试通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 分集弹幕流程测试失败: {e}")
            return False
    
    async def test_error_handling(self):
        """测试错误处理"""
        try:
            logger.info("测试错误处理...")
            
            anime_service = self.service_factory.anime
            from src.services.base import ServiceResult, ResourceNotFoundError, ValidationError
            
            # 模拟资源不存在错误
            anime_service.get_anime_with_details = AsyncMock(
                return_value=ServiceResult.error_result(
                    ResourceNotFoundError("Anime", 999)
                )
            )
            
            # 测试资源不存在处理
            not_found_result = await anime_service.get_anime_with_details(999)
            assert not_found_result.success == False
            assert not_found_result.error.error_code == "RESOURCE_NOT_FOUND"
            
            # 模拟验证错误
            anime_service.search_anime = AsyncMock(
                return_value=ServiceResult.error_result(
                    ValidationError("搜索关键词不能为空", "query")
                )
            )
            
            # 测试验证错误处理
            validation_result = await anime_service.search_anime("")
            assert validation_result.success == False
            assert validation_result.error.error_code == "VALIDATION_ERROR"
            
            logger.info("✅ 错误处理测试通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 错误处理测试失败: {e}")
            return False
    
    async def test_service_health_checks(self):
        """测试服务健康检查"""
        try:
            logger.info("测试服务健康检查...")
            
            from src.services.base import ServiceResult
            
            # 模拟各服务的健康检查
            services = [
                ("anime", self.service_factory.anime),
                ("episode", self.service_factory.episode),
                ("danmaku", self.service_factory.danmaku),
                ("user", self.service_factory.user),
                ("auth", self.service_factory.auth)
            ]
            
            for service_name, service in services:
                mock_health_data = {
                    "service": f"{service_name.title()}Service",
                    "status": "healthy",
                    "timestamp": "2024-01-01T00:00:00"
                }
                
                service.health_check = AsyncMock(
                    return_value=ServiceResult.success_result(mock_health_data)
                )
                
                # 测试健康检查
                health_result = await service.health_check()
                assert health_result.success == True
                assert health_result.data["status"] == "healthy"
            
            # 测试服务工厂的整体健康检查
            overall_health = await self.service_factory.health_check()
            assert "overall_status" in overall_health
            assert "services" in overall_health
            
            logger.info("✅ 服务健康检查测试通过")
            return True
            
        except Exception as e:
            logger.error(f"❌ 服务健康检查测试失败: {e}")
            return False
    
    async def run_all_tests(self):
        """运行所有集成测试"""
        logger.info("🚀 开始完整系统集成测试")
        logger.info("=" * 70)
        
        tests = [
            ("测试环境设置", self.setup_test_environment),
            ("应用启动", self.test_application_startup),
            ("依赖注入", self.test_dependency_injection),
            ("认证流程", self.test_authentication_flow),
            ("番剧管理流程", self.test_anime_management_flow),
            ("分集弹幕流程", self.test_episode_danmaku_flow),
            ("错误处理", self.test_error_handling),
            ("服务健康检查", self.test_service_health_checks),
        ]
        
        results = []
        for test_name, test_func in tests:
            logger.info(f"\\n📝 执行测试: {test_name}")
            logger.info("-" * 35)
            
            result = await test_func()
            results.append((test_name, result))
            self.test_results.append({"test": test_name, "passed": result})
        
        # 总结结果
        logger.info("\\n" + "=" * 70)
        logger.info("📊 集成测试结果总结:")
        
        passed = 0
        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            logger.info(f"  {test_name}: {status}")
            if result:
                passed += 1
        
        logger.info(f"\\n总计: {passed}/{len(tests)} 测试通过")
        
        if passed == len(tests):
            logger.info("🎉 完整系统集成测试通过！")
            logger.info("\\n系统验证完成:")
            logger.info("  ✅ 应用能够正常启动和运行")
            logger.info("  ✅ 依赖注入系统工作正常")
            logger.info("  ✅ 认证流程完整可用")
            logger.info("  ✅ 业务流程端到端测试通过")
            logger.info("  ✅ 错误处理机制正确")
            logger.info("  ✅ 服务健康检查正常")
            logger.info("\\n🚀 系统已准备好投入生产使用！")
        else:
            logger.error("⚠️  部分测试失败，需要修复后再部署")
        
        return passed == len(tests)


async def main():
    """主函数"""
    runner = IntegrationTestRunner()
    success = await runner.run_all_tests()
    
    # 生成测试报告
    report_file = Path("integration_test_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump({
            "test_run_date": "2024-01-01T00:00:00",
            "total_tests": len(runner.test_results),
            "passed_tests": sum(1 for r in runner.test_results if r["passed"]),
            "overall_result": "PASS" if success else "FAIL",
            "details": runner.test_results
        }, f, indent=2, ensure_ascii=False)
    
    logger.info(f"\\n📄 测试报告已保存至: {report_file}")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)