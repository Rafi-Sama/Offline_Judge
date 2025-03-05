x, y = map(int, input().split())
print(x, y)
if x > y:
    x, y = y, x
for i in range(x, y+1):
    print(i)