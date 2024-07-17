def dfs(Graph: list, v: int, seen: list):
    seen[v] = True
    
    for next_v in Graph[v]:
        if seen[next_v]: continue
        dfs(Graph, next_v, seen)


def main():
    input_data = [
        "8 12",
        "4 1",
        "4 6",
        "4 2",
        "1 6",
        "1 3",
        "6 7",
        "2 7",
        "2 5",
        "7 0",
        "3 0",
        "3 7",
        "0 5"
    ]
    
    input_iter = iter(input_data)
    N, M = map(int, next(input_iter).split())
    Graph =[[] for _ in range(N)]
    for _ in range(M):
        a, b = map(int, next(input_iter).split())
        Graph[a].append(b)
        
    seen = [False] * N
    for v in range(N):
        if seen[v]: continue
        dfs(Graph, v, seen)
    print(seen)
if __name__ == "__main__":
    main()