import io
import json
import os
import re
import sys
from datetime import datetime
from glob import glob
from zipfile import BadZipFile, ZipFile

from dateutil import parser
from sty import RgbFg, Style, fg

from src.config import settings
from src.utils import compare_versions, reg_ex_jar, remove_empty_fields
from src.web import request_api, request_github_api


# Derived from pluGET (https://github.com/Neocky/pluGET)
def cook_breakfast(jarPath, **args):
    try:
        with ZipFile(jarPath, "r") as pluginJar:
            with io.TextIOWrapper(
                pluginJar.open("plugin.yml"), encoding="utf-8"
            ) as pluginYml:
                for line in pluginYml:
                    # Extract name
                    if re.match(r"\s*name:", line):
                        pluginName = (
                            re.sub(r"^\s*name:", "", line)
                            .replace("\n", "")
                            .replace("'", "")
                            .replace('"', "")
                            .strip()
                        )
                    # Extract version
                    if args.get("includeVersion") and re.match(r"\s*version:", line):
                        pluginVersion = (
                            re.sub(r"^\s*version:", "", line)
                            .replace("\n", "")
                            .replace("'", "")
                            .replace('"', "")
                            .strip()
                        )
    except (BadZipFile, KeyError, UnicodeDecodeError):
        print(f"   ❌ {jarPath} is not a valid plugin! Exiting.\n")
        sys.exit()

    jarInfo = {"name": pluginName}
    if args.get("includeVersion"):
        jarInfo.update({"version": pluginVersion})
    if args.get("includePath"):
        jarInfo.update({"jarPath": jarPath})

    return jarInfo


def get_jar_info(**args):
    jarPaths = list(glob(rf"{settings.pluginsPath}/*.jar"))
    jarInfoList = []

    if jarPaths:
        for jarPath in jarPaths:
            # If name is specified
            if args.get("name"):
                jarName = cook_breakfast(jarPath)["name"]
                if re.fullmatch(args.get("name"), jarName, flags=re.I):
                    return cook_breakfast(
                        jarPath, includeVersion=True, includePath=True
                    )
            else:
                jarInfoList.append(
                    cook_breakfast(
                        jarPath,
                        includeVersion=args.get("includeVersion"),
                        includePath=args.get("includePath"),
                    )
                )

    if args.get("name"):
        return None
    return jarInfoList


def get_json_info(name=None):
    with open("plugins.json") as pluginsJson:
        # If name is specified
        if name:
            return next(
                (
                    plugin
                    for plugin in json.load(pluginsJson)["plugins"]
                    if re.fullmatch(name, plugin["name"], flags=re.I)
                ),
                None,
            )
        return remove_empty_fields(json.load(pluginsJson)["plugins"])


def generate_plugins_json(addMissing=False):
    currentInfo = get_jar_info(includeVersion=False, includePath=False)
    # If generating missing entries
    if addMissing and os.path.exists("plugins.json"):
        jsonInfoNames = [entry["name"] for entry in get_json_info()]
        currentInfo = get_json_info() + [
            entry for entry in currentInfo if entry["name"] not in jsonInfoNames
        ]
    pluginsJson = {
        "$schema": "https://github.com/shifterest/plugwatch/raw/main/schema.json",
        "plugins": currentInfo,
    }

    with open("plugins.json", "w") as f:
        json.dump(pluginsJson, f, indent=4)

    if currentInfo:
        return True
    return False


def get_latest_info(jsonInfo, currentVersion):
    # Colors!
    fg.spigot = Style(RgbFg(226, 149, 1))
    fg.bukkit = Style(RgbFg(32, 150, 225))
    fg.curseforge = Style(RgbFg(250, 188, 60))
    fg.github = Style(RgbFg(155, 31, 232))
    fg.jenkins = Style(RgbFg(76, 201, 240))
    latestVersion = None
    mostRecentVersion = None
    # githubRegEx and githubRegExInverse is included for artifacts
    info = {
        "moreRecentPrecedence": [],
        "customPrecedence": jsonInfo.get("customPrecedence"),
        "customPrecedenceOnly": jsonInfo.get("customPrecedenceOnly"),
        "filename": jsonInfo.get("filename"),
        "directUrls": {
            "stableDirectUrl": jsonInfo.get("stableDirectUrl"),
            "experimentalDirectUrl": jsonInfo.get("experimentalDirectUrl"),
        },
        "spigot": {},
        "bukkit": {},
        "github": {
            "regEx": jsonInfo.get("githubRegEx"),
            "regExInverse": jsonInfo.get("githubRegExInverse"),
        },
        "jenkins": {},
    }

    # SpigotMC
    if "spigotId" in jsonInfo:
        url = "https://api.spiget.org/v2/resources/" + str(jsonInfo["spigotId"])
        resourceDetails = request_api(url)

        # Check if ID is valid
        if "error" in resourceDetails:
            print(fg.red + "   ➡️ [SpigotMC] Error:", resourceDetails["error"] + fg.rs)
        else:
            resourceLatestVersion = request_api(f"{url}/versions/latest")
            latestTestedVersion = resourceDetails["testedVersions"][-1]
            mostRecentVersion = latestVersion = info["spigot"]["version"] = re.sub(
                "^v", "", resourceLatestVersion["name"]
            )

            # Check for external URLs
            if resourceDetails["file"]["type"] == "external":
                if "externalUrl" in resourceDetails["file"]:
                    info["spigot"]["url"] = resourceDetails["file"]["externalUrl"]

                    print(
                        f"   {fg.spigot}➡️ [SpigotMC]{fg.rs} Fetched latest version"
                        f" {latestVersion} (tested on {latestTestedVersion})"
                    )
                    print(
                        f"   {fg.spigot}➡️ [SpigotMC]{fg.rs} Download redirects to"
                        " external URL. Auto-download is not guaranteed to work."
                    )
                else:
                    print(
                        f"   {fg.spigot}➡️ [SpigotMC]{fg.rs} Download is external but"
                        " no URL is provided. Auto-download isn't possible."
                    )
            elif resourceDetails["file"]["type"] != ".jar":
                print(
                    f"   {fg.spigot}➡️ [SpigotMC]{fg.rs} Download is not a JAR file."
                    " Auto-download isn't possible (but might be soon)."
                )
            else:
                info["spigot"]["url"] = f"{url}/download"
                print(
                    f"   {fg.spigot}➡️ [SpigotMC]{fg.rs} Fetched latest version"
                    f" {latestVersion} (tested on {latestTestedVersion})"
                )

            if (
                "url" in info["spigot"]
                and currentVersion
                and compare_versions(latestVersion, currentVersion)
            ):
                info["moreRecentPrecedence"].append("spigot")

    # DevBukkit
    if "bukkitSlug" in jsonInfo:
        info["bukkit"]["url"] = (
            "https://dev.bukkit.org/projects/"
            + jsonInfo["bukkitSlug"]
            + "/files/latest"
        )
        print(f"   {fg.bukkit}➡️ [DevBukkit]{fg.rs} Generated URL")

    # GitHub
    if "githubRepo" in jsonInfo:
        url = "https://api.github.com/repos/" + jsonInfo["githubRepo"]
        releasesList = request_github_api(f"{url}/releases")

        # Releases
        if len(releasesList):
            latestRelease = next((r for r in releasesList if not r["prerelease"]), None)
            latestPrerelease = next((r for r in releasesList if r["prerelease"]), None)

            # Latest release
            if latestRelease and latestRelease["assets"]:
                latestVersion = latestReleaseVersion = re.sub(
                    r"^v", "", latestRelease["tag_name"]
                )
                latestReleaseTimestamp = int(
                    datetime.timestamp(parser.parse(latestRelease["created_at"]))
                )

                info["github"]["releaseUrl"] = reg_ex_jar(
                    (a["browser_download_url"] for a in latestRelease["assets"]),
                    jsonInfo.get("githubRegEx"),
                    jsonInfo.get("githubRegExInverse"),
                )

                print(
                    f"   {fg.github}➡️ [GitHub]{fg.rs} Fetched latest release"
                    f" {latestReleaseVersion}"
                )

            # Latest pre-release
            if latestPrerelease and latestPrerelease["assets"]:
                latestVersion = latestPrereleaseVersion = re.sub(
                    r"^v", "", latestPrerelease["tag_name"]
                )
                latestPrereleaseTimestamp = int(
                    datetime.timestamp(parser.parse(latestPrerelease["created_at"]))
                )

                if latestReleaseTimestamp > latestPrereleaseTimestamp:
                    print(
                        f"   {fg.github}❕ [GitHub]{fg.rs} Latest release is more recent"
                        " than latest pre-release"
                    )
                else:
                    info["github"]["prereleaseUrl"] = reg_ex_jar(
                        (a["browser_download_url"] for a in latestPrerelease["assets"]),
                        jsonInfo.get("githubRegEx"),
                        jsonInfo.get("githubRegExInverse"),
                    )

                    print(
                        f"   {fg.github}➡️ [GitHub]{fg.rs} Fetched latest pre-release"
                        f" {latestPrereleaseVersion}"
                    )

            if currentVersion and compare_versions(latestVersion, currentVersion):
                if (
                    latestVersion
                    and mostRecentVersion
                    and compare_versions(latestVersion, mostRecentVersion)
                ):
                    mostRecentVersion = latestVersion
                    info["moreRecentPrecedence"].insert(0, "github")
                else:
                    info["moreRecentPrecedence"].append("github")

        # Actions
        artifacts = request_github_api(f"{url}/actions/artifacts")

        if artifacts["total_count"]:
            latestArtifact = next(
                (
                    artifact
                    for artifact in artifacts["artifacts"]
                    if not artifact["expired"]
                ),
                None,
            )

            if latestArtifact:
                info["github"]["artifactUrl"] = latestArtifact["archive_download_url"]

                print(f"   {fg.github}➡️ [GitHub]{fg.rs} Fetched latest artifact")

    # Jenkins
    if "jenkinsServer" in jsonInfo:
        url = "https://" + jsonInfo["jenkinsServer"]

        # Last stable build
        lastStableBuild = request_api(f"{url}/lastStableBuild/api/json")

        info["jenkins"]["stableBuildUrl"] = reg_ex_jar(
            (
                f"{url}/lastStableBuild/artifact/" + path["relativePath"]
                for path in lastStableBuild["artifacts"]
            ),
            jsonInfo.get("jenkinsRegEx"),
            jsonInfo.get("jenkinsRegExInverse"),
        )

        print(f"   {fg.jenkins}➡️ [Jenkins]{fg.rs} Fetched last stable build")

        # Last successful build
        lastSuccessfulBuild = request_api(f"{url}/lastSuccessfulBuild/api/json")

        # Skip if both builds are the same
        if lastStableBuild["number"] == lastSuccessfulBuild["number"]:
            print(
                f"   {fg.jenkins}❕ [Jenkins]{fg.rs} Last stable build is also the last"
                " successful build"
            )
        else:
            info["jenkins"]["successfulBuildUrl"] = reg_ex_jar(
                (
                    f"{url}/lastSuccessfulBuild/artifact/" + path["relativePath"]
                    for path in lastStableBuild["artifacts"]
                ),
                jsonInfo.get("jenkinsRegEx"),
                jsonInfo.get("jenkinsRegExInverse"),
            )

            print(f"   {fg.jenkins}➡️ [Jenkins]{fg.rs} Fetched last successful build")

    return remove_empty_fields(info)
