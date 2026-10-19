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
