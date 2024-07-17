class UnionFind:
    def __init__(self, n) -> None:
        self.par = [-1] * n
        self.siz = [1] * n
        
    def root(self, x):
        if self.par[x] == -1:
            return x
        else:
            self.par[x] = self.root(self.par[x])
            return self.par[x]
    
    def issame(self, x, y):
        return self.root(x) == self.root(y)
    
    def unit(self, x, y):
        x = self.root(x)
        y = self.root(y)
        if x == y:
            return False
        if self.siz[x] < self.siz[y]:
            x, y = y, x
        self.par[y] = x
        self.siz[x] += self.siz[y]
        return True

    def size(self, x):
        return self.siz[self.root(x)]


def main():
    input_iter = iter([
        "8 12",
        "4 2 9",
        "4 6 2",
        "4 1 4",
        "2 5 10",
        "2 7 5",
        "6 7 7",
        "1 6 3",
        "1 3 8",
        "7 3 6",
        "7 0 3",
        "3 0 5",
        "0 5 6"
    ])
    
    N, M = map(int, next(input_iter).split())
    edges = []
    for _ in range(M):
        u, v, w = map(int, next(input_iter).split())
        edges.append([w, [u, v]])
    
    edges.sort()
    
    res = 0
    uf = UnionFind(N)
    for i in range(M):
        w = edges[i][0]
        u = edges[i][1][0]
        v = edges[i][1][1]
        
        if uf.issame(u, v): continue
        
        res += w
        uf.unit(u, v)
        
    print(res)

if __name__ == "__main__":
    main()