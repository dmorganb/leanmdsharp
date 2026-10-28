#!/usr/bin/env python3
"""Build both versions and compare completion/energy checks; not a performance test."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def run(args, cwd, timeout=300):
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=timeout)
    print(result.stdout, flush=True)
    if result.returncode:
        raise RuntimeError('Command failed: ' + repr(args))
    return result.stdout


def main(compiler, charmc):
    compiler = str(compiler.resolve())
    charmc = shutil.which(charmc) or str(Path(charmc).resolve())
    with tempfile.TemporaryDirectory() as temp:
        baseline = Path(temp)
        for name in ['Main.cc', 'Cell.cc', 'Compute.cc', 'Main.h', 'Cell.h', 'Compute.h', 'defs.h', 'physics.h', 'leanmd.ci']:
            shutil.copyfile(ROOT / name, baseline / name)
        run([charmc, '-E', 'leanmd.ci'], baseline)
        for name in ['Main', 'Cell', 'Compute']:
            run([charmc, '-O3', '-c', name + '.cc', '-o', name + '.o'], baseline)
        run([charmc, '-O3', '-module', 'CkMulticast', '-module', 'CommonLBs', '-language', 'charm++', 'Main.o', 'Cell.o', 'Compute.o', '-o', 'leanmd'], baseline)
        run(['make', 'all', 'CHARMSHARP=' + compiler, 'CHARMC=' + charmc], HERE)
        # 5 steps: normal force exchange. 21: particle migration at step 20,
        # plus repeated AtSync/ResumeFromSync. Two PE counts catch routing bugs.
        for pes in [1, 2]:
            if pes > (os.cpu_count() or 1):
                continue
            for steps, first_lb, period in [(5, 100, 100), (21, 3, 3)]:
                args = ['+p' + str(pes), '4', '4', '4', str(steps), str(first_lb), str(period), '+balancer', 'GreedyLB']
                for path in [baseline, HERE / 'build']:
                    log = run([str(path / 'leanmd')] + args, path)
                    if 'SIMULATION SUCCESSFULL' not in log or 'SIMULATION UNSUCCESSFULL' in log:
                        raise AssertionError('Energy conservation failed: ' + str(path))
                    if log.count('Benchmark Time') != steps:
                        raise AssertionError('Wrong number of steps: ' + str(path))
        print('PASS: original and hybrid complete all cases with energy conservation')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--charmc', default='charmc')
    args = parser.parse_args()
    main(args.compiler, args.charmc)
