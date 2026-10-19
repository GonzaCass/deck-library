#!/usr/bin/env python3
import argparse,json,os,sys
from deck_library.models import Store

def main():
    parser=argparse.ArgumentParser(description='Deck Library — ports y juegos emulados, juntos en Steam')
    parser.add_argument('--gaming',action='store_true',help='Abrir a pantalla completa desde Steam')
    sub=parser.add_subparsers(dest='action')
    for name in ('scan','sync','launch','check'):
        p=sub.add_parser(name)
        if name in ('launch','check'):p.add_argument('id')
        p.add_argument('--data-dir')
        if name=='sync':p.add_argument('--no-wait',action='store_true')
    args=parser.parse_args()
    if not args.action:
        # Steam shortcuts can call app.py directly instead of launch.sh.
        if os.environ.get('DISPLAY'):os.environ.setdefault('GDK_BACKEND','x11')
        from deck_library.gui import run
        run();return 0
    store=Store(args.data_dir)
    if args.action=='scan':
        from deck_library.discovery import scan
        print(json.dumps([e.to_dict() for e in scan()],indent=2,ensure_ascii=False));return 0
    if args.action=='sync':
        from deck_library.service import sync
        print(json.dumps(sync(store,wait=not args.no_wait)));return 0
    entry=next((e for e in store.load() if e.id==args.id),None)
    if entry is None:raise ValueError('El juego ya no está en la biblioteca. Volvé a agregarlo desde Deck Library.')
    if args.action=='check':
        from deck_library.runtime import diagnostics
        issues,log=diagnostics(entry,store);print(json.dumps({'issues':issues,'log':log},ensure_ascii=False,indent=2));return int(bool(issues))
    from deck_library.runtime import launch
    return launch(entry,store)

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as error:
        if len(sys.argv)>1 and sys.argv[1]=='launch':
            from deck_library.runtime import show_error
            show_error(str(error))
        print('Deck Library:',error,file=sys.stderr);sys.exit(1)
