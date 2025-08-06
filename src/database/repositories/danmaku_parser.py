"""
弹幕参数解析工具

提供弹幕参数的解析功能，包括数据库视图创建和Python解析工具。
"""

from typing import Dict, Any, List, Tuple, Optional
from sqlalchemy import text, select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession


class DanmakuParamsParser:
    """弹幕参数解析器"""
    
    @staticmethod
    def parse_params_string(params: str) -> Dict[str, Any]:
        """
        解析弹幕参数字符串
        
        Args:
            params: 参数字符串，格式为 "时间,模式,字号,颜色,用户ID,弹幕池,弹幕ID,用户哈希"
            
        Returns:
            解析后的参数字典
        """
        try:
            parts = params.split(',')
            if len(parts) >= 8:
                return {
                    'time': float(parts[0]),
                    'mode': int(parts[1]),  # 1-从右至左滚动 4-底端固定 5-顶端固定 6-逆向 7-精确定位
                    'font_size': int(parts[2]), # 字号 (12-小 18-标准 25-大)
                    'color': int(parts[3]), # 颜色 (十六进制)
                    'timestamp': int(parts[4]), # 发送时间戳
                    'pool': int(parts[5]), # 弹幕池 (0-普通 1-字幕 2-特殊)
                    'danmaku_id': parts[6], # 弹幕ID
                    'user_hash': parts[7] if len(parts) > 7 else '', # 用户哈希
                }
        except (ValueError, IndexError):
            pass
        
        return {}
    
    @staticmethod
    def get_mode_name(mode: int) -> str:
        """获取弹幕模式名称"""
        mode_names = {
            1: "从右至左滚动",
            4: "底端固定", 
            5: "顶端固定",
            6: "逆向滚动",
            7: "精确定位",
            8: "高级弹幕"
        }
        return mode_names.get(mode, f"未知模式({mode})")
    
    @staticmethod
    def get_color_hex(color: int) -> str:
        """将颜色整数转换为十六进制字符串"""
        return f"#{color:06X}"
    
    @staticmethod
    def get_font_size_name(size: int) -> str:
        """获取字号名称"""
        size_names = {
            12: "小",
            18: "标准", 
            25: "大"
        }
        return size_names.get(size, f"自定义({size})")


async def create_comment_params_view(session: AsyncSession, database_type: str = "mysql"):
    """
    创建弹幕参数视图
    
    Args:
        session: 数据库会话
        database_type: 数据库类型 (mysql, postgresql, sqlite)
    """
    
    if database_type == "mysql":
        # MySQL版本 - 使用SUBSTRING_INDEX函数
        create_view_sql = """
        CREATE OR REPLACE VIEW comment_params_view AS
        SELECT 
            id,
            episode_id,
            cid,
            t as time_offset,
            m as content,
            p as params_raw,
            CAST(SUBSTRING_INDEX(p, ',', 1) AS DECIMAL(10,2)) as param_time,
            CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(p, ',', 2), ',', -1) AS SIGNED) as mode,
            CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(p, ',', 3), ',', -1) AS SIGNED) as font_size,
            CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(p, ',', 4), ',', -1) AS SIGNED) as color,
            CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(p, ',', 5), ',', -1) AS SIGNED) as timestamp,
            CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(p, ',', 6), ',', -1) AS SIGNED) as pool,
            SUBSTRING_INDEX(SUBSTRING_INDEX(p, ',', 7), ',', -1) as danmaku_id,
            SUBSTRING_INDEX(p, ',', -1) as user_hash
        FROM comment
        WHERE p REGEXP '^[0-9.]+,[0-9]+,[0-9]+,[0-9]+,[0-9]+,[0-9]+,.+,.+'
        """
        
    elif database_type == "postgresql":
        # PostgreSQL版本 - 使用SPLIT_PART函数
        create_view_sql = """
        CREATE OR REPLACE VIEW comment_params_view AS
        SELECT 
            id,
            episode_id,
            cid,
            t as time_offset,
            m as content,
            p as params_raw,
            CAST(SPLIT_PART(p, ',', 1) AS DECIMAL(10,2)) as param_time,
            CAST(SPLIT_PART(p, ',', 2) AS INTEGER) as mode,
            CAST(SPLIT_PART(p, ',', 3) AS INTEGER) as font_size,
            CAST(SPLIT_PART(p, ',', 4) AS INTEGER) as color,
            CAST(SPLIT_PART(p, ',', 5) AS INTEGER) as timestamp,
            CAST(SPLIT_PART(p, ',', 6) AS INTEGER) as pool,
            SPLIT_PART(p, ',', 7) as danmaku_id,
            SPLIT_PART(p, ',', 8) as user_hash
        FROM comment
        WHERE p ~ '^[0-9.]+,[0-9]+,[0-9]+,[0-9]+,[0-9]+,[0-9]+,.+,.+'
        """
        
    else:  # SQLite
        # SQLite版本 - 使用JSON扩展或自定义函数
        create_view_sql = """
        CREATE VIEW IF NOT EXISTS comment_params_view AS
        SELECT 
            id,
            episode_id,
            cid,
            t as time_offset,
            m as content,
            p as params_raw,
            CAST(substr(p, 1, instr(p, ',') - 1) AS REAL) as param_time,
            -- 为简化SQLite实现，这里只提取前几个参数
            -- 完整的参数解析建议在应用层进行
            NULL as mode,
            NULL as font_size, 
            NULL as color,
            NULL as timestamp,
            NULL as pool,
            NULL as danmaku_id,
            NULL as user_hash
        FROM comment
        WHERE p LIKE '%,%,%,%,%,%,%,%'
        """
    
    try:
        await session.execute(text(create_view_sql))
        await session.commit()
        print(f"✅ 成功创建弹幕参数视图 (database_type: {database_type})")
    except Exception as e:
        await session.rollback()
        print(f"❌ 创建弹幕参数视图失败: {e}")
        raise


async def drop_comment_params_view(session: AsyncSession):
    """删除弹幕参数视图"""
    try:
        await session.execute(text("DROP VIEW IF EXISTS comment_params_view"))
        await session.commit()
        print("✅ 成功删除弹幕参数视图")
    except Exception as e:
        await session.rollback()
        print(f"❌ 删除弹幕参数视图失败: {e}")
        raise


class EnhancedCommentStatistics:
    """增强的弹幕统计功能"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.parser = DanmakuParamsParser()
    
    async def get_color_distribution_via_view(self, episode_id: int) -> Dict[str, int]:
        """通过视图获取颜色分布统计"""
        stmt = text("""
            SELECT color, COUNT(*) as count
            FROM comment_params_view 
            WHERE episode_id = :episode_id AND color IS NOT NULL
            GROUP BY color 
            ORDER BY count DESC
            LIMIT 20
        """)
        
        result = await self.session.execute(stmt, {"episode_id": episode_id})
        
        color_dist = {}
        for color_int, count in result.all():
            color_hex = self.parser.get_color_hex(color_int)
            color_dist[color_hex] = count
            
        return color_dist
    
    async def get_mode_distribution_via_view(self, episode_id: int) -> Dict[str, int]:
        """通过视图获取模式分布统计"""
        stmt = text("""
            SELECT mode, COUNT(*) as count
            FROM comment_params_view 
            WHERE episode_id = :episode_id AND mode IS NOT NULL
            GROUP BY mode 
            ORDER BY count DESC
        """)
        
        result = await self.session.execute(stmt, {"episode_id": episode_id})
        
        mode_dist = {}
        for mode_int, count in result.all():
            mode_name = self.parser.get_mode_name(mode_int)
            mode_dist[mode_name] = count
            
        return mode_dist
    
    async def get_font_size_distribution_via_view(self, episode_id: int) -> Dict[str, int]:
        """通过视图获取字号分布统计"""
        stmt = text("""
            SELECT font_size, COUNT(*) as count
            FROM comment_params_view 
            WHERE episode_id = :episode_id AND font_size IS NOT NULL
            GROUP BY font_size 
            ORDER BY count DESC
        """)
        
        result = await self.session.execute(stmt, {"episode_id": episode_id})
        
        size_dist = {}
        for size_int, count in result.all():
            size_name = self.parser.get_font_size_name(size_int)
            size_dist[size_name] = count
            
        return size_dist
    
    async def get_color_distribution_via_python(
        self, 
        episode_id: int, 
        limit: int = 1000
    ) -> Dict[str, int]:
        """
        通过Python解析获取颜色分布统计
        
        适用于SQLite或视图不可用的情况
        """
        from ..models.episode import Comment
        
        stmt = select(Comment.p).where(Comment.episode_id == episode_id).limit(limit)
        result = await self.session.execute(stmt)
        
        color_counts = {}
        for (params_str,) in result.all():
            params = self.parser.parse_params_string(params_str)
            if 'color' in params:
                color_hex = self.parser.get_color_hex(params['color'])
                color_counts[color_hex] = color_counts.get(color_hex, 0) + 1
        
        # 按数量排序
        return dict(sorted(color_counts.items(), key=lambda x: x[1], reverse=True))
    
    async def get_mode_distribution_via_python(
        self, 
        episode_id: int, 
        limit: int = 1000
    ) -> Dict[str, int]:
        """通过Python解析获取模式分布统计"""
        from ..models.episode import Comment
        
        stmt = select(Comment.p).where(Comment.episode_id == episode_id).limit(limit)
        result = await self.session.execute(stmt)
        
        mode_counts = {}
        for (params_str,) in result.all():
            params = self.parser.parse_params_string(params_str)
            if 'mode' in params:
                mode_name = self.parser.get_mode_name(params['mode'])
                mode_counts[mode_name] = mode_counts.get(mode_name, 0) + 1
        
        return dict(sorted(mode_counts.items(), key=lambda x: x[1], reverse=True))
    
    async def get_comprehensive_statistics(
        self, 
        episode_id: int,
        use_view: bool = True,
        python_limit: int = 1000
    ) -> Dict[str, Any]:
        """
        获取全面的弹幕统计信息
        
        Args:
            episode_id: 分集ID
            use_view: 是否使用数据库视图（性能更好）
            python_limit: Python解析模式下的限制数量
            
        Returns:
            包含详细统计的字典
        """
        if use_view:
            try:
                # 尝试使用视图进行统计
                color_dist = await self.get_color_distribution_via_view(episode_id)
                mode_dist = await self.get_mode_distribution_via_view(episode_id)
                size_dist = await self.get_font_size_distribution_via_view(episode_id)
                
                return {
                    "method": "database_view",
                    "color_distribution": color_dist,
                    "mode_distribution": mode_dist,
                    "font_size_distribution": size_dist
                }
            except Exception as e:
                print(f"视图统计失败，回退到Python解析: {e}")
        
        # 回退到Python解析
        color_dist = await self.get_color_distribution_via_python(episode_id, python_limit)
        mode_dist = await self.get_mode_distribution_via_python(episode_id, python_limit)
        
        # 字号统计（Python版）
        from ..models.episode import Comment
        stmt = select(Comment.p).where(Comment.episode_id == episode_id).limit(python_limit)
        result = await self.session.execute(stmt)
        
        size_counts = {}
        for (params_str,) in result.all():
            params = self.parser.parse_params_string(params_str)
            if 'font_size' in params:
                size_name = self.parser.get_font_size_name(params['font_size'])
                size_counts[size_name] = size_counts.get(size_name, 0) + 1
        
        return {
            "method": "python_parsing",
            "sample_limit": python_limit,
            "color_distribution": color_dist,
            "mode_distribution": mode_dist, 
            "font_size_distribution": dict(sorted(size_counts.items(), key=lambda x: x[1], reverse=True))
        }