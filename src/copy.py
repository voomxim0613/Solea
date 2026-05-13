#!/usr/bin/env python3

import urllib.request
import json
import shutil
import os
import subprocess
import threading
from pathlib import Path

DEBUG = False
THREADS_NUM = 15
PAGE_SIZE = 100  # 100 max
MAX_LINE_LENGTH = 500

gh_api_url = 'https://api.github.com/search/repositories'
gh_api_query = f"?q=vless+vmess+v2ray&sort=updated&order=desc&per_page={PAGE_SIZE}"

TEMP_DIR = "tmp"

LINK_PREFIXES = ["vless://", "vmess://", "trojan://", "v2rayn://"]
BLACK_LIST_FILE = "src/repo-cfg.txt"
FILTERED_REPOS = []


def LoadReposConfig():
    with open(BLACK_LIST_FILE, 'r') as file:
        for line in file:
            if line:
                s = line.strip().lower()
                if (len(s) > 5 and
                    s.startswith("https://github.com/") and
                        s not in FILTERED_REPOS):
                    FILTERED_REPOS.append(s)
    # print(json.dumps(FILTERED_REPOS, indent=4))


def IsFilteredRepo(url):
    if not url:
        return True
    for repo in FILTERED_REPOS:
        if url.lower() == repo:
            return True
    return False


def ToChunks(array):
    chunk_size = len(array) // THREADS_NUM
    chunks = [array[i:i + chunk_size]
              for i in range(0, len(array), chunk_size)]
    # If uneven, adjust last chunk
    if len(chunks) > THREADS_NUM:
        last = THREADS_NUM - 1
        chunks[last].extend(chunks.pop())
    return chunks


def CreateDirs():
    root = TEMP_DIR
    shutil.rmtree(root, ignore_errors=True)
    for dir in ["repos", "links"]:
        path = os.path.join(root, dir)
        os.makedirs(path, exist_ok=True)


def Retry(tag, f, times):
    if times < 0:
        return False
    try:
        return f()
    except Exception as e:
        print(f"{tag} Error: {e}, Retry: {times}")
    Retry(tag, f, times - 1)


def WriteAllText(file, content):
    with open(file, 'w+') as f:
        f.write(content)


def SearchReposCore():
    url = f"{gh_api_url}{gh_api_query}"
    print(f"get: {url}")

    headers = {
        "Accept": "application/vnd.github.text-match+json",
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "MyPythonApp"
    }

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        return response.read().decode('utf-8')
    return None


def IsShareLink(line):
    if not line or len(line) > MAX_LINE_LENGTH:
        return False
    for mark in LINK_PREFIXES:
        if line.startswith(mark):
            return True
    return False


def GetReposFromFile():
    path = "dev/repos.json"
    with open(path, "r") as f:
        return f.read()


def SearchRepos():
    text = DEBUG and GetReposFromFile() or Retry(
        "SearchRepoCore()", SearchReposCore, 3)

    len_search = 0
    r = set()
    try:
        data = json.loads(text)
        len_search = len(data and data["items"] or [])
        for item in data["items"]:
            url = item["clone_url"]
            if IsFilteredRepo(url):
                print(f"filtered repo: {url}")
            else:
                r.add(url)
    except Exception as e:
        print(f"SearchRepos() error: {e}")
    SetEnvVar("CREPO_SEARCH", len_search)
    SetEnvVar("CREPO_FILTERED", len(FILTERED_REPOS))
    SetEnvVar("CREPO_REMAIN", len(r))
    return list(r)


def CloneRepo(repo_url, dest):
    def action():
        subprocess.run(["git", "clone", "--depth", "1", "--",
                        repo_url, dest], check=True)
        return True
    Retry("CloneRepo()", action, 3)


def ExtractLinks(root_dir):
    links = set()
    path = Path(root_dir)
    for file_path in path.rglob('*'):
        if not file_path.is_file():  # Ensure we only read actual files
            continue
        DEBUG and print(f"reading: {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    text = line.strip()
                    if IsShareLink(text):
                        links.add(text)
        except Exception as e:
            DEBUG and print(f"read {file_path} error: {e}")
    return links


def SaveLinks(owner, repo, links):
    if len(links) < 1:
        return
    path = os.path.join(TEMP_DIR, "links", f"{owner}-{repo}.txt")
    with open(path, "w+") as f:
        for link in links:
            f.write(f"{link}\n")


def ProcessReposUrl(name, urls, results):
    for url in urls:
        owner, repo = url.split(".git")[0].split("/")[-2:]
        dest = os.path.join(TEMP_DIR, "repos", f"{owner}-{repo}")
        print(f"worker: {name}, clone: {url}, to: {dest}")
        DEBUG or CloneRepo(url, dest)
        links = DEBUG and set() or ExtractLinks(dest)
        results[url] = len(links)
        DEBUG or print(
            f'worker: {name}, url: "{url}", links: {len(links)}')
        DEBUG or SaveLinks(owner, repo, links)


def SetEnvVar(name, value):
    s = f"{name}={value}"
    print(s)
    env_file = os.environ.get('GITHUB_ENV')
    if env_file:
        with open(env_file, 'a') as f:
            f.write(s)
            f.write('\n')


def LogToSummary(s):
    print(s)
    summary_file_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_file_path:
        with open(summary_file_path, 'a') as f:
            f.write(s)
            f.write('\n')


def TestRepoFilter():
    # LoadBlackList()
    fail = 0
    ok = 0
    for repo in FILTERED_REPOS:
        if IsFilteredRepo(repo):
            ok = ok + 1
        else:
            fail = fail + 1
    print(f"ok: {ok}, expect: {len(FILTERED_REPOS)}")
    print(f"fail: {fail}, expect: 0")
    repos = [
        "abc.com",
        "http",
        "https://github.com/denxv/TGV2RayScraper.git",
        "TGV2RayScraper.git",
        "https://github.com",
        "denxv/TGV2RayScraper",
    ]
    for repo in repos:
        m = IsFilteredRepo(repo)
        print(f"repo: {repo} result: {m}")


def Main():
    LogToSummary(f"profile: {DEBUG and "debug" or "release"}")
    LoadReposConfig()
    LogToSummary(f"filter: {len(FILTERED_REPOS)} repos")
    # TestRepoFilter()
    # return
    DEBUG or CreateDirs()

    repos = SearchRepos()
    if len(repos) < 1:
        print('Error: no repo found!')
        return

    chunks = ToChunks(repos)
    results = {}
    threads = []
    for i in range(THREADS_NUM):
        name = f"#{i+1}"
        t = threading.Thread(target=ProcessReposUrl,
                             args=(name, chunks[i], results))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
    total_dict = dict(
        sorted(results.items(), key=lambda item: item[1], reverse=True))
    total_count = sum(results.values())
    sep_list = json.dumps(list(total_dict.values()))
    LogToSummary("results:")
    LogToSummary(json.dumps(total_dict, indent=4))
    LogToSummary(f"total: {total_count}")
    SetEnvVar("SEP_COUNT", total_count)
    SetEnvVar("SEP_LIST", f"'{sep_list}'")


if __name__ == "__main__":
    Main()
