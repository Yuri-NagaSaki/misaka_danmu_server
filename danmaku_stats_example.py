"""
弹幕增强统计功能使用示例

展示如何使用新的弹幕参数解析和统计功能。
"""

import asyncio
from typing import Dict, Any


async def example_usage():
    """使用示例"""
    
    # 假设你有一个数据库会话和Repository工厂
    # from your_app.database import get_session
    # from your_app.repositories import get_repository_factory
    
    print("🎯 弹幕增强统计功能使用示例")
    print("=" * 50)
    
    # 1. 首先创建数据库视图（推荐在应用启动时执行一次）
    print("\n📋 步骤1: 创建数据库视图")
    print("""
    from src.database.repositories.danmaku_parser import create_comment_params_view
    
    # 在应用启动时创建视图
    async with get_session() as session:
        await create_comment_params_view(session, database_type="mysql")  # 或 postgresql, sqlite
    """)
    
    # 2. 使用增强的CommentRepository
    print("\n🔍 步骤2: 使用增强统计功能")
    print("""
    async def analyze_episode_danmaku(episode_id: int):
        async with get_repository_factory() as repos:
            # 获取完整统计信息
            stats = await repos.comment.get_danmaku_statistics(
                episode_id=episode_id,
                use_enhanced=True,  # 启用增强统计
                use_view=True       # 使用数据库视图（性能更好）
            )
            
            print(f"分集 {episode_id} 弹幕统计:")
            print(f"  总弹幕数: {stats['total_count']}")
            print(f"  平均时间偏移: {stats['average_time_offset']}秒")
            print(f"  统计方法: {stats['statistics_method']}")
            
            # 颜色分布
            colors = stats['color_distribution']
            print("\\n  颜色分布:")
            for color, count in list(colors.items())[:5]:  # Top 5
                print(f"    {color}: {count}条弹幕")
            
            # 模式分布
            modes = stats['mode_distribution']
            print("\\n  模式分布:")
            for mode, count in modes.items():
                print(f"    {mode}: {count}条弹幕")
    """)
    
    # 3. 快捷统计方法
    print("\n⚡ 步骤3: 使用快捷统计方法")
    print("""
    async def get_specific_distributions(episode_id: int):
        async with get_repository_factory() as repos:
            # 只获取颜色分布
            colors = await repos.comment.get_danmaku_color_distribution(
                episode_id, use_view=True
            )
            
            # 只获取模式分布
            modes = await repos.comment.get_danmaku_mode_distribution(
                episode_id, use_view=True
            )
            
            return colors, modes
    """)
    
    # 4. 解析弹幕数据
    print("\n📊 步骤4: 获取解析后的弹幕数据")
    print("""
    async def get_parsed_comments(episode_id: int):
        async with get_repository_factory() as repos:
            # 获取解析后的弹幕（包含所有参数）
            parsed_danmaku = await repos.comment.get_parsed_danmaku(
                episode_id, limit=100
            )
            
            for danmaku in parsed_danmaku[:3]:  # 显示前3条
                print(f"弹幕ID: {danmaku['id']}")
                print(f"  内容: {danmaku['content']}")
                print(f"  时间: {danmaku['time_offset']}秒")
                print(f"  颜色: #{danmaku['color']:06X}")
                print(f"  模式: {danmaku['mode']}")
                print(f"  用户: {danmaku['user_hash']}")
                print()
    """)
    
    # 5. Python解析备用方案
    print("\n🔄 步骤5: Python解析备用方案（SQLite或视图不可用）")
    print("""
    async def fallback_statistics(episode_id: int):
        async with get_repository_factory() as repos:
            # 关闭视图，使用Python解析
            stats = await repos.comment.get_danmaku_statistics(
                episode_id=episode_id,
                use_enhanced=True,
                use_view=False  # 使用Python解析
            )
            
            # 这种方式会有样本限制，但适用于所有数据库
            if 'sample_limit' in stats:
                print(f"注意: 使用样本解析，限制{stats['sample_limit']}条弹幕")
    """)
    
    # 6. 手动解析器使用
    print("\n🛠️ 步骤6: 直接使用解析器")
    print("""
    from src.database.repositories.danmaku_parser import DanmakuParamsParser
    
    parser = DanmakuParamsParser()
    
    # 解析单条弹幕参数
    params_str = "23.5,1,25,16777215,1609459200,0,test_id,user_hash_123"
    params = parser.parse_params_string(params_str)
    
    print(f"解析结果: {params}")
    print(f"颜色名称: {parser.get_color_hex(params['color'])}")
    print(f"模式名称: {parser.get_mode_name(params['mode'])}")
    print(f"字号名称: {parser.get_font_size_name(params['font_size'])}")
    """)
    
    # 7. 性能对比
    print("\n⚡ 性能对比:")
    print("""
    数据库视图方案:
    ✅ 性能最佳（SQL原生处理）
    ✅ 支持复杂聚合查询
    ✅ 内存使用少
    ❌ 需要数据库支持视图
    
    Python解析方案:
    ✅ 兼容性最好（支持所有数据库）
    ✅ 灵活性高
    ❌ 性能较低（需要传输原始数据）
    ❌ 内存使用较多（受样本限制影响）
    """)
    
    print("\n🎉 示例完成！选择最适合你项目的方案。")


if __name__ == "__main__":
    asyncio.run(example_usage())