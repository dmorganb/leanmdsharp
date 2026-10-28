#!/usr/bin/env python3
"""Translation invariants and isolated, executable language-coverage probes."""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path
from assemble import assemble, HERE, ROOT


def tokens(text):
    # Sufficient for these pinned fixtures; keep string contents intact.
    pattern = r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\x27(?:\\.|[^\x27\\])*\x27|[A-Za-z_][A-Za-z_0-9]*|[0-9]+|[^\s]'
    return [t for t in re.findall(pattern, text) if not t.startswith(('//', '/*'))]


def interface(text):
    ts = tokens(text)
    globals_, other = [], []
    i = 0
    while i < len(ts):
        if ts[i] == 'readonly':
            end = ts.index(';', i) + 1
            globals_.append(tuple(ts[i:end]))
            i = end
        else:
            other.append(ts[i])
            i += 1
    return sorted(globals_), other


PROBES = {
    'arrays_3d_6d': ('array [3D] chare Cell { entry: Cell(); };\narray [6D] chare Compute { entry: Compute(); };', None),
    'custom_marshalled_type': ('array [3D] chare Cell { entry: void reduceForces(int n, vec3 forces[n]); };', 'unsupported marshalled array element type'),
    'trailing_array_length': ('array [3D] chare Cell { entry: void reduceForces(double forces[n], int n); };', 'marshalled array bound must name an earlier integer parameter'),
    'variable_message': ('message ParticleDataMsg { public: vec3 part[]; };', 'variable-size message arrays are deferred'),
    'complex_readonly': ('readonly std::string logs;', 'expected readonly Type name;'),
    'migratable_main': ('mainchare [migratable] Main { entry: Main(CkArgMsg* msg); };', 'expected a parallel type name'),
    'chained_receive': ('chare Compute { entry: void run() { when calculateForces(ParticleDataMsg *msg1) when calculateForces(ParticleDataMsg *msg2) { interact(msg1, msg2); } } };', 'expected SDAG receive body'),
    'nested_receive': ('chare Compute { entry: void run() { when calculateForces(ParticleDataMsg *msg1) { when calculateForces(ParticleDataMsg *msg2) { interact(msg1, msg2); } } } };', 'nested SDAG awaits are deferred'),
}


def main(compiler):
    compiler = compiler.resolve()
    manifest = json.loads((HERE / 'upstream-files.json').read_text())
    for name, expected in manifest.items():
        data = (ROOT / name).read_bytes()
        actual = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert actual == expected, 'Original source changed: ' + name
    with tempfile.TemporaryDirectory() as temp:
        out = assemble(compiler, Path(temp) / 'port')
        assert interface((out / 'leanmd.ci').read_text()) == interface((ROOT / 'leanmd.ci').read_text()), 'Interface/SDAG differs from upstream'
        cpp = (out / 'leanmd.cpp').read_text()
        for name in ['Main', 'Cell', 'Compute']:
            assert cpp.count('class ' + name + ' : public CBase_' + name) == 1
            assert cpp.count(name + '_SDAG_CODE') == 1
        assert cpp.count('#include "leanmd.def.h"') == 1
        assert (out / 'physics.h').read_bytes() == (ROOT / 'physics.h').read_bytes()
        results = []
        for name, (source, error) in PROBES.items():
            fixture = Path(temp) / (name + '.csh')
            fixture.write_text(source + '\n')
            result = subprocess.run([str(compiler), '--module', name, '--out-dir', str(Path(temp) / name), str(fixture)], text=True, capture_output=True)
            if error is None:
                assert result.returncode == 0, result.stderr
            else:
                assert result.returncode != 0 and error in result.stderr, name + ': ' + result.stderr
            results.append({'probe': name, 'accepted': result.returncode == 0, 'diagnostic': result.stderr.strip()})
        print(json.dumps(results, indent=2))
    print('PASS: 12 original files unchanged; interface and SDAG token-equivalent; 8 coverage probes')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', type=Path, required=True)
    main(parser.parse_args().compiler)
