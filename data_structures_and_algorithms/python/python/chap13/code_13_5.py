def dfs(G: list, v: int, color: list, cur: int=0):
    color[v] = cur
    for next_v in G[v]:
        if color[next_v] != -1:
            if color[next_v] == cur: return False
            continue
        if not(dfs(G, next_v, color, 1 - cur)): return False
    return True

def main():
    input_iter = iter([
        "5 6",
        "1 0",
        "1 4",
        "1 2",
        "0 3",
        "3 4",
        # input this result become to not bipartite
        "0 4",
    ])
    
    N, M = map(int, next(input_iter).split())
    Graph = [[] for _ in range(N)]
    for _ in range(M):
        a, b = map(int, next(input_iter).split())
        Graph[a].append(b)
        Graph[b].append(a)
        
    color = [-1] * N
    is_bipartite = True
    for v in range(0, N):
        if color[v] != -1: continue
        if not(dfs(Graph, v, color)): is_bipartite = False
    
    if is_bipartite: print("Yes")
    else: print("No")
    
if __name__ == "__main__":
    main()