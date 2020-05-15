from pathlib import Path

parent_directory = Path(__file__).parent

FRAGMENTS = {}
for filename in parent_directory.joinpath('fragments').iterdir():
  with open(filename) as f:
    FRAGMENTS[filename.stem] = f.read()

QUERIES = {}
for filename in parent_directory.joinpath('queries').iterdir():
  with open(filename) as f:
    QUERIES[filename.stem] = f.read() + "\n" + "\n".join(FRAGMENTS.values())
