def quick_sort(a: list, left: int, right: int):
    if right - left <= 1: return
    
    pivot_index = (left + right) // 2
    pivot = a[pivot_index]
    a[pivot_index], a[right - 1] = a[right - 1], a[pivot_index]
    
    i = left
    for j in range(left, right - 1):
        if a[j] < pivot:
            a[i], a[j] = a[j], a[i]
            i += 1
    
    a[i], a[right - 1] = a[right - 1], a[i]
    
    quick_sort(a, left, i)
    quick_sort(a, i + 1, right)
    
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
    
    quick_sort(a, 0, N)
    print(a)
    
if __name__ == "__main__":
    main()