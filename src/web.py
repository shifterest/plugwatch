import json
import os
import re
import zipfile
from io import BytesIO

import requests
from sty import fg

from src.config import settings
from src.utils import (
    compare_versions,
    get_filename_from_cd,
    is_stable_more_recent,
    reg_ex_jar,
)


def request_api(url):
    response = requests.get(url, headers={"User-Agent": settings.userAgent})
    return json.loads(response.text)


def request_github_api(url):
    if settings.githubToken:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"token {settings.githubToken}",
        }
        response = requests.get(url, headers=headers)
        return json.loads(response.text)
    return request_api(url)


def download_file(url, headers):
    try:
        return requests.get(url, headers=headers, allow_redirects=True)
    except:
        print(fg.red + "   ❗ Download failed! " + fg.rs)
        return None


def download_artifacts(url, regEx, regExInverse, jarPath):
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

            # Write to temporary file
            with open(f"{settings.pluginsPath}/{zipMember}.temp", "wb") as f:
                f.write(artifact.read())

            if jarPath:
                os.remove(jarPath)
            if os.path.exists(f"{settings.pluginsPath}/{zipMember}"):
                os.remove(f"{settings.pluginsPath}/{zipMember}")
            os.rename(
                f"{settings.pluginsPath}/{zipMember}.temp",
                f"{settings.pluginsPath}/{zipMember}",
            )

            print(
                f"{fg.green}   ⬇️ Extracted to {settings.pluginsPath}/{zipMember}{fg.rs}"
            )


def download_plugin(url, filename, jarPath):
    print(f"   ⬇️ Downloading {url}")

    headers = {"User-agent": settings.userAgent}
    pluginFile = download_file(url, headers)

    if pluginFile:
        # Custom filename > filename from content-disposition > filename from URL
        if not filename:
            filename = get_filename_from_cd(
                pluginFile.headers.get("content-disposition")
            )
        if not filename:
            filename = url.rsplit("/", 1)[1]

        with open(f"{settings.pluginsPath}/{filename}.temp", "wb") as f:
            f.write(pluginFile.content)

        if jarPath:
            os.remove(jarPath)
        if os.path.exists(f"{settings.pluginsPath}/{filename}"):
            os.remove(f"{settings.pluginsPath}/{filename}")
        os.rename(
            f"{settings.pluginsPath}/{filename}.temp",
            f"{settings.pluginsPath}/{filename}",
        )

        print(f"{fg.green}   ⬇️ Saved to {settings.pluginsPath}/{filename}{fg.rs}")


def download_precedence(info, name, currentVersion=None, jarPath=None):
    if "customPrecedence" in info and isinstance(info["customPrecedence"], list):
        if info.get("customPrecedenceOnly"):
            precedence = info["customPrecedence"]
        else:
            precedence = info["customPrecedence"] + settings.precedence
    else:
        precedence = settings.precedence

    for repo in precedence:
        if repo in info:
            url = None
            filename = None
            moreRecent = False

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
                    filename = (
                        re.sub("[^a-z0-9]", "", name, count=0, flags=re.I)
                        + "-spigot-"
                        + str(info["spigot"]["latestVersion"])
                        + ".jar"
                    )

                    if currentVersion and compare_versions(
                        info["spigot"]["latestVersion"], currentVersion
                    ):
                        moreRecent = True

                    if "latestVersionExternalUrl" in info["spigot"]:
                        url = info["spigot"]["latestVersionExternalUrl"]
                    else:
                        url = info["spigot"]["latestVersionUrl"]
                # DevBukkit
                case "bukkit":
                    filename = (
                        re.sub("[^a-z0-9]", "", name, count=0, flags=re.I)
                        + "-bukkit.jar"
                    )

                    url = info["bukkit"]["latestVersionUrl"]
                # GitHub
                case "github":
                    if settings.githubToken and (
                        ("artifacts" in info["github"] and settings.preferActions)
                        or "releases" not in info["github"]
                    ):
                        regEx = info["github"].get("regEx", ".*")
                        regExInverse = info["github"].get("regExInverse", ".^")

                        # Actions
                        download_artifacts(
                            info["github"]["latestArtifactUrl"],
                            regEx,
                            regExInverse,
                            jarPath,
                        )
                        break
                    if "releases" in info["github"]:
                        # Releases
                        if (
                            (
                                "latestReleaseUrl" in info["github"]["releases"]
                                and settings.preferStable
                            )
                            or (
                                settings.considerStable
                                and is_stable_more_recent(info["github"]["releases"])
                            )
                            or (
                                "latestReleaseUrl" in info["github"]["releases"]
                                and "latestPrereleaseUrl"
                                not in info["github"]["releases"]
                            )
                        ):
                            if currentVersion and compare_versions(
                                info["github"]["releases"]["latestRelease"],
                                currentVersion,
                            ):
                                moreRecent = True

                            url = info["github"]["releases"]["latestReleaseUrl"]
                        else:
                            if currentVersion and compare_versions(
                                info["github"]["releases"]["latestPrerelease"],
                                currentVersion,
                            ):
                                moreRecent = True

                            url = info["github"]["releases"]["latestPrereleaseUrl"]
                    else:
                        continue
                # Jenkins
                case "jenkins":
                    regEx = info.get("jenkinsRegEx", ".*")
                    regExInverse = info.get("jenkinsRegExInverse", ".^")

                    if (
                        "stable" in info["jenkins"] and settings.preferStable
                    ) or "successful" not in info["jenkins"]:
                        url = info["jenkins"]["latestStableBuildUrl"]
                    else:
                        url = info["jenkins"]["latestSuccessfulBuildUrl"]

            if isinstance(info.get("filename"), str):
                filename = info.get("filename")

            if isinstance(url, str):
                if (
                    not jarPath
                    or moreRecent
                    or (not moreRecent and settings.forceRedownload)
                    or repo == "directUrls"
                    or repo == "bukkit"
                    or repo == "jenkins"
                ):
                    download_plugin(url, filename, jarPath)
                else:
                    print(f"   ✨ You already have the latest version!")
            break
