INF = 10 << 60

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
    
    min_value = INF
    second_min_value = INF
    for i in range(N):
        if a[i] < min_value:
            second_min_value = min_value
            min_value = a[i]
        elif a[i] < second_min_value:
            second_min_value = a[i]
    
    print(second_min_value)
    
if __name__ == "__main__":
    main()