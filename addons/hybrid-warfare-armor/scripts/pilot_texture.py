"""Hand-crafted 64x32 Minecraft armor UV atlas for the experimental
Superb Warfare 6B47 + 6B43 / Mekanism hybrid. All pixel artwork original.
"""
W,H=64,32
OLIVE=(71,82,65,255)
OLIVE2=(89,101,78,255)
ARMOR=(45,52,47,255)
ARMORLIGHT=(111,119,104,255)
DARK=(26,33,36,255)
SHADOW=(38,45,41,255)
STRAP=(141,136,96,255)
CYAN=(57,203,230,255)
GLOW=(159,248,247,255)

def texture(part):
    img=[(0,0,0,0)]*(W*H)
    def px(x,y,c):
        if 0 <= x < W and 0 <= y < H: img[y*W+x]=c
    def rect(x,y,w,h,c):
        for yy in range(y,y+h):
            for xx in range(x,x+w): px(xx,yy,c)
    def face(x,y,w,h,base):
        rect(x,y,w,h,base)
        for xx in range(x,x+w):
            px(xx,y,ARMORLIGHT); px(xx,y+h-1,SHADOW)
        for yy in range(y,y+h):
            px(x,yy,DARK); px(x+w-1,yy,SHADOW)
        if w>3 and h>3:
            px(x+1,y+1,OLIVE2)
            if w>5: px(x+w-2,y+2,OLIVE2)
    if part=="helmet":
        for f in [(8,0,8,8),(16,0,8,8),(0,8,8,8),(8,8,8,8),
                  (16,8,8,8),(24,8,8,8)]:
            face(*f,OLIVE)
        rect(9,2,6,2,ARMOR);rect(10,3,4,1,OLIVE2)
        for x in (8,16,24,0):
            rect(x+1,10,6,1,STRAP)
            rect(x+1,12,6,2,ARMOR)
        rect(9,9,6,1,ARMORLIGHT)
        rect(9,11,6,2,DARK)
        rect(9,11,2,1,CYAN);rect(13,11,2,1,CYAN)
        px(10,11,GLOW);px(14,11,GLOW)
        rect(8,13,2,2,ARMOR);rect(14,13,2,2,ARMOR)
        px(14,9,CYAN);px(14,8,ARMORLIGHT)
        rect(1,10,2,3,ARMOR);px(2,11,CYAN)
        rect(17,10,2,3,ARMOR);px(18,11,CYAN)
        rect(25,11,6,1,SHADOW)
    elif part=="vest":
        for f in [(20,16,8,4),(28,16,8,4),(16,20,4,12),(20,20,8,12),
                  (28,20,4,12),(32,20,8,12),(44,16,4,4),(48,16,4,4),
                  (40,20,4,12),(44,20,4,12),(48,20,4,12),(52,20,4,12)]:
            face(*f,OLIVE)
        rect(20,20,2,7,DARK);rect(26,20,2,7,DARK)
        rect(21,23,6,6,ARMOR);rect(22,24,4,4,SHADOW)
        rect(23,24,2,1,ARMORLIGHT)
        rect(23,26,2,2,CYAN);px(23,26,GLOW)
        rect(21,29,6,2,STRAP)
        for x in (21,23,25):rect(x,29,1,2,OLIVE2)
        rect(22,21,4,1,STRAP)
        rect(33,22,6,8,ARMOR);rect(34,24,4,2,SHADOW)
        rect(35,25,2,1,CYAN);rect(34,28,4,1,STRAP)
        for x in (40,44,48,52):
            rect(x,22,4,3,ARMOR)
            rect(x+1,26,2,3,STRAP)
            rect(x+1,30,2,1,CYAN)
        rect(22,17,4,1,ARMOR);rect(30,17,4,1,ARMOR)
    else:raise ValueError(part)
    return img
