"""``python -m cleanarch`` -> the CLI entrypoint."""

import sys

from cleanarch.bootstrap.cli import main

sys.exit(main())
