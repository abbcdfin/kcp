#!/usr/bin/python

import os.path
import argparse
import glob
import tempfile
import subprocess
import logging
import shutil
import fileinput
import re
import sys

#
parser = argparse.ArgumentParser(description='Kernel configuration pruner')
parser.add_argument('--kernel-src', '-k', dest='kernel_source_path',
 action='store')
parser
args = parser.parse_args()

logging.basicConfig(level=logging.INFO)

# Check running environment


# Concatenate kernel Makefile together and store as a tmp file, which will be
# checked to find the module related kernel configuration.
kernel_makefiles = tempfile.TemporaryFile(mode='w+t')
makefile_list = glob.glob(os.path.join(args.kernel_source_path, "**/Makefile"),
                          recursive=True)
logging.debug(makefile_list)
for file in makefile_list:
    fo = open(file, mode='r+t')
    shutil.copyfileobj(fo, kernel_makefiles)
kernel_makefiles.seek(0)
    
# Check loaded module to gether all the required modules in kernel
# configuration.
cp = subprocess.run(["lsmod"], stdout=subprocess.PIPE)
loaded_module_list = cp.stdout

loaded_modules=[]
for i in loaded_module_list.split(b'\n'):
    m = re.search('^(\w*)\s*\d+.*', i.decode('utf-8'))
    if m:
        loaded_modules.append(m.group(1))

# Generate the required configurations from the loaded module
modules_configuration = []
for module in loaded_modules:
    module_search = module.replace('_', '\$')
    module_search = module_search.replace('-', '\$')
    module_search = module_search.replace('\$', '(_|-)')
    module_search = module_search + '.o'
    found = 0

    for l in kernel_makefiles:
        m = re.search('obj-\$\((\w*)\)\s*(\+|\:)\=.*' + module_search, l)
        if m:
            modules_configuration.append(m.group(1))
            found = 1
            break

    kernel_makefiles.seek(0)
    if found == 0: 
        logging.info("failed finding configuration for module %s" % (
            module_search))

# Get the running kernel configuration from the proc filesystem,
# process line by line to remove all the unloaded module line.
subprocess.run(["7z", "x", "-y", "-o/tmp", "/proc/config.gz"])

running_config_fo = open("/tmp/config")
pruned_config_fo = open("/tmp/config_pruned", "w+")
pruned_config_fo.seek(0)
pruned_config_fo.truncate()

ignored_module_cnt = 0
for line in running_config_fo.readlines():
    m = re.search('(CONFIG_\w*)\=m', line)
    if not m:
        pruned_config_fo.write(line)
        continue

    used = 0
    for k in modules_configuration:
        if m.group(1) == k:
            used = 1
            break

    if used:
        pruned_config_fo.write(line)
    else:
        ignored_module_cnt += 1

pruned_config_fo.close()
print("%d modules ignored" % (ignored_module_cnt))
    
        
    
