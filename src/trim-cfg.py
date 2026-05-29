#!/usr/bin/env python3

CFG_FILE = "src/repo-cfg.txt"


def IsUrl(s):
    if s is not None and s.startswith("https://"):
        return True
    return False


def HasContent(s):
    if s is None or len(s) < 1:
        return False
    return True


def ParseLine(line):
    if not HasContent(line):
        return None
    if IsUrl(line):
        return line
    if line.startswith('"'):
        parts = line.split('"')
        for part in parts:
            if HasContent(part) and IsUrl(part):
                return part
    return None


def AddDotGit(url):
    url = url.strip()
    if len(url) > 0 and not url.endswith(".git"):
        return f"{url}.git\n"
    return f"{url}\n"


def LoadConfig(filename):
    r = set()
    with open(filename, 'r') as file:
        for line in file:
            s = ParseLine(line)
            if HasContent(s):
                g = AddDotGit(s)
                r.add(g)
    return r


def WriteToFile(filename, data):
    with open(filename, 'w+') as file:
        for line in sorted(data):
            file.write(line)
            if not line.endswith("\n"):
                file.write("\n")


def Main():
    data = LoadConfig(CFG_FILE)
    print(f"Load {len(data)} lines from: {CFG_FILE}")
    WriteToFile(CFG_FILE, data)
    print("done")


if __name__ == "__main__":
    Main()
