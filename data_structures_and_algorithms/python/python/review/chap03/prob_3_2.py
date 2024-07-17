def main():
    input_iter = iter([
        "6 7",
        "4",
        "3",
        "12",
        "7",
        "11",
        "7"
    ])
    
    N, v = map(int, next(input_iter).split())
    
    a = [int(next(input_iter)) for _ in range(N)]
    
    count = 0
    for i in range(N):
        if a[i] == v:
            count += 1
            # break
    
    print(count)
    
if __name__ == "__main__":
    main()