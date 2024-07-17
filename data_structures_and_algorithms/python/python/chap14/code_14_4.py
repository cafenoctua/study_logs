import heapq
import sys

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
    
    que = []
    heapq.heappush(que, (dist[s], s))
    
    while que:
        d, v = heapq.heappop(que)
        
        
        if d > dist[v]: continue
        
        for e in G[v]:
            if chmin(dist, dist[v] + e.w, e.to):
                heapq.heappush(que, (dist[e.to], e.to))
    
    for v in range(N):
        if dist[v] < INF: print(dist[v])
        else: print("INF")
    
if __name__ == "__main__":
    main()