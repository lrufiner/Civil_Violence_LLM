import sys
from pathlib import Path

# Garantiza que los paquetes de nivel raíz (decision/, llm/, metrics/, etc.) sean importables en tests.
sys.path.insert(0, str(Path(__file__).parent))
