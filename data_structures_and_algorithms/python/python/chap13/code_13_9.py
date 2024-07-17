def dfs(Graph: list, v: int, depth: list, subtree_size: list, p: int = -1, d: int = 0):
    depth[v] = d
    
    for c in Graph[v]:
        if c == p: continue
        dfs(Graph, c, depth, subtree_size, v, d + 1)

    subtree_size[v] = 1
    for c in Graph[v]:
        if c == p: continue
        subtree_size[v] += subtree_size[c]

def main():
    input_data = [
        "15",
        "0 1",
        "1 2",
        "1 3",
        "2 4",
        "0 5",
        "5 6",
        "6 7",
        "6 8",
        "5 9",
        "9 10",
        "9 11",
        "0 12",
        "12 13",
        "12 14"
    ]
    
    input_iter = iter(input_data)
    N = int(next(input_iter))
    Graph =[[] for _ in range(N)]
    for _ in range(N - 1):
        a, b = map(int, next(input_iter).split())
        Graph[a].append(b)
        Graph[b].append(a)
    
    root = 0
    depth = [0] * N
    subtree_size = [0] * N
    dfs(Graph, root, depth, subtree_size)
    
    for v in range(N):
        print(f"{v}: depth = {depth[v]}, subtree_size = {subtree_size[v]}")
    
if __name__ == "__main__":
    main()