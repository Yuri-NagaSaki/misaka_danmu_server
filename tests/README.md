# 测试运行脚本

## 运行所有测试
```bash
# 使用pytest运行所有测试
cd tests && python -m pytest

# 运行特定类型的测试
python -m pytest tests/unit/          # 单元测试
python -m pytest tests/integration/   # 集成测试
python -m pytest tests/phase/         # 阶段测试
```

## 运行集成测试
```bash
# 直接运行集成测试
cd tests/integration && python integration_test.py

# 或使用scripts中的部署脚本
cd scripts && python deploy.py --test-only
```

## 运行阶段测试
```bash
# 运行特定阶段测试
python tests/phase/test_phase1.py
python tests/phase/test_phase2.py
# ... 等等
```