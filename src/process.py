import sys
import time

from src.config import settings
from src.info import get_jar_info, get_json_info, get_latest_info
from src.web import download_precedence


def process_plugin(name):
    jarInfo = get_jar_info(name=name, includeVersion=True, includePath=True)

    if not jarInfo:
        print(f"❕ I couldn't find {name} in the plugins path.")

    jsonInfo = get_json_info(name)

    if not jsonInfo:
        print(f"❌ I couldn't find {name} in plugins.json! Exiting.\n")
        sys.exit()

    print(f"🔍 Processing {name}...")

    if isinstance(jarInfo, dict):
        currentVersion = jarInfo.get("version")
        jarPath = jarInfo.get("jarPath")

        if isinstance(currentVersion, str):
            print(f"   🟡 Current version is {currentVersion}")
    else:
        currentVersion = None
        jarPath = None

    latestInfo = get_latest_info(jsonInfo, currentVersion)

    if not jsonInfo:
        print(f"❗ I couldn't find any recent info for {name}!")
        sys.exit()

    if settings.autoDownloads:
        download_precedence(latestInfo, name, currentVersion, jarPath)


def process_all_plugins():
    jarInfoList = get_jar_info(includeVersion=True, includePath=True)

    if not jarInfoList:
        print("❕ Your plugins path doesn't contain any plugins.\n")

    jsonInfoList = get_json_info()

    if not jsonInfoList:
        print("❌ Your plugins.json file doesn't contain any entries! Exiting.\n")
        sys.exit()

    print("📋 Found", len(jsonInfoList), "plugin(s) to process.")

    if len(jarInfoList) > len(jsonInfoList):
        diff = len(jarInfoList) - len(jsonInfoList)
        if diff > 1:
            print(f"❕ {diff} of your plugins don't have plugins.json entries")
        else:
            print("❕ one of your plugins doesn't have a plugins.json entry")
    elif len(jarInfoList) < len(jsonInfoList):
        diff = len(jsonInfoList) - len(jarInfoList)
        if diff > 1:
            print(f"❕ {diff} plugins.json entries do not exist in your plugins path.")
        else:
            print("❕ one plugins.json entry does not exist in your plugins path.")

    for jsonInfo in jsonInfoList:
        print("\n🔍 Processing", jsonInfo["name"] + "...")

        try:
            jarInfo = [
                plugin for plugin in jarInfoList if plugin["name"] == jsonInfo["name"]
            ][0]

            print("   🆚 Current version is", jarInfo["version"])
        except IndexError:
            jarInfo = {}

        latestInfo = get_latest_info(jsonInfo, jarInfo.get("version"))

        if settings.autoDownloads:
            download_precedence(
                latestInfo,
                jsonInfo["name"],
                jarInfo.get("version"),
                jarInfo.get("jarPath"),
            )

        # Apply delay
        time.sleep(settings.delay)
