INF = 10 ** 10

class Edge:
    def __init__(self, to: int, w: int) -> None:
        self.to: int = to
        self.w: int = w
    
def chmin(a: list, b: int, v: int):
    if a[v] > b:
        a[v] = b
        return True
    else:
        return False

def main():
    input_iter = iter([
        "6 9 0",
        "0 1 3",
        "0 2 5",
        "1 3 12",
        "1 2 4",
        "2 3 9",
        "2 4 4",
        "3 5 2",
        "4 3 7",
        "4 5 8"
    ])
    
    N, M, s = map(int, next(input_iter).split())
    
    G = [[] for _ in range(N)]
    for _ in range(M):
        a, b, w = map(int, next(input_iter).split())
        G[a].append(Edge(to=b, w=w))
    
    used = [False] * N
    dist = [INF] * N
    dist[s] = 0
    for _ in range(N):
        min_dist = INF
        min_v = -1
        for v in range(N):
            if not(used[v]) and dist[v] < min_dist:
                min_dist = dist[v]
                min_v = v
        if min_v == -1: break
        
        for e in G[min_v]:
            chmin(dist, dist[min_v] + e.w, e.to)
        used[min_v] = True
    
    for v in range(N):
        if dist[v] < INF: print(dist[v])
        else: print("INF")
    
if __name__ == "__main__":
    main()