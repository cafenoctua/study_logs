MAX = 1000000

def bucket_sort(a: list):
    N = len(a)
    
    num  = [0] * MAX
    for i in range(N):
        num[a[i]] += 1
        
    sum = [0] * MAX
    for v in range(1, MAX):
        sum[v] = sum[v - 1] + num[v]
        
    a2 = [0] * N
    for i in range(N - 1, -1, -1):
        a2[sum[a[i]] - 1] = a[i]
        sum[a[i]] -= 1
        
    return a2
    
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
    
    a = bucket_sort(a)
    print(a)
    
if __name__ == "__main__":
    main()