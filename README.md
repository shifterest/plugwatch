# plugwatch

A mediocre Minecraft server plugin updater.

This is my first time coding something in Python, or coding anything for public use, so pull requests and suggestions are very welcome.

![image](https://user-images.githubusercontent.com/86647101/173960483-3441b095-71d0-489d-8d3f-51eb3f506d47.png)

## Acknowledgments

Some code is derived from [pluGET](https://github.com/Neocky/pluGET) by [Neocky](https://github.com/Neocky).

## Features

plugwatch only supports downloading latest versions of plugins.

| Repository/server | Auto-download | RegEx filtering |
| ----------------- | ------------- | --------------- |
| SpigotMC          | ✅            | N/A             |
| DevBukkit         | ✅ forced[^1] | N/A             |
| GitHub releases   | ✅ forced[^1] | ✅ link         |
| GitHub Actions    | ✅ forced[^1] | ✅ filename     |
| Jenkins           | ✅            | ✅ link         |
| Direct links      | ✅            | N/A             |

[^1]: `forceDownloads` needs to be enabled in `settings.toml`

## Usage

#### _Do not run this script on plugins from a running server._

### 1. Clone this repository

Refer to [Cloning a repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/cloning-a-repository) for instructions.

### 2. Install Python and its dependencies

Get Python [here](https://www.python.org/downloads). To avoid problems, get a version later than `3.10`.

After installing Python, install the dependencies for this project by executing this command in `/plugwatch`:

```
py -m pip install -r requirements.txt
```

### 3. Configuration

Create configuration files `settings.toml` and `.secrets.toml` in `/plugwatch` (refer [below](#configuration)).

Configuration files are not required. Again, refer [below](#configuration) for the default values that will be used without them.

### 4. Execute the script

Execute this command in `/plugwatch`:

```
py plugwatch.py
```

If `plugins.json` doesn't exist yet, the script will generate it using the plugins already in your plugins path (default `plugins`).

To generate missing `plugins.json` entries, run the script with `--generate` or `-g` as an argument.

To process a single plugin, run the script with the plugin name as an argument. The plugin name isn't case-sensitive.

## Configuration

### `settings.toml`

```ini
# User agent for browsing the interwebz.
userAgent = "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36"

# Precedence list for plugin downloads. This is ignored if forceDownloads is disabled.
precedence = ["directUrls", "github", "jenkins", "spigot", "bukkit"]

# Path where plugins are processed and downloaded.
pluginsPath = "plugins"

# Whether to automatically download and replace plugins.
autoDownloads = false

# Whether to force download of plugins regardless of version. This is also the only way
# to allow downloads from direct URLs, DevBukkit and Jenkins (since they don't provide
# plugin versions explicitly).
forceDownloads = false

# Whether to prefer stable builds/releases.
preferStable = true

# Whether to prefer GitHub Actions artifacts over releases.
preferActions = false

# Delay for checking updates between plugins in seconds.
delay = 0
```

### `.secrets.toml`

```ini
# Token to use for GitHub API requests (scope public_repo is required). This is required
# for GitHub Actions artifacts.
githubToken = "token"
```

## Schema

Using an editor with [JSON schema support](https://json-schema.org/implementations.html#editors) support, use the following template for `plugins.json`:

```jsonc
{
  "$schema": "https://github.com/shifterest/plugwatch/raw/main/schema.json",
  "plugins": [
    {
      // The name of the plugin. This should be generated by the script and should not
      // contain spaces.
      "name": "PluginName",

      // Custom precedence list for plugin downloads.
      "customPrecedence": ["spigot", "github"],

      // If true, the script will only download from repositories/servers in
      // customPrecedence. Otherwise, the script will attempt to download from
      // customPrecedence first.
      "customPrecedenceOnly": false,

      // Filename to use for this specific plugin.
      "filename": "CustomPluginName.jar",

      // The SpigotMC ID of the plugin. To get the ID of a SpigotMC plugin, go to its
      // webpage and copy the trailing numbers.
      // https://www.spigotmc.org/resources/essentialsx.9089/ -> 9089
      "spigotID": 12345,

      // The DevBukkit slug of the plugin. To get the slug of a DevBukkit plugin, go to
      // its webpage and copy everything after the last slash.
      // https://dev.bukkit.org/projects/worldedit -> worldedit
      "bukkitSlug": "plugin-slug",

      // The GitHub repository of the plugin.
      "githubRepo": "github/repo",

      // Regular expressions used to filter out a single plugin (if releases/artifacts
      // have multiple files).
      // If the name/link of the file satisfies githubRegEx, it will be included.
      // If the name/link of the file satisfies githubRegExInverse, it will be excluded.
      "githubRegEx": ".*",
      "githubRegExInverse": ".^",

      // The Jenkins server of the plugin.
      "jenkinsServer": "jenkins.server.com/job/PluginName",

      // Same as githubRegEx and githubRegExInverse, respectively.
      "jenkinsRegEx": ".*",
      "jenkinsRegExInverse": ".^",

      // Direct download URLS for the plugin.
      "stableDirectUrl": "https://download.plugin.com/stable",
      "experimentalDirectUrl": "https://download.plugin.com/experimental"
    }
  ]
}
```

Take note that each entry corresponds to **a single** plugin only. If multiple plugins come from the same repository/server, use regular expressions for each plugin instead.
