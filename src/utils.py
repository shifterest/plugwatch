import re
import os


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


def reg_ex_jar(stringIter, regEx, regExInverse):
    output = (string for string in stringIter if re.search(r"\.jar$", string))

    if regEx:
        output = (string for string in output if re.search(regEx, string))
    if regExInverse:
        output = (string for string in output if not re.search(regExInverse, string))

    if output:
        try:
            return next(output)
        except StopIteration:
            pass
    return None


def get_filename(cd):
    if not cd:
        return None

    filename = re.sub(r"(\"|'|;)", "", re.findall("filename=(.+)", cd)[0])

    if filename:
        return filename
    return None


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


def write_plugin(content, path, *filesToDelete):
    # Write to temporary file
    with open(f"{path}.temp", "wb") as f:
        f.write(content)
    for fileToDelete in filesToDelete:
        if fileToDelete:
            os.remove(fileToDelete)
    if path and os.path.exists(path):
        os.remove(path)
    os.rename(f"{path}.temp", path)
