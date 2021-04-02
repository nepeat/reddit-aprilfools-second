import sys

def parse_line(line: str):
    timestamp, data = line.strip().split("|", 2)
    return (timestamp, data)

for filename in sys.argv[1:]:
    with open(filename, "r") as f:
        for line in f.readlines():
            timestamp, data = parse_line(line)
            print(f"RPUSH reddit:second:socket:opl {data}")