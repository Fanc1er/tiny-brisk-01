# brisk-sparrow-87 tiny-chess-01 engine (MIT): mailbox-120 board, incremental
# zobrist, alpha-beta with quiescence, killers, null-move, LMR; fixed node cap
# per move (no clock) so every trial replays byte for byte.
import json, os, sys, urllib.request

ENV_URL = os.environ.get("MAKEFUN_ENV_URL") or sys.exit("MAKEFUN_ENV_URL is not set")
NC = 150000
KL = {}
LO = -30000
ND = [0]
TT = {}
TC = 900000

EMPTY, OFF = 0, 7
VAL = (0, 100, 320, 330, 500, 900, 20000)

def table(rows):
    out = [0]*120
    for r in range(8):
        for f in range(8):
            out[21 + r*10 + f] = rows[r][f]
    return out

P_PST = table([
 [0]*8,
 [50]*8,
 [10, 10, 20, 30, 30, 20, 10, 10],
 [ 5,  5, 10, 25, 25, 10,  5,  5],
 [ 0,  0,  0, 20, 20,  0,  0,  0],
 [ 5, -5,-10,  0,  0,-10, -5,  5],
 [ 5, 10, 10,-20,-20, 10, 10,  5],
 [0]*8])
N_PST = table([
 [-50,-40,-30,-30,-30,-30,-40,-50],
 [-40,-20,  0,  0,  0,  0,-20,-40],
 [-30,  0, 10, 15, 15, 10,  0,-30],
 [-30,  5, 15, 20, 20, 15,  5,-30],
 [-30,  0, 15, 20, 20, 15,  0,-30],
 [-30,  5, 10, 15, 15, 10,  5,-30],
 [-40,-20,  0,  5,  5,  0,-20,-40],
 [-50,-40,-30,-30,-30,-30,-40,-50]])
B_PST = table([
 [-20,-10,-10,-10,-10,-10,-10,-20],
 [-10,  0,  0,  0,  0,  0,  0,-10],
 [-10,  0,  5, 10, 10,  5,  0,-10],
 [-10,  5,  5, 10, 10,  5,  5,-10],
 [-10,  0, 10, 10, 10, 10,  0,-10],
 [-10, 10, 10, 10, 10, 10, 10,-10],
 [-10,  5,  0,  0,  0,  0,  5,-10],
 [-20,-10,-10,-10,-10,-10,-10,-20]])
R_PST = table([
 [ 0,  0,  0,  5,  5,  0,  0,  0],
 [ 5, 10, 10, 10, 10, 10, 10,  5]] +
 [[-5,  0,  0,  0,  0,  0,  0, -5]]*5 +
 [[ 0,  0,  5, 10, 10,  5,  0,  0]])
Q_PST = table([
 [-20,-10,-10, -5, -5,-10,-10,-20],
 [-10,  0,  0,  0,  0,  0,  0,-10],
 [-10,  0,  5,  5,  5,  5,  0,-10],
 [ -5,  0,  5,  5,  5,  5,  0, -5],
 [  0,  0,  5,  5,  5,  5,  0, -5],
 [-10,  5,  5,  5,  5,  5,  0,-10],
 [-10,  0,  5,  0,  0,  0,  0,-10],
 [-20,-10,-10, -5, -5,-10,-10,-20]])
K_PST = table([
 [-30,-40,-40,-50,-50,-40,-40,-30]]*4 + [
 [-20,-30,-30,-40,-40,-30,-30,-20],
 [-10,-20,-20,-20,-20,-20,-20,-10],
 [ 20, 20,  0,  0,  0,  0, 20, 20],
 [ 20, 30, 10,  0,  0, 10, 30, 20]])

PST = (None, P_PST, N_PST, B_PST, R_PST, Q_PST, K_PST)

N_OFF = (-21,-19,-12,-8,8,12,19,21)
B_DIR = (-11,-9,9,11)
R_DIR = (-10,-1,1,10)
K_DIR = (-11,-10,-9,-1,1,9,10,11)

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

def mt(s, p):
    return s + p if s > 25000 else s - p if s < -25000 else s

def ck(st):
    return hash((tuple(st.b), st.side, st.cast, st.ep))

class State:
    __slots__ = ("b","side","cast","ep","half","hist","key","keys")

def gen_moves(st, caps_only=False):
    b, side = st.b, st.side
    mv = []
    ap = mv.append
    for i in range(21, 99):
        p = b[i]
        if p == EMPTY or p == OFF: continue
        if (p > 0) != (side > 0): continue
        a = p if p > 0 else -p
        if a == 1:
            d = i - 10*side
            pr1 = d <= 28 if side > 0 else d >= 91
            if not caps_only and b[d] == EMPTY:
                if pr1:
                    mv += [(i,d,5),(i,d,2),(i,d,4),(i,d,3)]
                else:
                    ap((i,d,0))
                if (side > 0 and 81 <= i <= 88 and b[i-20] == EMPTY) or \
                   (side < 0 and 31 <= i <= 38 and b[i+20] == EMPTY):
                    ap((i, i-20*side, 0))
            for dd in (-1, 1):
                t = d + dd
                q = b[t]
                if q and q != OFF and (q > 0) != (side > 0) and abs(q) != 6:
                    if side > 0 and t <= 28 or side < 0 and t >= 91:
                        mv += [(i,t,5),(i,t,2),(i,t,4),(i,t,3)]
                    else:
                        ap((i,t,0))
            if st.ep in (d-1, d+1) and not caps_only:
                    ap((i, st.ep, 0))
        elif a == 2 or a == 6:
            for o in (N_OFF if a == 2 else K_DIR):
                t = i + o
                q = b[t]
                if q == OFF: continue
                if q == EMPTY:
                    if not caps_only: ap((i,t,0))
                elif (q > 0) != (side > 0) and abs(q) != 6:
                    ap((i,t,0))
            if a == 6 and not caps_only:
                for rt, kf, d, qs in ((1,95,1,0),(2,95,-1,1),(4,25,1,0),(8,25,-1,1)):
                    if st.cast & rt and i == kf and b[kf+d]==EMPTY and b[kf+2*d]==EMPTY \
                       and (qs == 0 or b[kf+3*d]==EMPTY) and not attacked(st,kf,-side) \
                       and not attacked(st,kf+d,-side) and not attacked(st,kf+2*d,-side):
                        ap((i,kf+2*d,0))
        else:
            dirs = B_DIR if a == 3 else R_DIR if a == 4 else K_DIR
            for o in dirs:
                t = i + o
                while True:
                    q = b[t]
                    if q == OFF: break
                    if q == EMPTY:
                        if not caps_only: ap((i,t,0))
                    else:
                        if (q > 0) != (side > 0) and abs(q) != 6: ap((i,t,0))
                        break
                    t += o
    return mv

def attacked(st, sq, by):
    b = st.b
    d = sq + 10*by
    if b[d-1] == by or b[d+1] == by: return True
    for o in N_OFF:
        if b[sq+o] == 2*by: return True
    for o in B_DIR:
        t = sq + o
        while b[t] == EMPTY: t += o
        q = b[t]
        if q != OFF and (q == 3*by or q == 5*by): return True
    for o in R_DIR:
        t = sq + o
        while b[t] == EMPTY: t += o
        q = b[t]
        if q != OFF and (q == 4*by or q == 5*by): return True
    for o in K_DIR:
        if b[sq+o] == 6*by: return True
    return False

def king_sq(st, side):
    b = st.b
    k = 6*side
    for i in range(21, 99):
        if b[i] == k: return i
    return 0

CM = {98:~1, 91:~2, 28:~4, 21:~8, 95:~3, 25:~12}

def make(st, m):
    i, t, pr = m
    b = st.b
    p = b[i]
    capd = b[t]
    st.hist.append((m, capd, st.cast, st.ep, st.half, 0, 0))
    st.ep = 0
    st.half += 1
    a = abs(p)
    if capd or a == 1: st.half = 0
    if pr: b[t] = pr*st.side
    else: b[t] = p
    b[i] = EMPTY
    if a == 1:
        if t-i == 20 or i-t == 20: st.ep = (i+t)//2
        elif capd == 0 and abs(t-i) in (9, 11):
            cs = t + 10*st.side
            h = st.hist[-1]
            st.hist[-1] = (m, 0, h[2], h[3], h[4], cs, b[cs])
            b[cs] = EMPTY
    elif a == 6:
        if t == i+2: b[i+1], b[t+1] = b[t+1], EMPTY
        elif t == i-2: b[i-1], b[t-2] = b[t-2], EMPTY
    st.cast &= CM.get(i, -1) & CM.get(t, -1)
    st.side = -st.side
    st.key = ck(st)
    st.keys.append(st.key)

def unmake(st):
    m, capd, cast, ep, half, epsq, capp = st.hist.pop()
    i, t, pr = m
    st.side = -st.side
    st.keys.pop()
    b = st.b
    p = b[t]
    if pr: p = st.side
    b[i] = p
    if epsq:
        b[epsq] = capp; b[t] = EMPTY
    else:
        b[t] = capd
    a = abs(p)
    if a == 6:
        if t == i+2: b[t+1], b[i+1] = b[i+1], EMPTY
        elif t == i-2: b[t-2], b[i-1] = b[i-1], EMPTY
    st.cast, st.ep, st.half = cast, ep, half
    st.key = st.keys[-1]

def evaluate(st):
    b = st.b
    score = 0
    wb = bb = 0
    for i in range(21, 99):
        p = b[i]
        if 0 < p < 7:
            score += VAL[p] + PST[p][i]
            if p == 3: wb += 1
        elif p < 0:
            q = -p
            score -= VAL[q] + PST[q][112 - i + 2*((i-21) % 10)]
            if q == 3: bb += 1
    if wb > 1: score += 30
    if bb > 1: score -= 30
    return score * st.side

def quies(st, alpha, beta):
    ND[0] += 1
    incheck = attacked(st, king_sq(st, st.side), -st.side)
    moves = gen_moves(st, not incheck)
    if not incheck:
        stand = evaluate(st)
        if stand >= beta: return stand
        if stand > alpha: alpha = stand
    elif not moves: return -29000
    moves.sort(key=lambda m: -abs(st.b[m[1]]))
    for m in moves:
        make(st, m)
        if attacked(st, king_sq(st, -st.side), st.side):
            unmake(st); continue
        sc = -quies(st, -beta, -alpha)
        unmake(st)
        if sc >= beta: return sc
        if sc > alpha: alpha = sc
    return alpha

def search(st, depth, alpha, beta, ply):
    if ND[0] >= NC:
        return evaluate(st)
    ND[0] += 1
    incheck = attacked(st, king_sq(st, st.side), -st.side)
    if incheck and depth < 20: depth += 1
    if depth <= 0:
        return quies(st, alpha, beta)
    if st.half >= 100 or st.keys.count(st.key) >= 2:
        return 0
    a0, b0 = alpha, beta
    e = TT.get(st.key)
    tmove = e[3] if e else None
    moves = gen_moves(st)
    if not incheck and depth >= 3 and ply > 0:
        npm = 0
        for p in st.b:
            if 1 < abs(p) < 6 and (p > 0) == (st.side > 0):
                npm += 1
                if npm > 2: break
        if npm > 2:
            st.ep = 0
            st.side = -st.side
            sc = -search(st, depth - 3, -beta, -beta + 1, ply + 1)
            st.side = -st.side
            if sc >= beta:
                return sc
    scored = []
    for m in moves:
        q = st.b[m[1]]
        s = 0
        if 0 < q < 7:
            s = 1000 + 10*VAL[abs(q)] - VAL[abs(st.b[m[0]])]
        elif m[2]:
            s = 900
        elif m == tmove:
            s = 5000
        elif m in KL.get(ply, (0, 1)):
            s = 800
        scored.append((s, m))
    scored.sort(reverse=True)
    best = LO
    bm = None
    first = True
    for _, m in scored:
        make(st, m)
        if attacked(st, king_sq(st, -st.side), st.side):
            unmake(st); continue
        if first:
            sc = -search(st, depth-1, -beta, -alpha, ply+1)
            first = False
        else:
            sc = -search(st, depth-1, -alpha-1, -alpha, ply+1)
            if alpha < sc < beta:
                sc = -search(st, depth-1, -beta, -alpha, ply+1)
        unmake(st)
        if sc > best:
            best = sc
            bm = m
            if sc > alpha:
                alpha = sc
                if alpha >= beta:
                    if st.b[m[1]] == EMPTY and m[2] == 0:
                        kl = KL.setdefault(ply, [None, None])
                        if kl[0] != m:
                            kl[1] = kl[0]; kl[0] = m
                    TT[st.key] = (depth, 1, mt(best, ply), m)
                    return best
    if best == LO:
        return -29000 + ply if incheck else 0
    if len(TT) < TC:
        TT[st.key] = (depth, 0 if a0 < best < b0 else (2 if best <= a0 else 1), mt(best, ply), bm)
    return best

FENMAP = {"p":1,"n":2,"b":3,"r":4,"q":5,"k":6}

def from_fen(fen):
    st = State.__new__(State)
    st.b = [OFF]*120
    for r in range(2, 10):
        for f in range(1, 9):
            st.b[r*10+f] = EMPTY
    parts = fen.split()
    for r, row in enumerate(parts[0].split("/")):
        f = 0
        for c in row:
            if c.isdigit(): f += int(c)
            else:
                st.b[21+r*10+f] = FENMAP[c.lower()]*(-1 if c.islower() else 1)
                f += 1
    st.side = 1 if parts[1] == "w" else -1
    cs = parts[2]
    st.cast = sum(rt for c, rt in zip("KQkq", (1, 2, 4, 8)) if c in cs)
    st.ep = 0
    if parts[3] != "-":
        st.ep = sq(parts[3][0], int(parts[3][1]))
    st.half = int(parts[4])
    st.hist = []
    st.keys = [ck(st)]
    st.key = st.keys[0]
    return st

def sq(f, r):
    return 21 + (8 - r)*10 + "abcdefgh".index(f)

def to_uci(m):
    a = m[0] - 21; q = m[1] - 21
    return "abcdefgh"[a % 10] + str(8 - a // 10) + "abcdefgh"[q % 10] + str(8 - q // 10) + ("  nbrq"[m[2]] if m[2] else "")

def pick(fen, moves_uci, legal_uci):
    st = from_fen(fen)
    for u in moves_uci:
        make(st, (sq(u[0], int(u[1])), sq(u[2], int(u[3])), ("?nbrq".index(u[4])) if len(u) > 4 else 0))
    legal = legal_uci
    ND[0] = 0
    l0 = best_u = legal_uci[0]
    for depth in range(1, 30):
        sc = search(st, depth, LO, -LO, 0)
        if ND[0] >= NC: break
        e = TT.get(st.key)
        if e:
            u = to_uci(e[3])
            if u in legal: best_u = u
    return best_u if best_u in legal else l0

def post(path, body):
    req = urllib.request.Request(ENV_URL + path, data=json.dumps(body).encode(),
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req) as res:
        return json.load(res)

def main():
    while True:
        g = post("/game", {})
        while g.get("status") == "your_move":
            g = post("/move", {"game": g["game"], "move": pick(g["start_fen"], g["moves"], g["legal_moves"])})
        if g.get("status") == "done": return

main()
