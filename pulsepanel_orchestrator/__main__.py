"""Allow running the orchestrator as: python -m pulsepanel_orchestrator

Equivalent to: python -m pulsepanel_orchestrator.cli --stdin
"""

from .cli import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
