# 项目组织结构说明

## 目录结构

```
misaka_danmu_server/
├── src/                    # 源代码
│   ├── api/               # API路由
│   ├── database/          # 数据库相关
│   ├── services/          # 业务服务层
│   └── ...
├── tests/                 # 测试文件
│   ├── unit/             # 单元测试
│   ├── integration/      # 集成测试
│   └── phase/           # 阶段性测试
├── scripts/              # 部署和工具脚本
├── docs/                # 项目文档
├── alembic/            # 数据库迁移文件
└── ...
```

## 文件说明

### 测试文件
- `tests/phase/`: 包含各阶段开发测试 (test_phase1.py - test_phase6.py)
- `tests/integration/`: 包含完整系统集成测试 (integration_test.py)
- `tests/unit/`: 预留单元测试目录

### 脚本文件  
- `scripts/deploy.py`: 自动化部署脚本
- `scripts/start_dev.sh`: 开发环境启动脚本
- `scripts/start_prod.sh`: 生产环境启动脚本
- `scripts/start.bat`: Windows启动脚本
- `scripts/.env.template`: 环境变量模板

### 文档文件
- `docs/`: 项目相关文档存放目录