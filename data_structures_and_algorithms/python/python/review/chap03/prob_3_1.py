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
    
    found_id = -1
    for i in range(N):
        if a[i] == v:
            found_id = i
            # break
    
    print(found_id)
    
if __name__ == "__main__":
    main()