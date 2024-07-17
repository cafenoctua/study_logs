from collections import deque

def BFS(G:list, s:int) -> list:
    N: int = len(G)
    dist: list = [-1] * N
    queue = deque([s])
    
    dist[s] = 0
    
    while queue:
        v = queue.popleft()
        
        for x in G[v]:
            if dist[x] != -1: continue
            
            dist[x] = dist[v] + 1
            queue.append(x)
    
    return dist
    

def main():
    input_data = [
        "9 13",
        "0 1",
        "0 4",
        "0 2",
        "1 3",
        "1 8",
        "1 4",
        "4 8",
        "2 5",
        "3 7",
        "3 8",
        "8 5",
        "7 6",
        "5 6"
    ]
    
    input_iter = iter(input_data)
    N, M = map(int, next(input_iter).split())
    G: list[list[int]] =[[] for _ in range(N)]
    for _ in range(M):
        a, b = map(int, next(input_iter).split())
        G[a].append(b)
    
    dist: list = BFS(G, 0)
    for v in range(N):
        print(f'{v}: {dist[v]}')

if __name__ == "__main__":
    main()