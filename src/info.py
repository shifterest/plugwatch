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
from src.utils import (
    compare_versions,
    is_stable_more_recent,
    reg_ex_jar,
    remove_empty_fields,
)
from src.web import request_api, request_github_api


# Derived from pluGET (https://github.com/Neocky/pluGET)
def cook_breakfast(jarPath, **args):
    try:
        with ZipFile(jarPath, "r") as pluginJar:
            with io.TextIOWrapper(
                pluginJar.open("plugin.yml"), encoding="utf-8"
            ) as pluginYml:
                for line in pluginYml:
                    if re.match(r"\s*name:", line):
                        pluginName = (
                            re.sub(r"^\s*name:", "", line)
                            .replace("\n", "")
                            .replace("'", "")
                            .replace('"', "")
                            .strip()
                        )
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
    jarPaths = list(glob(rf"{settings.pluginsPath}\*.jar"))
    jarInfoList = []

    if jarPaths:
        for jarPath in jarPaths:
            jarName = cook_breakfast(jarPath)["name"]

            # If name is specified
            if args.get("name") and re.fullmatch(args.get("name"), jarName, flags=re.I):
                jarInfo = cook_breakfast(jarPath, includeVersion=True, includePath=True)
                return jarInfo

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
    currentInfoList = get_jar_info(includeVersion=False, includePath=False)

    if addMissing and os.path.exists("plugins.json"):
        jsonInfoNames = [entry["name"] for entry in get_json_info()]
        currentInfoList = get_json_info() + [
            entry for entry in currentInfoList if entry["name"] not in jsonInfoNames
        ]

    pluginsJson = {
        "$schema": "https://github.com/shifterest/plugwatch/raw/main/schema.json",
        "plugins": currentInfoList,
    }
    with open("plugins.json", "w") as f:
        json.dump(pluginsJson, f, indent=4, sort_keys=True)

    if currentInfoList:
        return True
    return False


def get_latest_info(jsonInfo, currentVersion=None):
    # Colors!
    fg.spigot = Style(RgbFg(226, 149, 1))
    fg.bukkit = Style(RgbFg(32, 150, 225))
    fg.curseforge = Style(RgbFg(250, 188, 60))
    fg.github = Style(RgbFg(155, 31, 232))
    fg.jenkins = Style(RgbFg(76, 201, 240))

    # githubRegEx and githubRegExInverse is included for artifacts
    info = {
        "precedence": jsonInfo.get("precedence"),
        "forcePrecedence": jsonInfo.get("forcePrecedence"),
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
            "releases": {},
        },
        "jenkins": {"stable": {}, "successful": {}},
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

            info["spigot"] = {
                "latestTestedVersion": resourceDetails["testedVersions"][-1],
                "latestVersion": re.sub("^v", "", resourceLatestVersion["name"]),
                "latestVersionUrl": f"{url}/download",
            }

            # Check for external URLs
            if resourceDetails["external"]:
                if "externalUrl" in resourceDetails["file"]:
                    info["spigot"]["latestVersionUrl"] = resourceDetails["file"][
                        "externalUrl"
                    ]
                else:
                    print(
                        f"   {fg.spigot}➡️ [SpigotMC]{fg.rs} Download URL redirects to webpage, auto-download not possible"
                    )

            if currentVersion and compare_versions(
                info["spigot"]["latestVersion"], currentVersion
            ):
                print(
                    f"   {fg.spigot}✨ [SpigotMC]{fg.rs} Fetched more recent version",
                    info["spigot"]["latestVersion"],
                    "(tested on",
                    info["spigot"]["latestTestedVersion"] + ")",
                )
            else:
                print(
                    f"   {fg.spigot}➡️ [SpigotMC]{fg.rs} Fetched latest version",
                    info["spigot"]["latestVersion"],
                    "(tested on",
                    info["spigot"]["latestTestedVersion"] + ")",
                )

    # DevBukkit
    if "bukkitSlug" in jsonInfo:
        info["bukkit"]["latestVersionUrl"] = (
            "https://dev.bukkit.org/projects/"
            + jsonInfo["bukkitSlug"]
            + "/files/latest"
        )
        print(f"   {fg.bukkit}➡️ [DevBukkit]{fg.rs} Generated URL")

    # GitHub
    if "githubRepo" in jsonInfo:
        url = "https://api.github.com/repos/" + jsonInfo["githubRepo"]
        releasesList = request_github_api(f"{url}/releases")

        try:
            # Releases
            if len(releasesList):
                # Latest stable release
                latestStableRelease = next(
                    (r for r in releasesList if not r["prerelease"]), None
                )
                latestPrerelease = next(
                    (r for r in releasesList if r["prerelease"]), None
                )

                if latestStableRelease and latestStableRelease["assets"]:
                    info["github"]["releases"] = {
                        "latestRelease": re.sub(
                            r"^v", "", latestStableRelease["tag_name"]
                        ),
                        "latestReleaseTimestamp": int(
                            datetime.timestamp(
                                parser.parse(latestStableRelease["created_at"])
                            )
                        ),
                        "latestReleaseUrl": reg_ex_jar(
                            [
                                a["browser_download_url"]
                                for a in latestStableRelease["assets"]
                            ],
                            jsonInfo.get("githubRegEx"),
                            jsonInfo.get("githubRegExInverse"),
                        ),
                    }

                    if currentVersion and compare_versions(
                        info["github"]["releases"]["latestRelease"], currentVersion
                    ):
                        print(
                            f"   {fg.github}✨ [GitHub]{fg.rs} Fetched more recent stable release",
                            info["github"]["releases"]["latestRelease"],
                        )
                    else:
                        print(
                            f"   {fg.github}➡️ [GitHub]{fg.rs} Fetched latest stable release",
                            info["github"]["releases"]["latestRelease"],
                        )

                # Latest pre-release
                latestPrerelease = next(
                    (r for r in releasesList if r["prerelease"]), None
                )

                if latestPrerelease and len(latestPrerelease["assets"]):
                    info["github"]["releases"].update(
                        {
                            "latestPrerelease": re.sub(
                                r"^v", "", latestPrerelease["tag_name"]
                            ),
                            "latestPrereleaseTimestamp": int(
                                datetime.timestamp(
                                    parser.parse(latestPrerelease["created_at"])
                                )
                            ),
                            "latestPrereleaseUrl": reg_ex_jar(
                                [
                                    a["browser_download_url"]
                                    for a in latestPrerelease["assets"]
                                ],
                                jsonInfo.get("githubRegEx"),
                                jsonInfo.get("githubRegExInverse"),
                            ),
                        }
                    )

                    if currentVersion and compare_versions(
                        info["github"]["releases"]["latestPrerelease"], currentVersion
                    ):
                        print(
                            f"   {fg.github}✨ [GitHub]{fg.rs} Fetched more recent pre-release",
                            info["github"]["releases"]["latestPrerelease"],
                        )
                    else:
                        print(
                            f"   {fg.github}➡️ [GitHub]{fg.rs} Fetched latest pre-release",
                            info["github"]["releases"]["latestPrerelease"],
                        )

                    # Check if latest stable release is more recent than latest pre-release
                    if is_stable_more_recent(info["github"]["releases"]):
                        print(
                            f"   {fg.github}➡️ [GitHub]{fg.rs} Latest stable release is more recent than latest pre-release"
                        )

            # Actions
            artifactsList = request_github_api(f"{url}/actions/artifacts")

            if artifactsList["total_count"]:
                latestArtifact = next(
                    (
                        artifact
                        for artifact in artifactsList["artifacts"]
                        if not artifact["expired"]
                    ),
                    None,
                )

                if latestArtifact:
                    info["github"]["latestArtifactUrl"] = latestArtifact[
                        "archive_download_url"
                    ]

                    print(f"   {fg.github}➡️ [GitHub]{fg.rs} Fetched latest artifact")

        except:
            if re.search("API rate limit exceeded.", releasesList.get("message", "")):
                print(
                    f"   {fg.github}❌ [GitHub]{fg.rs} You are being rate-limited. Exiting.\n"
                )
            elif re.search("Bad credentials", releasesList.get("message", "")):
                print(
                    f"   {fg.github}❌ [GitHub]{fg.rs} Your GitHub token is invalid. Exiting.\n"
                )
            sys.exit()

    # Jenkins
    if "jenkinsServer" in jsonInfo:
        url = "https://" + jsonInfo["jenkinsServer"]

        # Last stable build
        lastStableBuildDetails = request_api(f"{url}/lastStableBuild/api/json")

        info["jenkins"]["latestStableBuildUrl"] = reg_ex_jar(
            [
                f"{url}/lastStableBuild/artifact/" + path["relativePath"]
                for path in lastStableBuildDetails["artifacts"]
            ],
            jsonInfo.get("jenkinsRegEx"),
            jsonInfo.get("jenkinsRegExInverse"),
        )

        print(f"   {fg.jenkins}➡️ [Jenkins]{fg.rs} Fetched last stable build")

        # Last successful build
        lastSuccessfulBuildDetails = request_api(f"{url}/lastSuccessfulBuild/api/json")

        # Skip if both builds are the same
        if lastSuccessfulBuildDetails["number"] != lastStableBuildDetails["number"]:
            info["jenkins"]["latestSuccessfulBuildUrl"] = reg_ex_jar(
                [
                    f"{url}/lastSuccessfulBuild/artifact/" + path["relativePath"]
                    for path in lastStableBuildDetails["artifacts"]
                ],
                jsonInfo.get("jenkinsRegEx"),
                jsonInfo.get("jenkinsRegExInverse"),
            )

            print(f"   {fg.jenkins}➡️ [Jenkins]{fg.rs} Fetched last successful build")

    return remove_empty_fields(info)
