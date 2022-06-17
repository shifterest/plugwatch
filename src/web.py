import json
import re
import zipfile
from io import BytesIO
import sys

import requests
from sty import fg

from src.config import settings
from src.utils import get_filename, reg_ex_jar, write_plugin


def request_api(url, headers=None):
    try:
        if not headers:
            headers = {"User-Agent": settings.userAgent}

        return json.loads(requests.get(url, headers=headers).content)
    except (TimeoutError, requests.exceptions.ConnectionError):
        print(fg.red + f"   ❗ Failed to connect to {url}! Exiting." + fg.rs)
        sys.exit()


def request_github_api(url):
    if settings.githubToken:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {settings.githubToken}",
        }

    return request_api(url, headers)


def download_file(url, headers):
    try:
        return requests.get(url, headers=headers, allow_redirects=True)
    except:
        print(fg.red + "   ❗ Download failed! " + fg.rs)
        return None


def download_artifacts(url, regEx, regExInverse, jarPath, filename):
    print("   ❕ Downloading and extracting GitHub artifacts")

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"token {settings.githubToken}",
    }
    zipFile = BytesIO(download_file(url, headers).content)

    if zipFile:
        with zipfile.ZipFile(zipFile, "r") as artifactsZip:
            zipMember = reg_ex_jar(artifactsZip.namelist(), regEx, regExInverse)
            artifact = artifactsZip.open(zipMember, "r")

            if not filename:
                filename = zipMember
            write_plugin(artifact.read(), f"{settings.pluginsPath}/{filename}", jarPath)

            print(
                f"{fg.green}   ⬇️ Extracted to"
                f" {settings.pluginsPath}/{zipMember}{fg.rs}"
            )


def download_plugin(url, jarPath, filename):
    print(f"   ⬇️ Downloading {url}")

    headers = {"User-agent": settings.userAgent}
    pluginFile = download_file(url, headers)

    if pluginFile:
        # Custom filename > filename from content-disposition > filename from URL
        if not filename:
            filename = get_filename(pluginFile.headers.get("content-disposition"))
        if not filename:
            filename = url.rsplit("/", 1)[1]

        write_plugin(pluginFile.content, f"{settings.pluginsPath}/{filename}", jarPath)

        print(f"{fg.green}   ⬇️ Saved to {settings.pluginsPath}/{filename}{fg.rs}")


def download_precedence(info, name, jarPath=None):
    if settings.forceRedownload:
        precedence = settings.precedence
    else:
        precedence = info.get("moreRecentPrecedence", [])

    if "customPrecedence" in info:
        if info.get("customPrecedenceOnly"):
            precedence = info["customPrecedence"]
        else:
            precedence = info["customPrecedence"] + precedence

    for repo in precedence:
        if repo in info:
            url = None
            filename = info.get("filename")

            match repo:
                # URLs
                case "directUrls":
                    if (
                        "stableDirectUrl" in info["directUrls"]
                        and settings.preferStable
                    ) or "experimentalDirectUrl" not in info["directUrls"]:
                        url = info["directUrls"]["stableDirectUrl"]
                    else:
                        url = info["directUrls"]["experimentalDirectUrl"]
                # SpigotMC
                case "spigot":
                    if not filename:
                        filename = (
                            re.sub("[^a-z0-9]", "", name, count=0, flags=re.I)
                            + "-"
                            + info["spigot"]["version"]
                            + ".jar"
                        )
                    url = info["spigot"]["url"]
                # DevBukkit
                case "bukkit":
                    if not filename:
                        filename = (
                            re.sub("[^a-z0-9]", "", name, count=0, flags=re.I) + ".jar"
                        )
                    url = info["bukkit"]["url"]
                # GitHub
                case "github":
                    # Actions
                    if settings.githubToken and (
                        ("artifactUrl" in info["github"] and settings.preferActions)
                        or all(
                            url not in info["github"]
                            for url in ("releaseUrl", "prereleaseUrl")
                        )
                    ):
                        download_artifacts(
                            info["github"]["artifactUrl"],
                            info["github"].get("regEx", ".*"),
                            info["github"].get("regExInverse", ".^"),
                            jarPath,
                            filename,
                        )
                        break
                    # Releases
                    if (
                        "releaseUrl" in info["github"] and settings.preferStable
                    ) or "prereleaseUrl" not in info["github"]:
                        url = info["github"]["releaseUrl"]
                    else:
                        url = info["github"]["prereleaseUrl"]
                # Jenkins
                case "jenkins":
                    if (
                        "stableBuildUrl" in info["jenkins"] and settings.preferStable
                    ) or "successfulBuildUrl" not in info["jenkins"]:
                        url = info["jenkins"]["stableBuildUrl"]
                    else:
                        url = info["jenkins"]["successfulBuildUrl"]

            if url:
                download_plugin(url, jarPath, filename)

            break
