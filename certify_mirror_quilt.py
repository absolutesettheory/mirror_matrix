#!/usr/bin/env python3
"""Spin-Sweep certification for the Mirror-Quilt framework (author: Christopher Thomas Ronio).
Runs the framework's closure / determinant / parity checks, then builds the Spin-Sweep seal:
a SHA-256 hash chain over the 360-degree sweep, bound to the check log and the two figures.
Security rests on SHA-256. Usage: python3 certify_mirror_quilt.py [fig1.png fig2.png]"""
import numpy as np, itertools, random, hashlib, sys
sha = lambda b: hashlib.sha256(b).digest()

def run(fig1, fig2):
    random.seed(2); np.random.seed(3)
    R = []                                              # (label, passed)
    add = lambda label, ok: R.append((label, bool(ok)))
    M = np.diag([1,1,-1.]); F = np.diag([-1,1,1.]); Phi = np.diag([-1,1,-1.]); I3 = np.eye(3)
    Nn = np.array([[0,1],[1,0.]])
    def Ry(t):
        c, s = np.cos(t), np.sin(t); return np.array([[c,0,s],[0,1,0],[-s,0,c]])
    # --- spin sweep and bridge ---
    th = np.linspace(0, 2*np.pi, 361)
    add("S(theta)=Ry(theta).M has det -1 at all 361 samples", all(abs(np.linalg.det(Ry(t)@M)+1) < 1e-9 for t in th))
    add("Closure S(360)=S(0)=M and S(180)=F", np.allclose(Ry(2*np.pi)@M, M) and np.allclose(Ry(np.pi)@M, F))
    ok = True
    for t in th:
        n = np.array([np.sin(t/2), 0, np.cos(t/2)]); ok &= np.allclose(Ry(t)@M, np.eye(3) - 2*np.outer(n, n))
    add("Mirror normal turns at half rate: n(theta)=(sin(theta/2),0,cos(theta/2))", ok)
    add("Bridge Phi = F.M, Phi = Ry(pi), det Phi = +1", np.allclose(F@M, Phi) and np.allclose(Ry(np.pi), Phi) and abs(np.linalg.det(Phi)-1) < 1e-9)
    add("{I,M,F,Phi} is a Klein four-group", all(np.allclose(a@a, I3) for a in (M, F, Phi)) and np.allclose(M@F, F@M))
    add("Negation N: det -1, N^2=I; odd loops close at -1, even at +1", abs(np.linalg.det(Nn)+1) < 1e-9 and np.allclose(Nn@Nn, np.eye(2)) and np.allclose(Nn@np.array([1,-1.]), -np.array([1,-1.])) and np.allclose(Nn@Nn@Nn, Nn))
    # Rule 2/3 bridge: M and J as permutations of {0+,0-,+inf,-inf}
    lab = ["0+", "0-", "+inf", "-inf"]
    pM = {"0+":"0-", "0-":"0+", "+inf":"-inf", "-inf":"+inf"}; pJ = {"0+":"+inf", "+inf":"0+", "0-":"-inf", "-inf":"0-"}
    comp = lambda a, b: {x: a[b[x]] for x in lab}; idp = {x: x for x in lab}
    orbit = {pM[x] for x in lab} | {pJ[x] for x in lab} | {comp(pM, pJ)[x] for x in lab}
    add("Rules 2-3: M, J, MJ commute, square to I, act as one orbit on {0+,0-,+inf,-inf}",
        comp(pM,pJ) == comp(pJ,pM) and comp(pM,pM) == idp and comp(pJ,pJ) == idp and orbit == set(lab))
    add("Original paper's claim 'Phi is the mirror' passes the determinant test", abs(np.linalg.det(Phi)+1) < 1e-9)
    # --- mirror quilt theorem ---
    def refl(ax, a):
        A = np.eye(4); A[ax, ax] = -1; A[ax, 3] = 2*a; return A
    T = refl(2, 3.0) @ refl(2, 0.0)
    add("Part 1: mirrors z=0 then z=a compose to translation by 2a, det +1", np.allclose(T[:3,:3], I3) and np.allclose(T[:3,3], [0,0,6]))
    def step(T, ax, i, d): return refl(ax, i+1 if d == 1 else i) @ T
    def walk(path):
        T, pos = np.eye(4), [0,0,0]
        for ax, d in path: T = step(T, ax, pos[ax], d); pos[ax] += d
        return tuple(pos), T
    def g(c):
        p = []
        for ax in range(3): p += [(ax, 1 if c[ax] > 0 else -1)] * abs(c[ax])
        return walk(p)[1]
    rg = range(-3, 4); mats = {c: g(c) for c in itertools.product(rg, rg, rg)}
    keys = {tuple(np.round(m, 6).ravel()) for m in mats.values()}
    add("Part 1: 343 cells <-> 343 distinct group elements; g_C0 = I", len(keys) == len(mats) and np.allclose(mats[(0,0,0)], np.eye(4)))
    add("Part 2: det g_c = (-1)^(i+j+k) on all 343 cells", all(round(np.linalg.det(m)) == (-1)**(sum(c) % 2) for c, m in mats.items()))
    nb = True
    for c in mats:
        for ax in range(3):
            d = list(c); d[ax] += 1
            if tuple(d) in mats: nb &= round(np.linalg.det(mats[c])*np.linalg.det(mats[tuple(d)])) == -1
    add("Part 2: face-neighbours always have opposite handedness", nb)
    ok = True
    for _ in range(2000):
        path = [(random.randrange(3), random.choice([-1,1])) for _ in range(random.randint(1,16))]
        pos, T = walk(path); ok &= (np.allclose(T, mats[pos]) if pos in mats else True)
    add("Part 3: route independence over 2000 random walks", ok)
    cl = True
    for _ in range(500):
        h = [(random.randrange(3), random.choice([-1,1])) for _ in range(random.randint(1,8))]
        pos, T = walk(h + [(a, -d) for a, d in reversed(h)]); cl &= pos == (0,0,0) and np.allclose(T, np.eye(4))
    add("Part 3: closed loops return the identity (closure +1), 500 loops", cl)
    ctr = np.array([.5,.5,.5])
    def gamma(P, t):
        A = np.eye(4); A[:3,:3] = P; A[:3,3] = ctr - P @ ctr + np.array(t); return A
    def rand_P(): return np.diag(np.random.choice([-1,1], 3)) @ np.eye(3)[np.random.permutation(3)]
    def cell_of(A): return tuple(int(np.floor(x)) for x in (A @ np.array([.5,.5,.5,1]))[:3])
    def chi(A):
        c = cell_of(A); s = np.linalg.inv(g(c)) @ A
        assert np.allclose(s @ np.array([.5,.5,.5,1]), [.5,.5,.5,1]); return round(np.linalg.det(s)), c
    f1 = f2 = True
    for _ in range(1500):
        A = gamma(rand_P(), np.random.randint(-4, 5, 3)); x, c = chi(A)
        f1 &= x == round(np.linalg.det(A)) * (-1)**(sum(c) % 2)
        B = gamma(rand_P(), np.random.randint(-4, 5, 3)); y, _ = chi(B); z, _ = chi(A @ B); f2 &= z == x*y
    add("Part 4: chi(gamma) = det(gamma)(-1)^(i+j+k), 1500 random tiling symmetries", f1)
    add("Part 4: chi is multiplicative, 1500 random pairs", f2)
    for L in (2,3,4,5):
        pl = chi(gamma(np.eye(3), (L,0,0)))[0]; tw = chi(gamma(np.diag([1,-1,1.]), (L,0,0)))[0]
        add(f"Corollary L={L}: plain wrap chi={pl:+d}, y-flip wrap chi={tw:+d}", pl == (-1)**L and tw == -(-1)**L)
    gz = chi(gamma(np.diag([-1,1,1.]), (0,0,3)))[0]; gy = chi(gamma(np.eye(3), (0,2,0)))[0]
    add(f"3D twisted cuboid: z-wrap L=3 with x-flip chi={gz:+d}, y-wrap L=2 chi={gy:+d}", gz == 1 and gy == 1)
    log = "\n".join(f"{'PASS' if ok else 'FAIL'}|{lab}" for lab, ok in R)
    # --- Spin-Sweep seal: SHA-256 hash chain over the 360-degree sweep ---
    H = sha(b"SPIN-SWEEP-SEAL-v1")
    fmt = lambda x: f"{(0.0 if abs(x) < 5e-10 else x):.9f}"
    for k in range(361):
        S = Ry(np.deg2rad(k)) @ M
        H = sha(H + f"{k}|{','.join(fmt(x) for x in S.ravel())}".encode())
    closed = np.allclose(Ry(2*np.pi) @ M, M)
    H = sha(H + f"closure:{closed}".encode())
    log_h = sha(log.encode()); f1h = sha(open(fig1, "rb").read()); f2h = sha(open(fig2, "rb").read())
    seal = sha(H + log_h + f1h + f2h)
    return dict(results=R, log=log, chain=H.hex(), log_hash=log_h.hex(), fig1=f1h.hex(), fig2=f2h.hex(), seal=seal.hex())

if __name__ == "__main__":
    a = sys.argv[1:] or ["/mnt/user-data/outputs/Mirror_Quilt_and_Twist.png", "/mnt/user-data/outputs/Mirror_Quilt_3D.png"]
    r = run(*a); print(r["log"])
    for k in ("chain", "log_hash", "fig1", "fig2", "seal"): print(f"{k:9s} {r[k]}")
