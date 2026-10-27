#!/usr/bin/env python3
"""Audit public release metadata without installing or running ports."""
import argparse,collections,concurrent.futures,datetime,json,pathlib,re,shutil,subprocess,sys,urllib.error

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent))
from deck_library import ports
from deck_library.port_recipes import preparation

def inspect(item,get=ports.fetch_json):
    item=ports.clean(item);repo=item['repository']
    row={'repository':repo,'name':item.get('game_title') or item['name'],'preparation':preparation(item)[0]}
    if item.get('web') or item.get('setup')=='project2099':
        return {**row,'status':'specialized','note':'Uses a dedicated installation flow.'}
    try:
        release=ports.release_for(repo,get)
        row.update(tag=release.get('tag_name',''),published_at=release.get('published_at',''),assets=[a['name'] for a in release.get('assets',[])])
        plan=ports.package_plan(item,release.get('assets',[]))
        if item.get('package_role') in ('source-only','build-tool'):
            row.update(status='manual-build',note=item['source_note'])
        elif plan:
            row.update(status={'linux':'native','proton':'proton','detect':'inspect-archive'}[plan['runtime']],asset=plan['asset']['name'],package=plan['kind'])
        else:row.update(status='no-compatible-package',note='No supported portable Linux/Windows asset in the selected release.')
    except (OSError,ValueError,KeyError) as error:
        status='no-release' if 'no tiene versiones publicadas' in str(error) else 'unavailable' if isinstance(error,urllib.error.HTTPError) and error.code==404 else 'request-failed'
        row.update(status=status,note='No published release.' if status=='no-release' else 'Repository unavailable.' if status=='unavailable' else 'Metadata request failed; compatibility is unknown.')
    return row

def github_cli(url):
    """Use the caller's gh session; never read, print or persist its token."""
    if not url.startswith('https://api.github.com/'):return ports.fetch_json(url)
    try:result=subprocess.run([shutil.which('gh') or 'gh','api',url.removeprefix('https://api.github.com/')],capture_output=True,text=True,timeout=45)
    except subprocess.TimeoutExpired:raise OSError('GitHub CLI request timed out.') from None
    if result.returncode:
        match=re.search(r'HTTP (\d{3})',result.stderr)
        if match:raise urllib.error.HTTPError(url,int(match[1]),'GitHub request failed',{},None)
        raise OSError('GitHub CLI request failed.')
    return json.loads(result.stdout)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog',type=pathlib.Path,default=pathlib.Path(__file__).resolve().parent.parent/'catalog/ports.json')
    parser.add_argument('--refresh',action='store_true',help='Read current public catalogs instead of a local snapshot.')
    parser.add_argument('--github-cli',action='store_true',help='Use the existing gh login for GitHub API requests.')
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--output',type=pathlib.Path,required=True)
    args=parser.parse_args();get=github_cli if args.github_cli else ports.fetch_json
    data=None if args.refresh else json.loads(args.catalog.read_text())
    items=ports.fetch_catalog(get) if args.refresh else data.get('apps',[]) if isinstance(data,dict) else data
    items=ports.merged([i for i in items if ports.clean(i)])
    rows=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(args.workers,4))) as pool:
        for index,row in enumerate(pool.map(lambda item:inspect(item,get),items),1):
            rows.append(row)
            if index%25==0:print(f'{index}/{len(items)}',flush=True)
    report={'schema':1,'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Release metadata only. No gameplay or ROM verification. A portable package is not a guarantee of Proton compatibility.','summary':dict(collections.Counter(r['status'] for r in rows)),'ports':sorted(rows,key=lambda r:r['repository'].lower())}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report['summary'],ensure_ascii=False))

if __name__=='__main__':main()
