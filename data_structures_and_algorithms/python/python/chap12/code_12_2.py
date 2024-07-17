def merge_sort(a: list, left: int, right: int) -> None:
    if right - left == 1: return
    mid = left + (right - left) // 2
    
    merge_sort(a, left, mid)
    merge_sort(a, mid, right)
    
    buf = []
    for i in range(left, mid):
        buf.append(a[i])
    for i in range(right-1, mid-1, -1):
        buf.append(a[i])
    
    index_left = 0
    index_right = len(buf) - 1
    for i in range(left, right):
        if buf[index_left] <= buf[index_right]:
            a[i] = buf[index_left]
            index_left += 1
        else:
            a[i] = buf[index_right]
            index_right -= 1
            
    return

def main():
    input_data = [
        8,
        12,
        9,
        15,
        3,
        8,
        17,
        6,
        1
    ]
    
    input_iter = iter(input_data)
    N = int(next(input_iter))
    a = [int(next(input_iter)) for _ in range(N)]
    
    merge_sort(a, 0, N)
    print(a)
    
if __name__ == "__main__":
    main()