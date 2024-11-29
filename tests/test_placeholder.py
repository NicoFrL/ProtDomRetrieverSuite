from protdomretrieversuite.utils.config import BaseConfig
from pathlib import Path
import unittest

class ConfigTests(unittest.TestCase):
    """Basic tests for configuration functionality"""
    
    def test_base_config_initialization(self):
        """Test that BaseConfig initializes with correct default values"""
        config = BaseConfig(output_dir=Path("test_output"))
        
        self.assertEqual(config.output_dir, Path("test_output"))
        self.assertIsNone(config.log_dir)
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.timeout, 300)

if __name__ == '__main__':
    unittest.main()
