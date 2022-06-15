import re


# From https://gist.github.com/tianchu/f7835b08d7c788b79ade
def remove_empty_fields(data_):
    if isinstance(data_, dict):
        for key, value in data_.copy().items():

            # Dive into a deeper level.
            if isinstance(value, (dict, list)):
                value = remove_empty_fields(value)

            # Delete the field if it's empty.
            if value in ["", None, [], {}]:
                del data_[key]

    elif isinstance(data_, list):
        for index in reversed(range(len(data_))):
            value = data_[index]

            # Dive into a deeper level.
            if isinstance(value, (dict, list)):
                value = remove_empty_fields(value)

            # Delete the field if it's empty.
            if value in ["", None, [], {}]:
                data_.pop(index)

    return data_


def reg_ex_jar(stringDict, regEx, regExInverse):
    output = [string for string in stringDict if re.search(r"\.jar$", string)]

    if regEx:
        output = [string for string in output if re.search(regEx, string)]
    if regExInverse:
        output = [string for string in output if not re.search(regExInverse, string)]

    if output:
        return output[0]
    return None


def is_stable_more_recent(releases):
    releaseTimestamp = releases.get("latestReleaseTimestamp")
    prereleaseTimestamp = releases.get("latestPrereleaseTimestamp")

    if (
        releaseTimestamp
        and prereleaseTimestamp
        and releaseTimestamp > prereleaseTimestamp
    ):
        return True
    return False


def get_filename_from_cd(cd):
    if not cd:
        return None

    filename = re.sub(r"(\"|'|;)", "", re.findall("filename=(.+)", cd)[0])
    if len(filename) == 0:
        return None

    return filename


# Derived from pluGET (https://github.com/Neocky/pluGET)
def strip_version(version):
    return re.sub(r"\.+", ".", re.sub(r"[^\d]", ".", version))


# Derived from pluGET (https://github.com/Neocky/pluGET)
def get_version_tuple(version):
    return tuple(map(int, (version.split("."))))


# Derived from pluGET (https://github.com/Neocky/pluGET)
def compare_versions(latestVersion, currentVersion):
    try:
        currentVersionTuple = get_version_tuple(strip_version(currentVersion))
        latestVersionTuple = get_version_tuple(strip_version(latestVersion))
    except ValueError:
        return False

    return latestVersionTuple > currentVersionTuple
