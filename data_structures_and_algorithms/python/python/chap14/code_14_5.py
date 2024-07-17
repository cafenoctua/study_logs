INF = 10 << 60


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
    dp = [[INF] * N for _ in range(N)]
    
    for _ in range(M):
        a, b, w = map(int, next(input_iter).split())
        dp[a][b] = w
        
    for v in range(N):
        dp[v][v] = 0
    
    for k in range(N):
        for i in range(N):
            for j in range(N):
                dp[i][j] = min(dp[i][j], dp[i][k] + dp[k][j])
    
    exist_negative_cycle = False
    for v in range(N):
        if dp[v][v] < 0: exist_negative_cycle = True
    if exist_negative_cycle: print("NEGATIVE CYCLE")
    else:
        result = []
        for i in range(N):
            row = []
            for j in range(N):
                if j > 0:
                    row.append(" ")
                if dp[i][j] < INF//2: row.append(str(dp[i][j]))
                else: row.append("INF")
            result.append("".join(row))
        for line in result:
                print(line)

if __name__ == "__main__":
    main()