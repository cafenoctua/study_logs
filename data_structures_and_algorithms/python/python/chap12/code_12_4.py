def heapify(a: list, i: int, N: int):
    child1 = i * 2 + 1
    if child1 >= N: return
    
    if child1 + 1 < N and a[child1 + 1] > a[child1]: child1 += 1
    
    if a[child1] <= a[i]: return
    
    a[i], a[child1] = a[child1], a[i]
    
    heapify(a, child1, N)
    
def heap_sort(a: list):
    N = len(a)
    
    for i in range(int(N / 2 - 1), -1, -1):
        heapify(a, i, N)
    
    for i in range(N - 1, 0, -1):
        a[0], a[i] = a[i], a[0]
        heapify(a, 0, i)
    
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
    
    heap_sort(a)
    print(a)

if __name__ == "__main__":
    main()