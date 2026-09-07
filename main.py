import sys
import os

# Ensure project directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cli import main as cli_main

if __name__ == "__main__":
    cli_main()
