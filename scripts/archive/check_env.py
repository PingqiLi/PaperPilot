
import sys
import pkg_resources

print(f"Python Executable: {sys.executable}")
print(f"Sys Path: {sys.path}")

try:
    import arxiv
    print(f"Arxiv Version: {arxiv.__version__}")
    print(f"Arxiv File: {arxiv.__file__}")
except ImportError as e:
    print(f"Import Error: {e}")

installed_packages = pkg_resources.working_set
for i in installed_packages:
    if 'arxiv' in i.key:
        print(f"Installed: {i.key} {i.version}")
