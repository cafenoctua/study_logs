from bisect import bisect_left

def sort(a: list):
    b = a.copy()
    b.sort()
    return b

def my_bisect(b: list, a: int, l: int, h: int):
    mid = (h + l) // 2
    while b[mid] != a:
        if b[mid] < a:
            l = mid
        else:
            h = mid
        mid = (h + l) // 2
    print(mid)

def main():
    input_data = [
        8,
        10,
        12,
        15,
        3,
        8,
        17,
        4,
        1
    ]
    
    input_iter = iter(input_data)
    N = int(next(input_iter))
    a = [int(next(input_iter)) for _ in range(N)]
    
    b = sort(a)
    
    # results = []
    for i in range(N):
        print(bisect_left(b, a[i]))
        
        index = 0
        l = 0
        h = len(b)
        my_bisect(b, a[i], l=l, h=h)
        # mid = (h + l) // 2
        # while b[mid] != a[i]:
        #     if b[mid] < a[i]:
        #         l = mid
        #     else:
        #         h = mid
        #     mid = (h + l) // 2
        # print(mid)
    # print(results)
    
if __name__ == "__main__":
    main()