import json

from core.overhead_geometry import test_case_001_geometry


if __name__ == "__main__":
    print(json.dumps(test_case_001_geometry(), indent=2))
