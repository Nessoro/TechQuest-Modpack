#!/usr/bin/env python3
"""Run a pinned original Pretty Pipes oracle in a new isolated NeoForge world.

Only existing binary inputs are used. Dependencies are not decompiled; their
Java source is not read. No player account or remote service writes are used.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import zipfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from install_isolated_server import fresh_environment
from stage_terralith_content import read_checked
from stage_pretty_pipes import SOURCE


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('runtime','work'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--probe',choices=('redstone','content'),default='redstone')
    parser.add_argument('--cases',type=Path)
    parser.add_argument('--accept-eula',action='store_true')
    args=parser.parse_args();runtime=args.runtime.resolve();work=args.work.absolute()
    if args.probe=='content' and args.cases is None:raise ValueError('content oracle requires --cases')
    if work.exists() or work.is_symlink() or any(p.is_symlink() for p in work.parents) or not args.accept_eula:
        raise ValueError('new work without symlinks and accepted EULA required')
    if work==runtime or runtime in work.parents and work.parent!=runtime:
        raise ValueError('work must be a direct runtime child or separate workspace directory')
    for parent in work.parents:
        if (parent/'level.dat').exists() or (parent/'horizon-resources.json').exists():raise ValueError('work outside worlds/resources required')
    pin=json.loads(read_checked(SOURCE))['modrinth_lock']['XExdLWCQ']
    original=runtime/'pretty-pipes-reference/server/mods'/pin['filename']
    raw=read_checked(original)
    if pin['version']!='1.22.0' or hashlib.sha512(raw).hexdigest()!=pin['sha512']:raise ValueError('Pretty Pipes pin differs')
    libs=runtime/'neoforge-reference/server/libraries'
    named=libs/'net/minecraft/server/1.21.1-20240808.144430/server-1.21.1-20240808.144430-srg.jar'
    if not named.is_file() or not (libs/'net/neoforged/neoforge/21.1.264/unix_args.txt').is_file():raise ValueError('mapped NeoForge binary installation required')
    source=Path(__file__).with_name('PrettyPipesRedstoneProbe.java' if args.probe=='redstone' else 'PrettyPipesInteractionProbe.java')
    classes=work/'probe/classes';classes.mkdir(parents=True,mode=0o700)
    nested=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for name in archive.namelist():
            if name.startswith('META-INF/jarjar/') and name.endswith('.jar'):
                output=work/'binary-dependencies'/Path(name).name
                output.parent.mkdir(exist_ok=True);output.write_bytes(archive.read(name));nested.append(output)
    cp=[named]+[p for p in libs.rglob('*.jar') if p!=named and not any(s in p.name for s in ('-slim','-unpacked'))]+[original,*nested]
    subprocess.run([str(runtime/'jdk25/bin/javac'),'--release','21','-proc:none','-cp',os.pathsep.join(map(str,cp)),'-d',str(classes),str(source)],check=True)
    probe=work/'probe/techquest-reference-probe.jar'
    with zipfile.ZipFile(probe,'x',zipfile.ZIP_DEFLATED) as z:
        for p in classes.rglob('*.class'):z.write(p,p.relative_to(classes))
        z.writestr('META-INF/neoforge.mods.toml','modLoader="javafml"\nloaderVersion="[4,)"\nlicense="MIT"\n[[mods]]\nmodId="techquest_reference_probe"\nversion="0.1"\ndisplayName="TechQuest developer reference probe"\n')
    server=work/'server';server.mkdir();(server/'libraries').symlink_to(libs,target_is_directory=True);(server/'mods').mkdir()
    for p in (original,probe):shutil.copy2(p,server/'mods'/p.name)
    (server/'eula.txt').write_text('eula=true\n')
    for name in ('ops.json','whitelist.json'):(server/name).write_text('[]\n')
    (server/'server.properties').write_text('server-ip=127.0.0.1\nserver-port=25646\nlevel-name=techquest-pretty-pipes-redstone-reference\nlevel-seed=263\nonline-mode=true\nwhite-list=true\nenable-rcon=false\nenable-query=false\nview-distance=4\nsimulation-distance=4\n')
    sha=lambda p:hashlib.sha256(read_checked(p)).hexdigest()
    (work/'inputs.json').write_text(json.dumps({'probe':args.probe,'probe_source_sha256':sha(source),'probe_jar_sha256':sha(probe),'original_jar_sha512':pin['sha512'],'minecraft':'1.21.1','neoforge':'21.1.264','binary_dependencies':{p.name:sha(p) for p in nested}},indent=2)+'\n')
    env=fresh_environment(Path(tempfile.mkdtemp(prefix='reference-homes-',dir=work)))
    launch=[str(runtime/'jdk25/bin/java'),'-Xmx3G','-Djavax.net.ssl.trustStore=/etc/ssl/certs/java/cacerts','-Dtechquest.reference.result='+str(work/'result.json')]
    if args.cases is not None:launch.append('-Dtechquest.reference.crafting_cases='+str(args.cases.resolve()))
    proxy=urllib.parse.urlsplit(env.get('HTTPS_PROXY',''))
    if proxy.hostname:
        for protocol in ('http','https'):launch += [f'-D{protocol}.proxyHost={proxy.hostname}',f'-D{protocol}.proxyPort={proxy.port or 80}']
    launch += ['@libraries/net/neoforged/neoforge/21.1.264/unix_args.txt','nogui']
    with (work/'console.log').open('x') as log:
        (work/'console.log').chmod(0o600)
        subprocess.run(launch,cwd=server,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
    result=json.loads((work/'result.json').read_text())
    if args.probe=='redstone':
        assert result['original_module_and_menu_engines_executed'] and len(result['compatibility'])==66 and len(result['signals'])==48
        print('Original redstone module: 66 menu/compatibility cases and 48 signal/destination/store cases passed')
    else:
        assert len(result['crafting'])==len(json.loads(args.cases.read_text())['cases'])
        print('Original interaction and',len(result['crafting']),'crafting cases passed')


if __name__=='__main__':main()
