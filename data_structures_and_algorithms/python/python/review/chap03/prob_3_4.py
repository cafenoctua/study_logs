INF = 10 << 60

def main():
    input_iter = iter([
        "6",
        "4",
        "3",
        "12",
        "7",
        "11",
        "7"
    ])
    
    N = int(next(input_iter))
    
    a = [int(next(input_iter)) for _ in range(N)]
    
    min_value = INF
    max_value = 0
    for i in range(N):
        if a[i] < min_value:
            min_value = a[i]
        if a[i] > max_value:
            max_value = a[i]
    print(max_value - min_value)
    
if __name__ == "__main__":
    main()