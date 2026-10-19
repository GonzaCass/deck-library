"""Structured transfer progress; percentages and ETA describe measured download bytes."""
import time

class Progress:
    def __init__(self):
        self.started=None
        self.state={'phase':'preparing','text':'Preparando…','fraction':None,'eta':None,'done':0,'total':0}

    def update(self,event,now=None):
        now=time.monotonic() if now is None else now
        if isinstance(event,str):
            self.state.update(phase='working',text=event,fraction=None,eta=None)
            return dict(self.state)
        if event.get('phase')=='download':
            done,total=max(0,event.get('done',0)),max(0,event.get('total',0))
            if self.started is None:self.started=now
            elapsed=now-self.started
            speed=done/elapsed if elapsed>=1 and done else 0
            self.state.update(phase='download',text='Descargando',done=done,total=total,fraction=min(1,done/total) if total else None,eta=max(0,(total-done)/speed) if total and speed else None)
        else:self.state.update(event)
        return dict(self.state)

def caption(state):
    if state['phase']!='download':return state.get('text','Preparando…')
    done,total=state.get('done',0),state.get('total',0)
    amount=f'{done/(1<<20):.1f} MB'+(f' de {total/(1<<20):.1f} MB' if total else '')
    percent=f'{state["fraction"]*100:.0f}% · ' if state.get('fraction') is not None else ''
    eta=state.get('eta')
    remaining=(f'{int(eta)//60} min {int(eta)%60:02d} s restantes' if eta is not None else 'Calculando tiempo restante')
    return percent+amount+' · '+remaining
