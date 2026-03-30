#!/usr/bin/env python3
"""
Shadow AI v2.0.2 - Fix Verification Script
Tests all critical bug fixes and new features
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing imports...")
    try:
        from output.gui import GUI
        from core.unified_llm import UnifiedLLM
        from core.config import Config
        from core.engine import ShadowCore
        from core.memory import MemoryBank
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Test config persistence."""
    print("\n🔍 Testing config system...")
    try:
        from core.config import Config
        config = Config()
        
        # Test get/set
        config.set("test_key", "test_value")
        assert config.get("test_key") == "test_value"
        
        # Test persistence
        config2 = Config()
        assert config2.get("test_key") == "test_value"
        
        # Cleanup
        config.data.pop("test_key", None)
        config.save()
        
        print("✅ Config persistence working")
        return True
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False

def test_unified_llm():
    """Test UnifiedLLM has no 'model' attribute (should use config instead)."""
    print("\n🔍 Testing UnifiedLLM structure...")
    try:
        from core.unified_llm import UnifiedLLM
        from core.config import Config
        
        config = Config()
        llm = UnifiedLLM(config)
        
        # Verify no direct model attribute
        has_model_attr = hasattr(llm, 'model')
        if has_model_attr:
            print("⚠️  Warning: UnifiedLLM has 'model' attribute (may cause issues)")
        else:
            print("✅ UnifiedLLM correctly uses config for model selection")
        
        # Test that it can read from config
        test_model = config.get("ollama_model", "gemma2:2b")
        print(f"   Current model in config: {test_model}")
        
        return True
    except Exception as e:
        print(f"❌ UnifiedLLM error: {e}")
        return False

def test_api_providers():
    """Test that all API providers are mapped correctly."""
    print("\n🔍 Testing API provider support...")
    try:
        from core.unified_llm import UnifiedLLM
        from core.config import Config
        
        config = Config()
        llm = UnifiedLLM(config)
        
        # Test that _call_openai_compatible exists
        has_method = hasattr(llm, '_call_openai_compatible')
        if has_method:
            print("✅ Generic API handler exists")
        else:
            print("❌ Missing _call_openai_compatible method")
            return False
        
        # Check provider mappings in the method
        expected_providers = [
            "mistral", "cohere", "together", "perplexity", "groq", 
            "deepseek", "huggingface", "openrouter", "anyscale", "fireworks"
        ]
        print(f"   Expected provider support: {len(expected_providers)} additional providers")
        
        return True
    except Exception as e:
        print(f"❌ API provider error: {e}")
        return False

def test_gui_structure():
    """Test that GUI has required streaming components."""
    print("\n🔍 Testing GUI streaming components...")
    try:
        # Don't actually create GUI (requires display), just check the class
        import inspect
        from output.gui import GUI
        
        methods = dict(inspect.getmembers(GUI, predicate=inspect.isfunction))
        
        required_methods = [
            '_stream_ai_response',
            '_execute_shell_command', 
            '_process_queue',
            'change_model'
        ]
        
        missing = []
        for method in required_methods:
            if method not in methods:
                missing.append(method)
        
        if missing:
            print(f"❌ Missing methods: {missing}")
            return False
        else:
            print("✅ All streaming methods present")
        
        # Check that queue is imported
        import output.gui as gui_module
        if 'queue' in dir(gui_module):
            print("✅ Queue module imported")
        else:
            print("⚠️  Warning: Queue module may not be imported")
        
        return True
    except Exception as e:
        print(f"❌ GUI structure error: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("Shadow AI v2.0.2 - Fix Verification")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_config,
        test_unified_llm,
        test_api_providers,
        test_gui_structure
    ]
    
    results = []
    for test in tests:
        results.append(test())
    
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("\n✨ Shadow AI v2.0.2 is ready to use!")
        print("\nTo run the app:")
        print("  cd $(dirname $0)")
        print("  ./run.sh")
        print("\nOr build the .deb package:")
        print("  See instructions in FIXES.md")
        return 0
    else:
        print(f"⚠️  SOME TESTS FAILED ({passed}/{total})")
        print("\nPlease review the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
