#!/usr/bin/env python3
"""LeanMD-specific integration adapter, not a general Charm# migration tool."""
import argparse
import re
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def assemble(compiler, output):
    output.mkdir(parents=True, exist_ok=True)
    raw = output / 'raw'
    subprocess.run([str(compiler.resolve()), '--force', '--module', 'leanmd',
                    '--out-dir', str(raw), str(HERE / 'leanmd.csh')], check=True)
    generated = (raw / 'leanmd.ci').read_text()
    template = (HERE / 'legacy.ci.in').read_text()
    readonly = re.findall(r'^\s*(readonly [^;]+;)', generated, re.M)
    if len(readonly) != 13:
        raise ValueError('Expected exactly 13 migrated readonly declarations')
    template = template.replace('@READONLY@', '\n  '.join(readonly))
    for name, count in [('Main', 1), ('Cell', 2), ('Compute', 1)]:
        match = re.search(r'(mainchare|array \[\d+D\]) ' + name +
                          r' \{([^{}]*)\};', generated)
        if not match:
            raise ValueError('Unexpected generated interface for ' + name)
        entries = re.findall(r'entry [^;]+;', match[2])
        if len(entries) != count:
            raise ValueError('Unexpected entry count for ' + name)
        template = template.replace('@' + name.upper() + '_KIND@', match[1])
        template = template.replace('@' + name.upper() + '_ENTRIES@', '\n    '.join(entries))
    if re.search(r'@[A-Z_]+@', template):
        raise ValueError('Unresolved interface template marker')
    (output / 'leanmd.ci').write_text(template)
    shutil.copyfile(raw / 'leanmd.cpp', output / 'leanmd.cpp')

    # Charm# prepends .decl.h before user includes. Force these value types in
    # before it, without importing the original interface/extern declarations.
    definitions = (ROOT / 'defs.h').read_text()
    types, rest = definitions.split('#include "leanmd.decl.h"', 1)
    (output / 'types.h').write_text('#include <cmath>\n#include <string>\n#include <vector>\n' + types + '\n#endif\n')
    shutil.copyfile(HERE / 'compat_types.h', output / 'compat_types.h')
    shutil.copyfile(ROOT / 'physics.h', output / 'physics.h')
    # physics.h still includes defs.h. Its original guard is already set by
    # force-included types.h, but the header must exist for include lookup.
    shutil.copyfile(ROOT / 'defs.h', output / 'defs.h')
    for name in ['Main', 'Cell', 'Compute']:
        source = (ROOT / (name + '.cc')).read_text()
        # Remove only includes supplied by the single generated translation unit.
        source = re.sub(r'^#include "(?:defs.h|Main.h|Cell.h|Compute.h|leanmd.decl.h|leanmd.def.h)"\s*$', '', source, flags=re.M)
        if name == 'Main':
            source, count = re.subn(r'^/\* readonly \*/[^\n]+\n', '', source, flags=re.M)
            if count != 13:
                raise ValueError('Expected 13 original readonly definitions')
        (output / (name + '.inc')).write_text(source)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', required=True, type=Path)
    parser.add_argument('--output', type=Path, default=HERE / 'build')
    args = parser.parse_args()
    assemble(args.compiler, args.output.resolve())
