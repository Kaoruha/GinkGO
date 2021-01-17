# a = 100
# b = None
# c = False

# print(not a)
# print(not b)
# print(not c)


# print('='*50)

# print(a is None)
# print(b is None)
# print(c is None)


# a = []
# print(len(a))

# a=['name','age']
# b = {"name":1,"age":2}

# for i in a:
#     print(b[i])


a = 240241


split_unit = 10000

b = a // split_unit
c = int(a / split_unit)

print(b)
print(c)

for i in range(c + 1):
    print(f"{i*split_unit}到{(i+1)*split_unit}")


a = [1, 2, 3, 4]
print(a[0:10])
