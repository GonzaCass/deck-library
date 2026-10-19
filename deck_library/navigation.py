"""Directional navigation through allocated card rectangles."""
def neighbour(rectangles,current,direction):
    if current not in rectangles:return next(iter(rectangles),None)
    x,y,w,h=rectangles[current];cx,cy=x+w/2,y+h/2;candidates=[]
    horizontal=direction in ('left','right');sign=-1 if direction in ('left','up') else 1
    for key,(tx,ty,tw,th) in rectangles.items():
        if key==current:continue
        dx,dy=tx+tw/2-cx,ty+th/2-cy
        along=dx if horizontal else dy;across=dy if horizontal else dx
        if along*sign<=1:continue
        # Horizontal movement stays on the row, including at its last card.
        if horizontal and abs(dy)>=(h+th)/2:continue
        candidates.append((abs(along),abs(across),key))
    return min(candidates)[2] if candidates else None

def control_neighbour(rectangles,current,direction):
    """Move between mixed-size controls, favouring the current row/column."""
    if current not in rectangles:return next(iter(rectangles),None)
    x,y,w,h=rectangles[current];cx,cy=x+w/2,y+h/2
    horizontal=direction in ('left','right');sign=-1 if direction in ('left','up') else 1;candidates=[]
    for key,(tx,ty,tw,th) in rectangles.items():
        if key==current:continue
        dx,dy=tx+tw/2-cx,ty+th/2-cy
        along=dx if horizontal else dy
        if along*sign<=1:continue
        overlap=min(y+h,ty+th)-max(y,ty) if horizontal else min(x+w,tx+tw)-max(x,tx)
        gap=max(0,abs(along)-(w+tw)/2 if horizontal else abs(along)-(h+th)/2)
        across=max(0,abs(dy)-(h+th)/2 if horizontal else abs(dx)-(w+tw)/2)
        candidates.append((overlap<=0,gap*gap+across*across*2,abs(along),key))
    return min(candidates)[3] if candidates else None
