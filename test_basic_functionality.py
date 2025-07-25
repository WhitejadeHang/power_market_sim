#!/usr/bin/env python3
"""
基本功能测试脚本
用于验证simpower的核心功能是否正常工作
"""

def test_imports():
    """测试所有主要模块是否可以正常导入"""
    try:
        import simpower
        print("✓ simpower 包导入成功")
        
        from simpower import config
        print("✓ config 模块导入成功")
        
        from simpower import solve
        print("✓ solve 模块导入成功")
        
        from simpower import generators
        print("✓ generators 模块导入成功")
        
        from simpower import powersystems
        print("✓ powersystems 模块导入成功")
        
        from simpower import optimization
        print("✓ optimization 模块导入成功")
        
        return True
    except ImportError as e:
        print(f"✗ 导入失败: {e}")
        return False

def test_basic_config():
    """测试基本配置是否正常"""
    try:
        from simpower.config import user_config
        print(f"✓ 配置加载成功, 默认求解器: {user_config.solver}")
        return True
    except Exception as e:
        print(f"✗ 配置测试失败: {e}")
        return False

def test_version():
    """测试版本信息"""
    try:
        import simpower
        print(f"✓ 版本信息: {simpower.__version__}")
        return True
    except Exception as e:
        print(f"✗ 版本测试失败: {e}")
        return False

def main():
    """运行所有基本测试"""
    print("开始运行 simpower 基本功能测试...\n")
    
    tests = [
        ("模块导入", test_imports),
        ("基本配置", test_basic_config), 
        ("版本信息", test_version),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"运行 {test_name} 测试...")
        if test_func():
            passed += 1
        print()
    
    print(f"测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("✓ 所有基本功能测试通过!")
        return 0
    else:
        print("✗ 部分测试失败，请检查错误信息")
        return 1

if __name__ == "__main__":
    exit(main())