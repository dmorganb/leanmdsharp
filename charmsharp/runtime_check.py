#!/usr/bin/env python3
"""Build both versions and compare completion/energy checks; not a performance test."""
import argparse
import os
import json
import re
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
    results = []
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
                    variant = 'original' if path == baseline else 'hybrid'
                    (HERE / 'build' / (variant + '-p' + str(pes) + '-steps' + str(steps) + '.log')).write_text(log)
                    results.append({'variant': variant, 'pes': pes, 'steps': steps,
                                    'energy_conservation': True, 'step_count': True})
        print('PASS: original and hybrid complete all cases with energy conservation')
        # The short application runs do not touch logs: independently exercise
        # a non-empty readonly string on both PEs and compare a handwritten .ci.
        fixture = HERE / 'build' / 'readonly-check'
        fixture.mkdir(exist_ok=True)
        run([compiler, '--force', '--module', 'ReadonlyAlias', '--out-dir', str(fixture),
             str(HERE / 'fixtures' / 'readonly_alias.csh')], HERE)
        shutil.copyfile(HERE / 'fixtures' / 'readonly_reference.ci', fixture / 'ReadonlyReference.ci')
        shutil.copyfile(HERE / 'fixtures' / 'readonly_reference.C', fixture / 'ReadonlyReference.C')
        run([charmc, 'ReadonlyReference.ci'], fixture)
        run([charmc, 'ReadonlyReference.C', '-o', 'reference'], fixture)
        run([charmc, 'ReadonlyAlias.ci'], fixture)
        run([charmc, '-I' + str(HERE / 'build'), '-include', str(HERE / 'build' / 'compat_types.h'),
             'ReadonlyAlias.cpp', '-o', 'alias'], fixture)
        for pes in [1, 2]:
            if pes > (os.cpu_count() or 1):
                continue
            observations = []
            for variant in ['reference', 'alias']:
                log = run([str(fixture / variant), '+p' + str(pes)], fixture)
                received = sorted((int(i), int(pe)) for i, pe in
                                  re.findall(r'READONLY_OK index=(\d+) pe=(\d+)', log))
                assert [i for i, pe in received] == [0, 1], log
                assert {pe for i, pe in received} == set(range(pes)), log
                assert log.count('READONLY_DONE') == 1, log
                observations.append(received)
                (HERE / 'build' / ('readonly-' + variant + '-p' + str(pes) + '.log')).write_text(log)
            assert observations[0] == observations[1], observations
            results.append({'fixture': 'readonly_alias', 'pes': pes, 'broadcast_matches_reference': True})
        print('PASS: non-empty readonly alias broadcast matches std::string reference')
    (HERE / 'build' / 'runtime-results.json').write_text(json.dumps(results, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--compiler', type=Path, required=True)
    parser.add_argument('--charmc', default='charmc')
    args = parser.parse_args()
    main(args.compiler, args.charmc)
