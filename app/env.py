import os
from dotenv import dotenv_values

_env_dict = None

def get_env(key: str, default=None):
    """
    Get environment variable strictly from the .env file if it exists there.
    Ignores system environment variables for keys that are defined in .env 
    to guarantee local config takes absolute priority.
    """
    global _env_dict
    
    if _env_dict is None:
        # Resolve absolute path to .env file in project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(project_root, ".env")
        
        if os.path.exists(env_path):
            _env_dict = dotenv_values(env_path)
        else:
            _env_dict = {}

    # Strict priority: if the key exists in .env, use that value
    if key in _env_dict and _env_dict[key] is not None:
        return _env_dict[key]
        
    # Fallback to system env only if not in .env at all
    return os.getenv(key, default)
