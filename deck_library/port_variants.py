"""Per-repository gameplay evidence and conservative grouping of alternative ports.

Catalog scores, package hashes and installation recipes never grant gameplay validation.
All lookups are local; construct one Index per catalog render, not per card.
"""
import json,pathlib,re
from . import validated_games

def version(value):
    value=str(value or '').strip().casefold()
    return value[1:] if value.startswith('v') else value

def groups(path=None):
    path=pathlib.Path(path or pathlib.Path(__file__).resolve().parent.parent/'catalog/port-variants.json')
    value=json.loads(path.read_text());seen=set()
    if value.get('schema_version')!=1 or not isinstance(value.get('groups'),list):raise ValueError('Catálogo de variantes inválido.')
    for group in value['groups']:
        if set(group)!={'id','title','platform','repositories','issues'} or not re.fullmatch(r'[a-z0-9-]{1,80}',group['id']):raise ValueError('Grupo de variantes inválido.')
        for repo in group['repositories']:
            if not isinstance(repo,str) or not re.fullmatch(r'[\w.-]+/[\w.-]+',repo) or repo.casefold() in seen:raise ValueError('Repositorio de variante inválido o repetido.')
            seen.add(repo.casefold())
        for issue in group['issues']:
            if set(issue)!={'repository','versions','description'} or issue['repository'].casefold() not in {r.casefold() for r in group['repositories']} or not issue['versions'] or not all(isinstance(v,str) and v for v in issue['versions']) or not isinstance(issue['description'],str):raise ValueError('Incidencia de variante inválida.')
    return value['groups']

def entry_item(entry):
    return {'repository':entry.metadata.get('port_repository',''),'name':entry.name,'game_title':entry.metadata.get('game_title',''),'list':entry.metadata.get('original_platform',''),'release_version':entry.metadata.get('port_tag') or entry.metadata.get('build') or ''}

class Index:
    def __init__(self,items=(),entries=(),reports=None,families=None):
        from . import ports
        from .originals import key,platform_key
        self.items={i['repository'].casefold():dict(i) for i in items if i.get('repository')}
        for entry in entries:
            item=entry_item(entry)
            if item['repository']:self.items.setdefault(item['repository'].casefold(),item)
        self.reports={};self.issues={};self.family={};self.members={};identities={}
        for report in validated_games.catalog() if reports is None else reports:
            if report['repository']:self.reports.setdefault(report['repository'].casefold(),[]).append(report)
        for group in groups() if families is None else families:
            family=('curated',group['id']);identities[(platform_key(group['platform']),key(group['title']))]=family
            for repo in group['repositories']:
                repo_key=repo.casefold();self.family[repo_key]=family
                self.items.setdefault(repo_key,ports.clean({'repository':repo,'name':group['title'],'game_title':group['title'],'category':group['platform']}))
            for issue in group['issues']:self.issues.setdefault(issue['repository'].casefold(),[]).append(issue)
        for repo,item in self.items.items():
            if repo not in self.family:
                title=key(item.get('game_title',''));platform=platform_key(ports.platform_for(item.get('list','')) or item.get('original_platform',''))
                # A repository/name resemblance alone cannot identify a game or its source platform.
                self.family[repo]=identities.get((platform,title),('title',platform,title)) if title and platform else ('repo',repo)
            self.members.setdefault(self.family[repo],[]).append(item)

    def alternatives(self,item):
        repo=item.get('repository','').casefold();family=self.family.get(repo)
        return sorted((i for i in self.members.get(family,[]) if i['repository'].casefold()!=repo),key=lambda i:(not bool(self.reports.get(i['repository'].casefold())),i['repository'].casefold()))

    def assess(self,item,tag=None):
        repo=item.get('repository','').casefold();tag=str((item.get('release_version','') if tag is None else tag) or '');normalized=version(tag)
        reports=self.reports.get(repo,[]);exact=next((r for r in reports if normalized and normalized==version(r['version'])),None)
        alternative=next((self.reports.get(i['repository'].casefold(),[]) for i in self.alternatives(item) if self.reports.get(i['repository'].casefold())),[])
        result={'state':'unvalidated','label':'Sin validar en Steam Deck','tone':'neutral','report':None,'version':tag or '', 'issue':''}
        for issue in self.issues.get(repo,[]):
            if normalized and normalized in {version(v) for v in issue['versions']}:
                return {**result,'state':'issue','label':'Problema conocido · '+tag,'tone':'red','issue':issue['description'],'report':alternative[-1] if alternative else None}
        if exact:return {**result,'state':'verified','label':'Verificado en Deck','tone':'green','report':exact}
        if reports:
            report=reports[-1]
            return {**result,'state':'different-version' if normalized else 'version-unknown','label':'Versión sin validar' if normalized else 'Prueba disponible · '+report['version'],'tone':'yellow' if normalized else 'blue','report':report}
        if alternative:return {**result,'state':'other-variant','label':'Otra variante sin validar','tone':'yellow','report':alternative[-1]}
        return result

    def installed(self,item,entries):
        family=self.family.get(item.get('repository','').casefold())
        return [e for e in entries if e.metadata.get('port_repository') and self.family.get(e.metadata['port_repository'].casefold())==family and family is not None]
