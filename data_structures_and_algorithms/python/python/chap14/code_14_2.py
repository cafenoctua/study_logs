INF = 10 ** 10

def chmin(a: list, b: int, v: int):
    if a[v] > b:
        a[v] = b
        return True
    else:
        return False
    

def main():
    input_iter = iter([
        "6 12 0",
        "0 1 3",
        "0 3 100",
        "1 2 50",
        "1 4 -4",
        "1 3 -5",
        "4 3 25",
        "2 3 -10",
        "3 1 57",
        "2 5 100",
        "2 4 -5",
        "4 5 8",
        "4 2 57"
    ])
    
    N, M, s = map(int, next(input_iter).split())
    G = [] * N
    for _ in range(M):
        a, b, w = map(int, next(input_iter).split())
        G.append((a, b, w))
    
    exist_negative_cycle = False
    dist = [INF] * N
    dist[s] = 0
    for i in range(N):
        update = False
        for v in range(N):
            if dist[v] == INF: continue
            
            for u, v,  w in G:
                if chmin(dist, dist[u] + w, v):
                    update = True
    
        if not(update): break
        
        if i == N - 1 and update: exist_negative_cycle = True
    
    if exist_negative_cycle: print("NEGATIVE CYCLE")
    else:
        for v in range(N):
            if dist[v] < INF: print(dist[v])
            else: print("INF")
    print(G)
    
if __name__ == "__main__":
    main()