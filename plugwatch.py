import os
import sys

from src.config import settings
from src.info import generate_plugins_json
from src.process import process_all_plugins, process_plugin

pluginVersion = "0.1-alpha"

print(f"\n🔌 plugwatch {pluginVersion}")
print("------------------------------------------")

# Make a plugins folder if it doesn't exist
if not os.path.exists(settings.pluginsPath):
    os.mkdir(settings.pluginsPath)

# Check if plugins.json exists
if not os.path.exists("plugins.json"):
    print("\n⚙️ plugins.json does not exist!")

    print(f"   💡 Generating from your plugins path ({settings.pluginsPath})...")
    if not generate_plugins_json():
        print(
            "\n❕ I couldn't find any plugins, so plugins.json won't contain any entries."
        )
    print(
        "\n✅ Done! Please fill it out (refer to https://github.com/shifterest/plugwatch#schema), then run this script again.\n"
    )
    sys.exit()

# Alert user of auto-download mode
if not settings.autoDownloads:
    print("🔴 Auto-downloads are disabled! No changes will be written to disk.\n")
else:
    print("🟢 Auto-downloads are enabled!\n")

# Bring the action
if len(sys.argv) >= 2:
    if sys.argv[1] == "--generate" or sys.argv[1] == "-g":
        print("💡 Generating missing plugins.json entries...")
        generate_plugins_json(True)
        print("\n✅ Done!\n")
        sys.exit()
    else:
        process_plugin(sys.argv[1])
else:
    process_all_plugins()

print("\n✅ All plugs have been watched! Whatever that means.\n")
