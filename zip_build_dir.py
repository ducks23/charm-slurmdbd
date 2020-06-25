#!/usr/bin/env python3
import os
import yaml
import zipfile
import pathlib
def handle_package():
    """Handle the final package creation."""
    with pathlib.Path('metadata.yaml').open('rt', encoding='utf8') as fh:
        metadata = yaml.safe_load(fh)
    print("Creating the package itself")
    zipname = metadata['name'] + '.charm'
    zipfh = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)
    buildpath_str = f'{os.getcwd()}/build'  # os.walk does not support pathlib in 3.5
    for dirpath, dirnames, filenames in os.walk(buildpath_str, followlinks=True):
        dirpath = pathlib.Path(dirpath)
        for filename in filenames:
            filepath = dirpath / filename
            zipfh.write(str(filepath), str(filepath.relative_to(buildpath_str)))
    zipfh.close()
    return zipname
if __name__ == "__main__":
    handle_package()
