from bisect import bisect_left
def main():
    input_data = [
        "3 6",
        "10 6",
        "15 3",
        "5 2"
    ]
    input_iter = iter(input_data)
    N, M = map(int, next(input_iter).split())
    
    A = []
    B = []
    v = []
    for _ in range(N):
        a, b = map(int, next(input_iter).split())
        v.append([a, b])
        
    v.sort()
    res = 0
    for a, b in v:
        if M <= 0: break
        res += a * min(M, b)
        M -= min(M, b)
        
    print(res)
    
if __name__ == "__main__":
    main()