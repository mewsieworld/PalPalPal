"""Help > Check for Updates: GitHub releases of the private repo, download, and the exe swap."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)


# ---------------------------------------------------------------------------
# Updates (GitHub releases built from UPDATE_BRANCH)
# ---------------------------------------------------------------------------

def parse_version(text):
    """'v1.2.10' -> (1, 2, 10); anything that isn't a number counts as 0."""
    parts = []
    for bit in str(text).strip().lstrip("vV").split("-")[0].split("."):
        digits = "".join(ch for ch in bit if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts + [0] * (3 - len(parts)))


def update_token():
    """The read-only GitHub token the release build bakes in (None when running from source)."""
    try:
        from _update_token import TOKEN
        return TOKEN or None
    except ImportError:
        return os.environ.get("PALPALPAL_UPDATE_TOKEN") or None


def github_headers(accept):
    headers = {"Accept": accept, "User-Agent": "%s/%s" % (APP_NAME, APP_VERSION)}
    token = update_token()
    if token:
        headers["Authorization"] = "Bearer " + token
    return headers


def fetch_latest_release(repo=UPDATE_REPO, branch=UPDATE_BRANCH, timeout=10):
    """The newest published release built from the update branch, as GitHub's JSON, or None if there is none."""
    import urllib.error
    import urllib.request
    req = urllib.request.Request("https://api.github.com/repos/%s/releases?per_page=20" % repo,
                                 headers=github_headers("application/vnd.github+json"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            releases = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            raise RuntimeError("GitHub refused this copy's update key (it may have expired). Download the latest "
                               "PalPalPal.exe from whoever gave you this one.")
        if exc.code == 404:
            raise RuntimeError("The update repository %s can't be reached.%s" % (
                repo, "" if update_token() else " It's private, and this copy has no update key (only the "
                                                "released PalPalPal.exe has one)."))
        raise
    for rel in releases:
        if rel.get("draft") or rel.get("prerelease"):
            continue
        if rel.get("target_commitish") not in (branch, None, "") and len(rel.get("target_commitish", "")) != 40:
            continue  # built from some other branch
        return rel
    return None


def download_file(url, path, progress=None, timeout=30):
    import urllib.request
    req = urllib.request.Request(url, headers=github_headers("application/octet-stream"))
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(path + ".part", "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if progress:
                progress(done, total)
    os.replace(path + ".part", path)


def write_swap_script(old_exe, new_exe, pid):
    """A small batch file that waits for this process to end, swaps the exe in, relaunches it and deletes itself."""
    script = os.path.join(os.path.dirname(old_exe), "palpalpal_update.bat")
    # Full System32 paths so a Unix "find" on PATH can't break the wait; ping is the pause because
    # "timeout" fails without a console window
    sys32 = r"%SystemRoot%\System32"
    with open(script, "w", encoding="mbcs" if sys.platform == "win32" else "utf-8", errors="replace",
              newline="\r\n") as f:
        f.write('@echo off\n'
                ':wait\n'
                '"{s}\\tasklist.exe" /FI "PID eq {pid}" /NH | "{s}\\find.exe" " {pid} " >NUL\n'
                'if not errorlevel 1 (\n'
                '  "{s}\\PING.EXE" -n 2 127.0.0.1 >NUL\n'
                '  goto wait\n'
                ')\n'
                ':swap\n'
                'move /y "{new}" "{old}" >NUL\n'
                'if errorlevel 1 (\n'
                '  "{s}\\PING.EXE" -n 2 127.0.0.1 >NUL\n'
                '  goto swap\n'
                ')\n'
                'start "" "{old}"\n'
                '(goto) 2>NUL & del "%~f0"\n'.format(s=sys32, pid=pid, new=new_exe, old=old_exe))
    return script
