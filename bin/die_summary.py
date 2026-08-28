import pathlib
import sys
BIN = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BIN))
from die_cron import main
raise SystemExit(main("summary"))
