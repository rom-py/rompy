from importlib import resources
import shutil
from pathlib import Path


def extract_notebooks(dest_dir="docs/notebooks"):
    notebook_dir = resources.files("rompy_notebooks") / "notebooks_data"
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    shutil.copytree(notebook_dir, dest, dirs_exist_ok=True)
    print(f"Copied notebooks to {dest.resolve()}")


if __name__ == "__main__":
    extract_notebooks()
